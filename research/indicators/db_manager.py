import sys
import os

# Menambahkan direktori saat ini ke sys.path jika belum ada untuk memudahkan modul db ditemukan
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from db.manager import StockbitDbManager
except ImportError:
    from .db.manager import StockbitDbManager
