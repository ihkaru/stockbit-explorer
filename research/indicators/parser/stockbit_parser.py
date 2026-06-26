import json
import os
import glob
import time
import logging
from urllib.parse import urlparse
from db_manager import StockbitDbManager
from .dispatcher import dispatch


class StockbitParser:
    """
    Parser untuk memproses log WebSocket/HTTP Stockbit mentah ke PostgreSQL.

    Mendukung dua mode operasi:
      - parse_file()    : baca file JSONL dari disk (workflow mitmdump/offline).
      - parse_payload() : parse payload langsung dari memory tanpa I/O disk
                          (workflow backloader multi-thread).
    """

    def __init__(self, raw_dir="data/raw", db_path=None):
        self.raw_dir = raw_dir
        self.db = StockbitDbManager(db_path)

    # ------------------------------------------------------------------
    # In-memory parsing (untuk backloader multi-thread — tanpa temp file)
    # ------------------------------------------------------------------

    def parse_payload(self, url: str, payload: dict, timestamp: float = None) -> dict:
        """
        Parse satu API response payload langsung dari memory.

        Tidak menulis file apapun ke disk sehingga aman dipanggil dari banyak
        thread secara bersamaan (setiap thread punya instance parser sendiri).

        Args:
            url      : URL endpoint yang menghasilkan payload.
            payload  : Dict response body dari API.
            timestamp: Unix timestamp request. Default: waktu sekarang.

        Returns:
            dict dengan kunci "trades_inserted" dan "summaries_inserted"
            menunjukkan jumlah baris yang berhasil disimpan.
        """
        ts = timestamp or time.time()
        parsed_url = urlparse(url)
        path = parsed_url.path

        try:
            batch_data = dispatch(self.db, path, parsed_url, payload, ts)
        except Exception as e:
            logging.error(f"[parse_payload] Dispatcher error untuk '{path}': {e}")
            return {"trades_inserted": 0, "summaries_inserted": 0}

        trades_inserted = 0
        summaries_inserted = 0

        if batch_data:
            trades = batch_data.get("trades") or []
            summaries = batch_data.get("broker_summaries") or []

            if trades:
                try:
                    trades_inserted = self.db.insert_running_trades(trades)
                    logging.debug(f"[parse_payload] Inserted {trades_inserted} running trades ({path})")
                except Exception as e:
                    logging.error(f"[parse_payload] insert_running_trades error: {e}")

            if summaries:
                try:
                    summaries_inserted = self.db.insert_broker_summaries(summaries)
                    logging.debug(f"[parse_payload] Inserted {summaries_inserted} broker summaries ({path})")
                except Exception as e:
                    logging.error(f"[parse_payload] insert_broker_summaries error: {e}")

        return {"trades_inserted": trades_inserted, "summaries_inserted": summaries_inserted}

    # ------------------------------------------------------------------
    # File-based parsing (workflow mitmdump / offline replay)
    # ------------------------------------------------------------------

    def parse_all_raw_files(self):
        """Membaca dan memproses seluruh berkas .jsonl dalam folder data/raw/."""
        search_pattern = os.path.join(self.raw_dir, "*.jsonl")
        jsonl_files = glob.glob(search_pattern)

        if not jsonl_files:
            logging.info("Tidak ada file mentah (.jsonl) yang ditemukan di folder data/raw/.")
            return

        logging.info(f"Ditemukan {len(jsonl_files)} file mentah untuk diproses.")

        for file_path in jsonl_files:
            logging.info(f"Memproses file: {file_path}")
            self.parse_file(file_path)

    def parse_file(self, file_path: str):
        """Memproses satu file JSONL baris demi baris."""
        trades_to_insert = []
        broker_summaries_to_insert = []
        total_rows_processed = 0

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                path = ""
                try:
                    entry = json.loads(line.strip())
                    url = entry.get("url", "")
                    payload = entry.get("payload", {})
                    timestamp = entry.get("timestamp", time.time())

                    parsed_url = urlparse(url)
                    path = parsed_url.path

                    batch_data = dispatch(self.db, path, parsed_url, payload, timestamp)

                    if batch_data:
                        if batch_data.get("trades"):
                            trades_to_insert.extend(batch_data["trades"])
                        if batch_data.get("broker_summaries"):
                            broker_summaries_to_insert.extend(batch_data["broker_summaries"])

                    total_rows_processed += 1
                except Exception as e:
                    path_info = f" untuk path '{path}'" if path else ""
                    logging.debug(f"Gagal memparsing baris{path_info} pada file {file_path}: {e}")

        if trades_to_insert:
            inserted = self.db.insert_running_trades(trades_to_insert)
            logging.info(f"  -> Berhasil menyimpan {inserted} running trades baru ke database.")

        if broker_summaries_to_insert:
            inserted = self.db.insert_broker_summaries(broker_summaries_to_insert)
            logging.info(f"  -> Berhasil menyimpan/mengupdate {inserted} data EOD broker summaries ke database.")

        logging.info(f"Selesai memproses {file_path}. Total log rows: {total_rows_processed}")
