import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Menambahkan direktori saat ini ke sys.path jika belum ada untuk memudahkan modul tape_reading ditemukan
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from tape_reading.analyzer import TapeReadingAnalyzer
    from tape_reading.models import TradeTick, VolumeCategory, SLotGroup, HAKAHAKIResult
except ImportError:
    from .tape_reading.analyzer import TapeReadingAnalyzer
    from .tape_reading.models import TradeTick, VolumeCategory, SLotGroup, HAKAHAKIResult

if __name__ == "__main__":
    try:
        from tape_reading.cli import demo_from_database, batch_analysis
    except ImportError:
        from .tape_reading.cli import demo_from_database, batch_analysis
    import psycopg2
    import os
    
    tickers_in_db_query = """
        SELECT symbol, COUNT(*) as cnt
        FROM running_trades
        GROUP BY symbol
        ORDER BY cnt DESC
    """
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
    )
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cursor:
            cursor.execute(tickers_in_db_query)
            rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Gagal terhubung ke database PostgreSQL: {e}")
        sys.exit(1)
    
    if not rows:
        print("\n[ERROR] Database kosong. Tidak ada data running trade yang ditemukan.")
        sys.exit(1)
        
    symbols = [r[0] for r in rows]
    
    print("\n" + "#" * 70)
    print("  TAPE READING ANALYZER - STOCKBIT EXPLORER (SHIM)")
    print(f"  Data tersedia untuk: {', '.join(symbols)}")
    print("#" * 70)
    
    primary_symbol = symbols[0]
    demo_from_database(symbol=primary_symbol, window=500)
    
    if len(symbols) > 1:
        batch_analysis(symbols=symbols, window=300)
