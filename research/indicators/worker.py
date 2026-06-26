# Real-time Background Ingestion Worker for Stockbit Explorer

import os
import sys
import json
import time
import glob
import logging
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv

# Ensure current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Load environment variables
load_dotenv()

from db_manager import StockbitDbManager
from parser.dispatcher import dispatch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [WORKER] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("data", "worker.log"), encoding="utf-8")
    ]
)

class LogTailerWorker:
    def __init__(self, raw_dir="data/raw", db_dsn=None, poll_interval_sec=1.0):
        self.raw_dir = raw_dir
        self.db = StockbitDbManager(db_dsn)
        self.poll_interval = poll_interval_sec
        # Maps file path to its last read offset (byte position)
        self.file_offsets = {}
        logging.info("Real-time Ingestion Worker initialized.")
        logging.info(f"Watching directory: {os.path.abspath(raw_dir)}")

    def process_line(self, file_path, line):
        """Parses a single JSONL line and inserts data into PostgreSQL immediately."""
        if not line.strip():
            return
        
        try:
            entry = json.loads(line.strip())
            url = entry.get("url", "")
            payload = entry.get("payload", {})
            timestamp = entry.get("timestamp", time.time())
            
            if not url or not payload:
                return
                
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Execute the parser dispatcher
            batch_data = dispatch(self.db, path, parsed_url, payload, timestamp)
            
            # If dispatcher returned batched records, write them immediately
            if batch_data:
                if "trades" in batch_data and batch_data["trades"]:
                    inserted = self.db.insert_running_trades(batch_data["trades"])
                    if inserted > 0:
                        logging.debug(f"[{os.path.basename(file_path)}] Inserted {inserted} running trades.")
                elif "broker_summaries" in batch_data and batch_data["broker_summaries"]:
                    inserted = self.db.insert_broker_summaries(batch_data["broker_summaries"])
                    if inserted > 0:
                        logging.debug(f"[{os.path.basename(file_path)}] Inserted {inserted} broker summaries.")
                        
        except Exception as e:
            logging.debug(f"Failed to process log line from {os.path.basename(file_path)}: {e}")

    def tail_file(self, file_path):
        """Reads new lines from a file from the last saved offset position."""
        try:
            current_size = os.path.getsize(file_path)
        except OSError:
            # File might have been deleted/rotated
            self.file_offsets.pop(file_path, None)
            return

        last_offset = self.file_offsets.get(file_path, 0)

        # Handle file rotation/truncation
        if current_size < last_offset:
            logging.info(f"File {os.path.basename(file_path)} truncated/rotated. Resetting offset to start.")
            last_offset = 0

        if current_size == last_offset:
            # No new data
            return

        # Read new lines
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                f.seek(last_offset)
                for line in f:
                    self.process_line(file_path, line)
                # Save new byte position
                self.file_offsets[file_path] = f.tell()
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")

    def scan_and_process(self):
        """Scans the raw data folder and tails all active JSONL files."""
        os.makedirs(self.raw_dir, exist_ok=True)
        search_pattern = os.path.join(self.raw_dir, "*.jsonl")
        files = glob.glob(search_pattern)

        for file_path in files:
            # Skip temporary files written by backloader or fetch scripts
            filename = os.path.basename(file_path)
            if filename.startswith("temp") or "temp_" in filename:
                continue

            self.tail_file(file_path)

    def start(self):
        """Starts the main worker polling loop."""
        logging.info("Ingestion polling loop started. Press Ctrl+C to stop.")
        
        # Initial scan to record starting file sizes
        # This prevents ingesting massive existing files from start on startup, unless desired.
        # But we want to ingest any existing logs if they haven't been tracked.
        # So we default to starting at current offsets on fresh run.
        os.makedirs(self.raw_dir, exist_ok=True)
        for f in glob.glob(os.path.join(self.raw_dir, "*.jsonl")):
            filename = os.path.basename(f)
            if filename.startswith("temp") or "temp_" in filename:
                continue
            try:
                self.file_offsets[f] = os.path.getsize(f)
                logging.info(f"Tracking existing log file: {filename} at offset {self.file_offsets[f]} bytes.")
            except OSError:
                pass

        while True:
            try:
                self.scan_and_process()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logging.info("Worker stopped by user.")
                break
            except Exception as e:
                logging.error(f"Error in worker polling loop: {e}")
                time.sleep(2.0)  # Sleep longer on loop errors

if __name__ == "__main__":
    # Allow overriding directories via arguments
    parser_arg = argparse.ArgumentParser(description="Stockbit Ingestion Daemon Worker.")
    parser_arg.add_argument("--raw-dir", type=str, default="data/raw", help="Path to raw jsonl directory")
    parser_arg.add_argument("--db", type=str, default=None, help="Database DSN")
    parser_arg.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    
    args = parser_arg.parse_args()
    
    worker = LogTailerWorker(
        raw_dir=args.raw_dir,
        db_dsn=args.db,
        poll_interval_sec=args.interval
    )
    worker.start()
