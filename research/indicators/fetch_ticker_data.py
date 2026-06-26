import os
import sys
import json
import time
import argparse
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable proxy settings from environment to connect directly
os.environ['HTTP_PROXY'] = ""
os.environ['HTTPS_PROXY'] = ""
os.environ['http_proxy'] = ""
os.environ['https_proxy'] = ""

# Ensure research/indicators is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_client import StockbitApiClient
from parser.stockbit_parser import StockbitParser
from db_manager import StockbitDbManager

def get_db_counts(dsn, tables):
    """Mendapatkan jumlah baris untuk setiap tabel di database PostgreSQL."""
    counts = {}
    try:
        # Fallback default DSN if None
        dsn = dsn or os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
        )
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cursor.fetchone()[0]
            except Exception:
                counts[t] = 0
        conn.close()
    except Exception:
        for t in tables:
            counts[t] = 0
    return counts

def main():
    parser_args = argparse.ArgumentParser(description="Fetch and load all data for a single ticker to PostgreSQL.")
    parser_args.add_argument("--symbol", type=str, default="BBCA", help="Ticker Saham (e.g. BBCA, GOTO, TLKM)")
    parser_args.add_argument("--date", type=str, default=None, help="Tanggal analisis (format YYYY-MM-DD). Default kemaren.")
    parser_args.add_argument("--db", type=str, default=None, help="DSN PostgreSQL (e.g. postgresql://postgres:postgres@localhost:5432/stockbit_explorer)")
    args = parser_args.parse_args()

    symbol = args.symbol.upper()
    db_path = args.db
    
    # Tentukan tanggal default (kemarin) jika tidak diberikan
    if not args.date:
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%Y-%m-%d")
    else:
        date_str = args.date

    print("=" * 80)
    db_desc = db_path or os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:6432/stockbit_explorer")
    print(f" FETCHING ALL STOCKBIT DATA FOR {symbol} ON {date_str}")
    print(f" Target Database: {db_desc}")
    print("=" * 80)

    # 1. Inisialisasi Database, Client, dan Parser
    db = StockbitDbManager(db_path)
    parser = StockbitParser(db_path=db_path)
    
    try:
        client = StockbitApiClient()
    except Exception as e:
        print(f"[ERROR] Gagal inisialisasi API client: {e}")
        print("Pastikan token Stockbit di 'STOCKBIT_HEADERS_PATH' atau 'data/session_headers.json' valid.")
        return

    # Daftar tabel yang dipantau
    tables_to_monitor = [
        "running_trades", "trade_book", "broker_summaries", "price_grids", "ohlcv_data",
        "brokers", "watchlists", "watchlist_items", "broker_daily_activity",
        "orderbook_snapshots", "orderbook_ticks", "order_queues",
        "company_profiles", "company_executives", "company_shareholders", "company_beneficiaries",
        "company_shareholder_stats", "company_shareholding_compositions", "company_insider_transactions",
        "company_keystats", "company_dividends", "company_analyst_ratings"
    ]

    # Rekam jumlah data sebelum penarikan
    counts_before = get_db_counts(db_path, tables_to_monitor)

    # Hitung unix timestamp untuk parameter intraday candle
    try:
        dt_start = datetime.strptime(date_str, "%Y-%m-%d")
        dt_end = dt_start + timedelta(days=1) - timedelta(seconds=1)
        from_unix = int(dt_start.timestamp())
        to_unix = int(dt_end.timestamp())
    except Exception as e:
        print(f"[ERROR] Format tanggal salah: {e}")
        return

    # 2. Definisikan pemanggilan API
    api_calls = [
        # Metadata dasar emiten
        ("get_company_info", {"symbol": symbol}),
        ("get_company_profile", {"symbol": symbol}),
        ("get_insider_composition", {"symbol": symbol}),
        ("get_insider_majorholders", {"symbol": symbol}),
        ("get_keystats", {"symbol": symbol}),
        ("get_analyst_consensus", {"symbol": symbol}),
        ("get_analyst_ratings", {"symbol": symbol}),
        # Market Data EOD & Histori
        ("get_prices", {"stock_code": symbol}),
        ("get_market_detector", {"stock_code": symbol, "from_date": date_str, "to_date": date_str}),
        ("get_historical_summary", {"symbol": symbol, "limit": 30}),
        ("get_daily_candles", {"symbol": symbol, "from_date": date_str, "to_date": date_str, "limit": 0}),
        ("get_intraday_candles", {"symbol": symbol, "from_unix": from_unix, "to_unix": to_unix, "limit": 0}),
        # Real-time / EOD Snapshots
        ("get_running_trade", {"symbols": [symbol], "date": date_str, "limit": 0}),
        ("get_trade_book", {"symbol": symbol}),
        ("get_orderbook", {"symbol": symbol}),
        ("get_foreign_domestic_chart", {"symbol": symbol})
    ]

    temp_jsonl_path = "data/raw/temp_fetch_ticker.jsonl"
    if os.path.exists(temp_jsonl_path):
        os.remove(temp_jsonl_path)

    # 3. Pemicuan API & Rekam ke file JSONL Sementara
    print(f"\n[STEP 1] Memulai penarikan data dari Stockbit API...")
    success_count = 0
    failure_count = 0

    with open(temp_jsonl_path, "a", encoding="utf-8") as temp_file:
        for method_name, kwargs in api_calls:
            if not hasattr(client, method_name):
                print(f"  [ERROR] Method '{method_name}' tidak ditemukan di API Client.")
                failure_count += 1
                continue

            method = getattr(client, method_name)
            print(f"  Memanggil '{method_name}' dengan parameter {kwargs}...", end="", flush=True)

            try:
                # Spy URL untuk pencatatan URL asli
                orig_get = client._get
                last_url = ""
                def spy_get(url, params=None):
                    nonlocal last_url
                    last_url = url
                    if params:
                        from urllib.parse import urlencode
                        last_url = f"{url}?{urlencode(params, doseq=True)}"
                    return orig_get(url, params)
                
                client._get = spy_get
                payload = method(**kwargs)
                client._get = orig_get # restore

                log_entry = {
                    "timestamp": time.time(),
                    "url": last_url or f"https://exodus.stockbit.com/fallback/{method_name}",
                    "payload": payload
                }
                temp_file.write(json.dumps(log_entry) + "\n")
                print(" OK.")
                success_count += 1
            except Exception as e:
                print(f" GAGAL: {e}")
                failure_count += 1
                client._get = orig_get

    # 4. Parsing dan Ingest ke Database
    print(f"\n[STEP 2] Mem-parsing berkas log mentah dan memuatnya ke PostgreSQL...")
    if os.path.exists(temp_jsonl_path) and os.path.getsize(temp_jsonl_path) > 0:
        try:
            parser.parse_file(temp_jsonl_path)
            print("  [SUCCESS] Selesai mem-parsing dan memuat data.")
        except Exception as e:
            print(f"  [ERROR] Gagal mem-parsing data: {e}")
    else:
        print("  [WARNING] File log kosong, tidak ada data untuk di-parsing.")

    # Hapus file JSONL sementara
    if os.path.exists(temp_jsonl_path):
        os.remove(temp_jsonl_path)

    # 4.5. Pembersihan data tidak valid & optimasi database pasca-penarikan
    print(f"\n[STEP 2.5] Menjalankan pembersihan integritas dan optimasi database...")
    try:
        clean_report = db.clean_database()
        t_del = clean_report["trade_book_duplicates_deleted"]
        o_del = clean_report["orphan_orderbook_ticks_deleted"]
        if t_del > 0 or o_del > 0:
            print(f"  [SUCCESS] Berhasil menghapus {t_del} duplikat trade_book dan {o_del} orphan orderbook_ticks.")
        else:
            print("  [INFO] Database bersih, tidak ada duplikat atau orphan ticks yang dihapus.")
            
        db.optimize_database()
        print("  [SUCCESS] Indeks database diperbarui dan ukuran dirampingkan (VACUUM & ANALYZE).")
    except Exception as e:
        print(f"  [WARNING] Gagal menjalankan optimasi pasca-penarikan: {e}")

    # 5. Dapatkan Jumlah Baris Setelah Ingesti & Laporkan Perubahan
    counts_after = get_db_counts(db_path, tables_to_monitor)
    
    print(f"\n[STEP 3] LAPORAN PERUBAHAN DATABASE:")
    print("-" * 70)
    print(f" {'Nama Tabel':<35} | {'Sebelum':<10} | {'Sesudah':<10} | {'Tambahan':<10}")
    print("-" * 70)
    
    total_added = 0
    for t in tables_to_monitor:
        diff = counts_after[t] - counts_before[t]
        total_added += diff
        print(f" {t:<35} | {counts_before[t]:<10} | {counts_after[t]:<10} | +{diff:<10}")
    print("-" * 70)

    print(f"\nAPI Calls Sukses : {success_count}")
    print(f"API Calls Gagal  : {failure_count}")
    print(f"Total baris data baru ditambahkan ke database: {total_added}")
    print("=" * 80)

if __name__ == "__main__":
    main()
