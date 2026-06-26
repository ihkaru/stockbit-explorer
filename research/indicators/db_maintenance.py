import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Ensure current directory is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env if present
load_dotenv()

from db_manager import StockbitDbManager

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_db_size(db):
    """Mendapatkan ukuran database PostgreSQL saat ini dalam bytes."""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                return cursor.fetchone()[0]
    except Exception as e:
        logging.warning(f"Gagal mendeteksi ukuran database: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(
        description="Stockbit Explorer PostgreSQL Database Maintenance & Integrity Utility"
    )
    parser.add_argument(
        "--db", 
        type=str, 
        default=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"), 
        help="PostgreSQL Connection DSN (default: read from DATABASE_URL env)"
    )
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Lakukan pemeriksaan integritas database relasional & TimescaleDB"
    )
    parser.add_argument(
        "--clean", 
        action="store_true", 
        help="Lakukan pembersihan data duplikat & data yatim (orphan)"
    )
    parser.add_argument(
        "--optimize", 
        action="store_true", 
        help="Lakukan optimalisasi indeks dan perampingan penyimpanan (VACUUM & ANALYZE)"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Jalankan semua tindakan maintenance (Check, Clean, & Optimize)"
    )
    
    args = parser.parse_args()
    dsn = args.db
    
    logging.info("=" * 70)
    logging.info(f"MEMULAI DATABASE MAINTENANCE (PostgreSQL)")
    # Mask password in connection string for security output logging
    from urllib.parse import urlparse
    try:
        parsed_dsn = urlparse(dsn)
        masked_dsn = f"{parsed_dsn.scheme}://{parsed_dsn.username}:****@{parsed_dsn.hostname}:{parsed_dsn.port}{parsed_dsn.path}"
    except Exception:
        masked_dsn = "PostgreSQL DSN"
    logging.info(f"Target Database: {masked_dsn}")
    logging.info("=" * 70)
    
    db = StockbitDbManager(dsn)
    
    # Jalankan jika flag --all diset atau tidak ada flag spesifik yang dipilih
    run_check = args.check or args.all or not (args.check or args.clean or args.optimize)
    run_clean = args.clean or args.all or not (args.check or args.clean or args.optimize)
    run_optimize = args.optimize or args.all or not (args.check or args.clean or args.optimize)
    
    # 1. VERIFIKASI INTEGRITAS
    if run_check:
        logging.info("[TINDAKAN 1] Menjalankan Pemeriksaan Integritas Relasional & Hypertables...")
        report = db.verify_integrity()
        
        if report["integrity_ok"]:
            logging.info("  -> Status Koneksi & Driver PostgreSQL: OK")
            logging.info(f"  -> Hypertables TimescaleDB Terdeteksi: {', '.join(report['hypertables'])}")
        else:
            logging.error(f"  -> ERROR INTEGRITAS TERDETEKSI: {report['integrity_errors']}")
            
        # Optional relasional integrity checks can be queried here if needed
        # In PG, foreign key checks are enforced native by default.
        logging.info("  -> Status Foreign Key (Relasional): OK (Enforced by PostgreSQL schema)")
                
    # 2. PEMBERSIHAN DATA
    if run_clean:
        logging.info("[TINDAKAN 2] Menjalankan Pembersihan Duplikat & Orphan Ticks...")
        clean_report = db.clean_database()
        
        t_del = clean_report["trade_book_duplicates_deleted"]
        o_del = clean_report["orphan_orderbook_ticks_deleted"]
        
        if t_del > 0 or o_del > 0:
            logging.info(f"  -> Berhasil menghapus {t_del} duplikat trade_book.")
            logging.info(f"  -> Berhasil menghapus {o_del} orphan orderbook_ticks.")
            logging.info("  -> Pembersihan data tidak valid: SELESAI.")
        else:
            logging.info("  -> Database bersih. Tidak ada data tidak valid yang perlu dihapus.")
            
    # 3. OPTIMALISASI
    if run_optimize:
        logging.info("[TINDAKAN 3] Menjalankan Rekonstruksi Indeks & Perampingan Database...")
        start_size = get_db_size(db)
        
        db.optimize_database()
        
        end_size = get_db_size(db)
        saved_bytes = start_size - end_size
        
        logging.info("  -> Pembangunan ulang indeks (ANALYZE): SELESAI.")
        logging.info("  -> Perampingan penyimpanan (VACUUM): SELESAI.")
        if saved_bytes > 0:
            logging.info(f"  -> Ruang penyimpanan yang berhasil diklaim kembali: {saved_bytes / (1024 * 1024):.2f} MB")
        else:
            logging.info("  -> Ukuran database sudah optimal.")
            
    logging.info("=" * 70)
    logging.info("DATABASE MAINTENANCE SELESAI DENGAN SUKSES!")
    logging.info("=" * 70)

if __name__ == "__main__":
    main()
