"""
backloader.py — High-Performance Historical Data Backloader
============================================================
Arsitektur:
  ThreadPoolExecutor (N workers)
    └─ setiap worker:
         ├─ thread-local StockbitApiClient
         ├─ thread-local StockbitParser  (instance baru per thread, DB dari pool)
         ├─ TokenBucketRateLimiter.acquire()
         └─ parser.parse_payload(url, payload)   ← tanpa temp file

Tidak ada ingest_queue, tidak ada temp file, tidak ada single consumer bottleneck.
"""

import os
import sys
import json
import time
import math
import logging
import threading
import argparse
import concurrent.futures
from datetime import datetime, timedelta
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Env & path setup
# ---------------------------------------------------------------------------

load_dotenv()

# Bypass proxy so Python scripts can reach Stockbit API directly
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ[_k] = ""

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from api_client import StockbitApiClient
from parser.stockbit_parser import StockbitParser
from db_manager import StockbitDbManager
from db.base_repository import BaseRepository
from backload_config import (
    TICKER_GROUPS,
    CHECKPOINT_PATH,
    DATA_TYPE_METADATA,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
    DEFAULT_DELAY_MS,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging():
    os.makedirs("data", exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        # FileHandler sudah thread-safe (internal lock di logging module)
        logging.FileHandler(os.path.join("data", "backloader.log"), encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)

_setup_logging()
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter
# ---------------------------------------------------------------------------

class TokenBucketRateLimiter:
    """
    Thread-safe Token Bucket rate limiter.

    Mengizinkan burst kecil tanpa memblokir thread lain di dalam lock.
    Berbeda dengan naive sleep-inside-lock, hanya kalkulasi & update token
    yang dilakukan di dalam lock; sleep() dilakukan di luar.
    """

    def __init__(self, rate_per_second: float, burst: int = 1):
        """
        Args:
            rate_per_second: jumlah token (request) yang diregenerasi per detik.
            burst          : kapasitas maksimum token (max instantaneous requests).
        """
        self._rate = rate_per_second
        self._burst = float(burst)
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0):
        """Block sampai token tersedia, lalu konsumsi token."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last_refill = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return  # Token tersedia, lanjut

                # Hitung waktu tunggu tanpa holding lock
                wait_time = (tokens - self._tokens) / self._rate

            # Sleep di luar lock agar thread lain bisa acquire sementara kita menunggu
            time.sleep(wait_time)


# ---------------------------------------------------------------------------
# Thread-local worker context
# ---------------------------------------------------------------------------

class _WorkerContext(threading.local):
    """
    Thread-local storage untuk API client dan parser.
    Setiap thread mendapat instance sendiri sehingga tidak ada shared mutable state.
    """
    client: StockbitApiClient = None
    parser: StockbitParser = None


_ctx = _WorkerContext()


def _get_worker_client(headers_path: str) -> StockbitApiClient:
    if _ctx.client is None:
        _ctx.client = StockbitApiClient(headers_path=headers_path)
    return _ctx.client


def _get_worker_parser(db_dsn: str) -> StockbitParser:
    if _ctx.parser is None:
        _ctx.parser = StockbitParser(db_path=db_dsn)
    return _ctx.parser


# ---------------------------------------------------------------------------
# StockbitBackloader
# ---------------------------------------------------------------------------

class StockbitBackloader:
    """
    Orchestrator utama backloader.

    Menggunakan ThreadPoolExecutor di mana setiap worker thread memiliki
    API client dan parser sendiri (thread-local).  Semua DB writes dilakukan
    langsung dari parser menggunakan koneksi dari shared ThreadedConnectionPool.
    """

    def __init__(
        self,
        db_dsn: str = None,
        headers_path: str = None,
        delay_ms: int = DEFAULT_DELAY_MS,
        workers: int = 4,
        max_connections: int = None,
    ):
        self.db_dsn = db_dsn
        self.headers_path = headers_path or os.environ.get(
            "STOCKBIT_HEADERS_PATH", "data/session_headers.json"
        )
        self.workers = workers

        # Inisialisasi connection pool sebelum worker thread dibuat
        # max_connections default = workers * 2 + 2 (untuk main thread)
        max_conn = max_connections or (workers * 2 + 2)
        BaseRepository.init_pool(
            db_dsn or os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"),
            minconn=2,
            maxconn=max_conn,
        )
        log.info(f"Connection pool initialized: min=2, max={max_conn}")

        # Rate limiter: 1 request per delay_ms ms, burst = min(workers, 2)
        rate_per_second = 1000.0 / max(delay_ms, 1)
        self._rate_limiter = TokenBucketRateLimiter(
            rate_per_second=rate_per_second,
            burst=min(workers, 2),
        )
        log.info(f"Rate limiter: {rate_per_second:.1f} req/s, burst={min(workers, 2)}")

        # Checkpoint & lock
        self._checkpoint_lock = threading.Lock()
        self._checkpoint = self._load_checkpoint()

        # Lightweight DB handle untuk operasi orchestrator (query trading dates, dll)
        self._db = StockbitDbManager(db_dsn, initialize=True)

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------

    def _load_checkpoint(self) -> dict:
        if os.path.exists(CHECKPOINT_PATH):
            try:
                with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Gagal membaca checkpoint: {e}. Mulai dari awal.")
        return {"completed_tickers": {}}

    def _save_checkpoint(self):
        """Simpan checkpoint ke disk. Caller harus memegang _checkpoint_lock."""
        os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
        try:
            with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                json.dump(self._checkpoint, f, indent=2)
        except Exception as e:
            log.error(f"Gagal menyimpan checkpoint: {e}")

    # ------------------------------------------------------------------
    # API call wrapper
    # ------------------------------------------------------------------

    def _api_call(self, client: StockbitApiClient, method_name: str, kwargs: dict, max_retries: int = 6):
        """
        Panggil method API dengan:
          1. Token bucket rate limiting (acquire sebelum request)
          2. Exponential backoff pada 429/5xx
          3. URL spy untuk mendapatkan URL aktual dengan query params
        """
        method = getattr(client, method_name)
        backoff = 5.0
        last_exc = None

        for attempt in range(max_retries):
            # Acquire rate limit token (sleep di luar lock jika perlu)
            self._rate_limiter.acquire()

            # Spy URL aktual (termasuk query string)
            last_url = {"value": ""}
            orig_get = client._get

            def spy_get(url, params=None):
                from urllib.parse import urlencode
                last_url["value"] = f"{url}?{urlencode(params, doseq=True)}" if params else url
                return orig_get(url, params)

            client._get = spy_get
            try:
                payload = method(**kwargs)
                client._get = orig_get
                return payload, last_url["value"]
            except Exception as exc:
                client._get = orig_get
                last_exc = exc
                err_str = str(exc)
                log.warning(f"API {method_name} gagal (percobaan {attempt+1}/{max_retries}): {err_str}")

                if any(code in err_str for code in ("400", "404", "401")):
                    raise  # Non-retriable client errors
                
                log.warning(f"Server error atau masalah koneksi jaringan. Mencoba kembali dengan backoff {backoff:.0f}s ...")
                time.sleep(backoff)
                backoff = min(backoff * 2.0, 120.0)
                try:
                    client.load_headers()
                except Exception:
                    pass

        raise Exception(f"API {method_name} gagal setelah {max_retries} percobaan: {last_exc}")

    # ------------------------------------------------------------------
    # Helper DB queries
    # ------------------------------------------------------------------

    def _get_trading_dates(self, symbol: str, start_date: str, end_date: str) -> list:
        """Ambil daftar tanggal trading dari tabel ohlcv_data (EOD rows)."""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT date
                        FROM ohlcv_data
                        WHERE symbol = %s
                          AND time = 'EOD'
                          AND date >= %s
                          AND date <= %s
                        ORDER BY date DESC
                        """,
                        (symbol, start_date, end_date),
                    )
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            log.error(f"[{symbol}] Query trading dates gagal: {e}")
            return []

    def _broker_summary_exists(self, symbol: str, date_str: str) -> bool:
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT EXISTS(SELECT 1 FROM broker_summaries WHERE symbol=%s AND date=%s LIMIT 1)",
                        (symbol, date_str),
                    )
                    return cur.fetchone()[0]
        except Exception:
            return False

    def _intraday_exists(self, symbol: str, date_str: str) -> bool:
        """True jika sudah ada >= 100 candle 1m untuk symbol pada tanggal tersebut di DB."""
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM ohlcv_data
                        WHERE symbol = %s AND date = %s AND time != 'EOD'
                        """,
                        (symbol, date_str),
                    )
                    return cur.fetchone()[0] >= 100
        except Exception as e:
            log.error(f"[{symbol}] Error checking if intraday exists for date {date_str}: {e}")
            return False

    def _running_trades_exist(self, symbol: str, date_str: str) -> bool:
        """True jika sudah ada >= 100 running trades untuk symbol pada tanggal tersebut di DB.
        Threshold 100 = satu hari penuh (TLKM saja bisa 30.000+).
        """
        try:
            # Parse start and end timestamp for precise epoch-based filtering
            dt_start = datetime.strptime(date_str, "%Y-%m-%d")
            start_ts = dt_start.timestamp()
            end_ts = start_ts + 86400

            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM running_trades
                        WHERE symbol = %s AND timestamp >= %s AND timestamp < %s
                        """,
                        (symbol, start_ts, end_ts),
                    )
                    return cur.fetchone()[0] > 0
        except Exception as e:
            log.error(f"[{symbol}] Error checking if running trades exist for date {date_str}: {e}")
            return False

    # ------------------------------------------------------------------
    # Ticker group resolver
    # ------------------------------------------------------------------

    def get_ticker_group_symbols(self, group_name: str) -> list:
        name = group_name.upper()
        if name in TICKER_GROUPS:
            return TICKER_GROUPS[name]
        queries = {
            "CONGLOMERATE": "SELECT DISTINCT symbol FROM conglomerate_stocks ORDER BY symbol",
            "MSCI":         "SELECT DISTINCT symbol FROM msci_tracker WHERE status='ACTIVE' ORDER BY symbol",
            "ALL":          "SELECT symbol FROM company_profiles ORDER BY symbol",
        }
        if name in queries:
            try:
                with self._db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries[name])
                        return [r[0] for r in cur.fetchall()]
            except Exception as e:
                log.error(f"Gagal resolve group '{name}': {e}")
                return []
        # Watchlist lookup
        try:
            with self._db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT symbol
                        FROM watchlist_items wi
                        JOIN watchlists w ON wi.watchlist_id = w.id
                        WHERE UPPER(w.name) = %s
                        ORDER BY symbol
                        """,
                        (name,),
                    )
                    rows = cur.fetchall()
                    if rows:
                        return [r[0] for r in rows]
        except Exception as e:
            log.error(f"Gagal resolve watchlist '{name}': {e}")
        return []

    # ------------------------------------------------------------------
    # Individual data-type backloaders
    # ------------------------------------------------------------------

    def _backload_ohlcv(self, symbol: str, start_date: str, end_date: str) -> bool:
        client = _get_worker_client(self.headers_path)
        parser = _get_worker_parser(self.db_dsn)
        log.info(f"[{symbol}] Fetching daily OHLCV ({start_date} → {end_date}) ...")
        try:
            payload, url = self._api_call(
                client,
                "get_daily_candles",
                {"symbol": symbol, "from_date": end_date, "to_date": start_date, "limit": 0},
            )
            parser.parse_payload(url, payload)
            return True
        except Exception as e:
            log.error(f"[{symbol}] OHLCV failed: {e}")
            return False

    def _backload_foreign_flow(self, symbol: str, start_date: str, end_date: str) -> bool:
        client = _get_worker_client(self.headers_path)
        parser = _get_worker_parser(self.db_dsn)
        log.info(f"[{symbol}] Fetching foreign flow ({start_date} → {end_date}) ...")
        page, limit, total = 1, 50, 0
        dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()

        while True:
            orig_get = client._get
            def patch_get(url, params=None):
                params = params or {}
                params["start_date"] = start_date
                params["end_date"] = end_date
                return orig_get(url, params)
            client._get = patch_get
            try:
                payload, url = self._api_call(
                    client, "get_historical_summary",
                    {"symbol": symbol, "period": "HS_PERIOD_DAILY", "limit": limit, "page": page},
                )
            finally:
                client._get = orig_get

            results = payload.get("data", {}).get("result", [])
            if not results:
                break
            parser.parse_payload(url, payload)
            total += len(results)
            last_date_str = results[-1].get("date")
            if last_date_str:
                try:
                    if datetime.strptime(last_date_str, "%Y-%m-%d").date() <= dt_start:
                        break
                except Exception:
                    pass
            if len(results) < limit:
                break
            page += 1

        log.info(f"[{symbol}] Foreign flow done: {total} records.")
        return True

    def _backload_broker_summary(self, symbol: str, start_date: str, end_date: str) -> bool:
        client = _get_worker_client(self.headers_path)
        parser = _get_worker_parser(self.db_dsn)
        trading_dates = self._get_trading_dates(symbol, start_date, end_date)
        if not trading_dates:
            log.warning(f"[{symbol}] Tidak ada trading dates — broker summary dilewati.")
            return False

        # Load completed dates dari checkpoint
        completed = set()
        with self._checkpoint_lock:
            prog = self._checkpoint["completed_tickers"].get(symbol, {})
            completed = set(prog.get("broker_summary_dates", []))

        ok, skip = 0, 0
        for d in trading_dates:
            if d in completed or self._broker_summary_exists(symbol, d):
                skip += 1
                completed.add(d)
                continue

            orig_get = client._get
            def patch_get(url, params=None):
                params = params or {}
                params.update({
                    "transaction_type": "TRANSACTION_TYPE_NET",
                    "market_board": "MARKET_BOARD_REGULER",
                    "investor_type": "INVESTOR_TYPE_ALL",
                    "limit": 25,
                })
                return orig_get(url, params)
            client._get = patch_get
            try:
                payload, url = self._api_call(
                    client, "get_market_detector",
                    {"stock_code": symbol, "from_date": d, "to_date": d, "transaction_type": "TRANSACTION_TYPE_NET"},
                )
                parser.parse_payload(url, payload)
                completed.add(d)
                ok += 1
                if ok % 10 == 0:
                    with self._checkpoint_lock:
                        prog["broker_summary_dates"] = list(completed)
                        self._checkpoint["completed_tickers"][symbol] = prog
                        self._save_checkpoint()
            except Exception as e:
                log.error(f"[{symbol}] Broker summary {d} failed: {e}")
            finally:
                client._get = orig_get

        with self._checkpoint_lock:
            prog["broker_summary_dates"] = list(completed)
            self._checkpoint["completed_tickers"][symbol] = prog
            self._save_checkpoint()

        log.info(f"[{symbol}] Broker summary done: {ok} fetched, {skip} skipped.")
        return True

    def _backload_intraday(self, symbol: str, start_date: str, end_date: str) -> bool:
        client = _get_worker_client(self.headers_path)
        parser = _get_worker_parser(self.db_dsn)
        trading_dates = self._get_trading_dates(symbol, start_date, end_date)
        if not trading_dates:
            log.warning(f"[{symbol}] Tidak ada trading dates — intraday dilewati.")
            return False

        completed = set()
        with self._checkpoint_lock:
            prog = self._checkpoint["completed_tickers"].get(symbol, {})
            completed = set(prog.get("intraday_dates", []))

        ok, skip = 0, 0
        for d in trading_dates:
            # Idempoten: skip jika ada di checkpoint ATAU sudah ada di DB
            d_str = d if isinstance(d, str) else d.isoformat()
            if d_str in completed or self._intraday_exists(symbol, d_str):
                completed.add(d_str)
                skip += 1
                continue
            try:
                dt_s = datetime.strptime(d_str, "%Y-%m-%d")
                dt_e = dt_s + timedelta(days=1) - timedelta(seconds=1)
                from_unix = int(dt_s.timestamp())
                to_unix   = int(dt_e.timestamp())
            except Exception as e:
                log.error(f"[{symbol}] Invalid date {d_str}: {e}")
                continue

            try:
                # API: from = end of day (newer), to = start of day (older)
                payload, url = self._api_call(
                    client, "get_intraday_candles",
                    {"symbol": symbol, "from_unix": to_unix, "to_unix": from_unix, "limit": 0},
                )
                parser.parse_payload(url, payload)
                completed.add(d_str)
                ok += 1
                if ok % 10 == 0:
                    with self._checkpoint_lock:
                        prog["intraday_dates"] = list(completed)
                        self._checkpoint["completed_tickers"][symbol] = prog
                        self._save_checkpoint()
            except Exception as e:
                log.error(f"[{symbol}] Intraday {d_str} failed: {e}")

        with self._checkpoint_lock:
            prog["intraday_dates"] = list(completed)
            self._checkpoint["completed_tickers"][symbol] = prog
            self._save_checkpoint()

        log.info(f"[{symbol}] Intraday done: {ok} fetched, {skip} skipped.")
        return True

    def _backload_running_trades(self, symbol: str, start_date: str, end_date: str) -> bool:
        client = _get_worker_client(self.headers_path)
        parser = _get_worker_parser(self.db_dsn)
        trading_dates = self._get_trading_dates(symbol, start_date, end_date)
        if not trading_dates:
            log.warning(f"[{symbol}] Tidak ada trading dates — running trades dilewati.")
            return False

        completed = set()
        with self._checkpoint_lock:
            prog = self._checkpoint["completed_tickers"].get(symbol, {})
            completed = set(prog.get("running_trades_dates", []))

        ok, skip = 0, 0
        limit = 100

        for d in trading_dates:
            # Idempoten: skip jika ada di checkpoint (sumber kebenaran kelengkapan)
            d_str = d if isinstance(d, str) else d.isoformat()
            if d_str in completed:
                skip += 1
                continue

            log.info(f"[{symbol}] Running trades scroll pagination: {d_str} ...")
            page, last_trade_num, day_total = 1, None, 0
            success = True

            while True:
                kwargs = {"symbols": [symbol], "date": d_str, "limit": limit}
                if last_trade_num:
                    kwargs["trade_number"] = last_trade_num
                    kwargs["cursor_direction"] = "CURSOR_DIRECTION_NEXT"

                try:
                    payload, url = self._api_call(client, "get_running_trade", kwargs)
                except Exception as e:
                    log.error(f"[{symbol}] Running trades {d_str} page {page} failed: {e}")
                    success = False
                    break

                trades = payload.get("data", {}).get("running_trade", [])
                if not trades:
                    break

                parser.parse_payload(url, payload)
                day_total += len(trades)
                last_trade_num = trades[-1].get("trade_number")
                last_time_str  = trades[-1].get("time", "")

                log.info(f"[{symbol}] RT {d_str} page {page}: {len(trades)} trades. Last time: {last_time_str}")

                if len(trades) < limit:
                    break  # Halaman terakhir
                if last_time_str and last_time_str < "08:50:00":
                    break  # Sudah melewati pre-opening

                page += 1

            if success:
                log.info(f"[{symbol}] RT {d_str} selesai: {day_total} trades total.")
                completed.add(d_str)
                ok += 1
                if ok % 5 == 0:
                    with self._checkpoint_lock:
                        prog["running_trades_dates"] = list(completed)
                        self._checkpoint["completed_tickers"][symbol] = prog
                        self._save_checkpoint()
            else:
                log.warning(f"[{symbol}] RT {d_str} tidak selesai karena kesalahan jaringan/API. Checkpoint dilewati.")

        with self._checkpoint_lock:
            prog["running_trades_dates"] = list(completed)
            self._checkpoint["completed_tickers"][symbol] = prog
            self._save_checkpoint()

        log.info(f"[{symbol}] Running trades done: {ok} fetched, {skip} skipped.")
        return True

    # ------------------------------------------------------------------
    # Per-ticker orchestration
    # ------------------------------------------------------------------

    def backload_ticker(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data_types: list,
        ohlcv_ready_event: threading.Event = None,
    ) -> bool:
        """
        Jalankan seluruh pipeline backload untuk satu ticker.

        ohlcv_ready_event: Event yang di-set setelah OHLCV selesai disimpan.
        Hanya digunakan jika worker ini bertanggung jawab memicu event tersebut.
        """
        log.info("=" * 70)
        log.info(f" BACKLOAD: {symbol}")
        log.info("=" * 70)

        with self._checkpoint_lock:
            if symbol not in self._checkpoint["completed_tickers"]:
                self._checkpoint["completed_tickers"][symbol] = {}
            prog = self._checkpoint["completed_tickers"][symbol]

        # 1. OHLCV Daily (harus selesai dulu jika ada downstream dependency)
        if "ohlcv" in data_types:
            if not prog.get("ohlcv_completed"):
                success = self._backload_ohlcv(symbol, start_date, end_date)
                if success:
                    with self._checkpoint_lock:
                        prog["ohlcv_completed"] = True
                        self._save_checkpoint()
                else:
                    log.error(f"[{symbol}] OHLCV gagal — skip downstream.")
                    if ohlcv_ready_event:
                        ohlcv_ready_event.set()  # Tetap signal agar tidak deadlock
                    return False
            else:
                log.info(f"[{symbol}] OHLCV sudah selesai (checkpoint). Dilewati.")

        # Signal bahwa OHLCV sudah siap di DB
        if ohlcv_ready_event:
            ohlcv_ready_event.set()

        # 2. Foreign Flow
        if "foreign-flow" in data_types and not prog.get("foreign_flow_completed"):
            if self._backload_foreign_flow(symbol, start_date, end_date):
                with self._checkpoint_lock:
                    prog["foreign_flow_completed"] = True
                    self._save_checkpoint()

        # 3. Broker Summary (butuh OHLCV dates di DB)
        if "broker-summary" in data_types:
            if self._backload_broker_summary(symbol, start_date, end_date):
                with self._checkpoint_lock:
                    prog["broker_summary_completed"] = True
                    self._save_checkpoint()

        # 4. Intraday 1m Candles — selalu masuk per-date loop (idempoten via DB check)
        if "intraday" in data_types:
            self._backload_intraday(symbol, start_date, end_date)

        # 5. Running Trades — selalu masuk per-date loop (idempoten via DB check)
        if "running-trade" in data_types:
            self._backload_running_trades(symbol, start_date, end_date)

        log.info(f"[{symbol}] Backload selesai.")
        return True


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="High-performance Stockbit historical data backloader."
    )
    ap.add_argument("--symbols",     required=True,
                    help="Comma-separated symbols or group name (LQ45, MSCI, BLUECHIP, CONGLOMERATE, ALL)")
    ap.add_argument("--start-date",  default=DEFAULT_START_DATE,
                    help=f"Start date YYYY-MM-DD (default: {DEFAULT_START_DATE})")
    ap.add_argument("--end-date",    default=DEFAULT_END_DATE,
                    help=f"End date YYYY-MM-DD (default: {DEFAULT_END_DATE})")
    ap.add_argument("--data-types",
                    default="ohlcv,broker-summary,foreign-flow,intraday,running-trade",
                    help="Comma-separated data types to backload")
    ap.add_argument("--workers",     type=int, default=4,
                    help="Number of concurrent worker threads (default: 4)")
    ap.add_argument("--delay-ms",    type=int, default=DEFAULT_DELAY_MS,
                    help=f"Target ms between API requests (default: {DEFAULT_DELAY_MS})")
    ap.add_argument("--max-connections", type=int, default=None,
                    help="Max DB pool connections (default: workers*2+2)")
    ap.add_argument("--db",          default=None,
                    help="PostgreSQL DSN (default: DATABASE_URL env)")
    ap.add_argument("--dry-run",     action="store_true",
                    help="Plan only, no API calls")
    args = ap.parse_args()

    # Validate data types
    valid_types = {"ohlcv", "broker-summary", "foreign-flow", "intraday", "running-trade"}
    selected = [t.strip().lower() for t in args.data_types.split(",") if t.strip()]
    for t in selected:
        if t not in valid_types:
            log.error(f"Invalid data type: '{t}'. Valid: {', '.join(sorted(valid_types))}")
            return

    # Build backloader (initialises pool at this point)
    backloader = StockbitBackloader(
        db_dsn=args.db,
        delay_ms=args.delay_ms,
        workers=args.workers,
        max_connections=args.max_connections,
    )

    # Resolve symbols
    raw = args.symbols.strip()
    symbols = backloader.get_ticker_group_symbols(raw)
    if not symbols:
        symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not symbols:
        log.error(f"Tidak ada symbol ditemukan untuk '{args.symbols}'. Aborting.")
        return

    log.info("=" * 70)
    log.info(" STOCKBIT HISTORICAL BACKLOADER")
    log.info("=" * 70)
    log.info(f" Symbols   : {len(symbols)} tickers")
    log.info(f" Date range: {args.start_date} --> {args.end_date}")
    log.info(f" Types     : {', '.join(selected)}")
    log.info(f" Workers   : {args.workers}")
    log.info(f" Delay     : {args.delay_ms} ms")
    log.info(f" Dry run   : {args.dry_run}")
    log.info("=" * 70)

    if args.dry_run:
        log.info("Dry-run complete. No API calls made.")
        return

    success_list, failed_list = [], []

    try:
        if args.workers == 1:
            log.info("Running in SEQUENTIAL mode.")
            for sym in symbols:
                try:
                    ok = backloader.backload_ticker(sym, args.start_date, args.end_date, selected)
                    (success_list if ok else failed_list).append(sym)
                except Exception as e:
                    log.error(f"Fatal error backloading {sym}: {e}")
                    failed_list.append(sym)
        else:
            log.info(f"Running in MULTI-THREADED mode ({args.workers} workers).")
            # Per-symbol OHLCV ready events (hanya relevan jika ohlcv di data_types)
            ohlcv_events = {sym: threading.Event() for sym in symbols}
            if "ohlcv" not in selected:
                for ev in ohlcv_events.values():
                    ev.set()  # Tidak perlu tunggu OHLCV

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers,
                thread_name_prefix="backloader",
            ) as executor:
                future_map = {
                    executor.submit(
                        backloader.backload_ticker,
                        sym,
                        args.start_date,
                        args.end_date,
                        selected,
                        ohlcv_events[sym],
                    ): sym
                    for sym in symbols
                }
                for future in concurrent.futures.as_completed(future_map):
                    sym = future_map[future]
                    try:
                        ok = future.result()
                        (success_list if ok else failed_list).append(sym)
                    except Exception as e:
                        log.error(f"Fatal error backloading {sym}: {e}")
                        failed_list.append(sym)

    except KeyboardInterrupt:
        log.info("Interrupted. Saving checkpoint ...")
        with backloader._checkpoint_lock:
            backloader._save_checkpoint()
        sys.exit(0)

    # Summary
    log.info("")
    log.info("=" * 70)
    log.info(" BACKLOAD COMPLETE")
    log.info("=" * 70)
    log.info(f" Success: {len(success_list)}/{len(symbols)}")
    if failed_list:
        log.warning(f" Failed : {', '.join(failed_list)}")

    # Post-load DB maintenance
    log.info("Running DB maintenance ...")
    try:
        db = StockbitDbManager(args.db)
        report = db.clean_database()
        log.info(f"  Cleaned: {report.get('trade_book_duplicates_deleted',0)} dups, "
                 f"{report.get('orphan_orderbook_ticks_deleted',0)} orphans.")
        db.optimize_database()
        log.info("  VACUUM + ANALYZE done.")
    except Exception as e:
        log.warning(f"DB maintenance warning: {e}")

    # Shutdown connection pool cleanly
    BaseRepository.close_pool()
    log.info("Connection pool closed. All done.")


if __name__ == "__main__":
    main()
