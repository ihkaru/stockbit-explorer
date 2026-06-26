import sys
import os

# Menambahkan direktori saat ini ke sys.path jika belum ada untuk memudahkan modul parser ditemukan
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from parser.stockbit_parser import StockbitParser
except ImportError:
    from .parser.stockbit_parser import StockbitParser

if __name__ == "__main__":
    parser = StockbitParser()
    parser.parse_all_raw_files()
