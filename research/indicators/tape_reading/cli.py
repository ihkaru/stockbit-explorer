import sys
import psycopg2
import logging
import os
from dotenv import load_dotenv
from .analyzer import TapeReadingAnalyzer

# Load environment variables
load_dotenv()

# Setup logger for CLI run
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def demo_from_database(symbol: str = "BBCA", window: int = 300):
    """Demo analisis Tape Reading menggunakan data historis dari database PostgreSQL."""
    print(f"\n{'#' * 70}")
    print(f"  DEMO TAPE READING ANALYZER")
    print(f"  Saham: {symbol} | Window: {window} transaksi terakhir")
    print(f"{'#' * 70}")
    
    analyzer = TapeReadingAnalyzer()
    
    # Cek ketersediaan data
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
    )
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM running_trades WHERE symbol=%s", [symbol])
            total = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"\n  [ERROR] Gagal terhubung ke database PostgreSQL: {e}")
        return None
    
    if total == 0:
        print(f"\n  [TIDAK ADA DATA] Tidak ditemukan data running trade untuk {symbol} di database.")
        print(f"  Jalankan interceptor / API fetch terlebih dahulu untuk merekam data.")
        return None
    
    print(f"\n  [INFO] Total transaksi {symbol} di database: {total:,}")
    print(f"  [INFO] Menganalisis {window} transaksi terakhir...")
    
    result = analyzer.analyze(symbol=symbol, limit=window)
    analyzer.print_report(result)
    
    return result


def batch_analysis(symbols: list, window: int = 300):
    """Analisis sekelompok saham dan cetak sinyalnya."""
    analyzer = TapeReadingAnalyzer()
    
    print("\n" + "=" * 70)
    print(f"  BATCH ANALYSIS SUMMARY ({len(symbols)} saham)")
    print("=" * 70)
    print(f"  {'Symbol':<8} {'Signal':<8} {'Strength':<10} {'HAKA%':>7} {'HAKA Lot':>12} {'HAKI Lot':>12} {'S-Lots':>8}")
    print(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*7} {'-'*12} {'-'*12} {'-'*8}")
    
    results = []
    for symbol in symbols:
        r = analyzer.analyze(symbol=symbol, limit=window)
        results.append(r)
        signal_icon = {"BUY": "[BUY]", "SELL": "[SELL]", "NEUTRAL": "[NTRL]"}.get(r.signal, r.signal)
        print(f"  {r.symbol:<8} {signal_icon:<8} {r.signal_strength:<10} "
              f"{r.haka_ratio:>6.1%} {r.haka_lot:>12.1f} {r.haki_lot:>12.1f} "
              f"{len(r.s_lot_groups):>8}")
    
    print("=" * 70)
    
    # Saham terbaik berdasarkan HAKA ratio
    valid_results = [r for r in results if r.signal not in ("INSUFFICIENT_DATA",)]
    if valid_results:
        best = max(valid_results, key=lambda r: r.haka_ratio)
        worst = min(valid_results, key=lambda r: r.haka_ratio)
        print(f"\n  >> Saham Akumulasi Terkuat : {best.symbol} ({best.haka_ratio:.1%})")
        print(f"  >> Saham Distribusi Terkuat: {worst.symbol} ({worst.haka_ratio:.1%})")
    
    return results


if __name__ == "__main__":
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
        print("        Pastikan container PostgreSQL + TimescaleDB sudah berjalan.")
        sys.exit(1)
    
    if not rows:
        print("\n[ERROR] Database kosong. Tidak ada data running trade yang ditemukan.")
        print("        Jalankan interceptor dan biarkan data terekam, kemudian jalankan parser.py dulu.")
        sys.exit(1)
    
    symbols = [r[0] for r in rows]
    
    print("\n" + "#" * 70)
    print("  TAPE READING ANALYZER - STOCKBIT EXPLORER")
    print(f"  Data tersedia untuk: {', '.join(symbols)}")
    print("#" * 70)
    
    # Demo detail satu saham
    primary_symbol = symbols[0]
    demo_from_database(symbol=primary_symbol, window=500)
    
    # Analisis batch semua saham di database
    if len(symbols) > 1:
        batch_analysis(symbols=symbols, window=300)

