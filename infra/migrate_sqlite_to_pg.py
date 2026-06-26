import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def migrate(sqlite_db_path="data/stockbit_explorer.db", pg_dsn=None):
    pg_dsn = pg_dsn or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
    )

    if not os.path.exists(sqlite_db_path):
        logging.error(f"SQLite database file not found at '{sqlite_db_path}'. Migration aborted.")
        return False

    logging.info("=" * 80)
    logging.info(f"STARTING DATABASE MIGRATION FROM SQLite TO PostgreSQL")
    logging.info(f"Source SQLite: {sqlite_db_path}")
    logging.info(f"Target PostgreSQL: {pg_dsn}")
    logging.info("=" * 80)

    # 1. Connect to databases
    try:
        lite_conn = sqlite3.connect(sqlite_db_path)
        lite_conn.row_factory = sqlite3.Row
        lite_cursor = lite_conn.cursor()
    except Exception as e:
        logging.error(f"Failed to connect to SQLite: {e}")
        return False

    try:
        pg_conn = psycopg2.connect(pg_dsn)
        
        # Inisialisasi skema tabel PostgreSQL + TimescaleDB
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "research", "indicators")))
        from db.schema import initialize_schema
        initialize_schema(pg_conn)
        
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {e}")
        lite_conn.close()
        return False

    # Explicit ordering to satisfy Foreign Key constraints during insertion
    ordered_tables = [
        "brokers",
        "conglomerates",
        "conglomerate_stocks",
        "conglomerate_brokers",
        "msci_tracker",
        "watchlists",
        "watchlist_items",
        "trading_preferences",
        "company_profiles",
        "company_executives",
        "company_shareholders",
        "company_beneficiaries",
        "company_shareholder_stats",
        "company_shareholding_compositions",
        "company_insider_transactions",
        "company_keystats",
        "company_dividends",
        "company_analyst_ratings",
        "running_trades",
        "trade_book",
        "price_grids",
        "ohlcv_data",
        "orderbook_snapshots",
        "orderbook_ticks",
        "order_queues",
        "broker_summaries",
        "broker_daily_activity"
    ]

    try:
        for table_name in ordered_tables:
            logging.info(f"Migrating table '{table_name}'...")
            
            # Check if table exists in SQLite
            lite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not lite_cursor.fetchone():
                logging.warning(f"  -> Table '{table_name}' does not exist in source SQLite. Skipping.")
                continue

            # Check if table exists in PostgreSQL
            pg_cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            if not pg_cursor.fetchone()[0]:
                logging.error(f"  -> Table '{table_name}' does not exist in target PostgreSQL. Run schema setup first.")
                continue

            # Get column list from SQLite
            lite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col["name"] for col in lite_cursor.fetchall()]
            
            if not columns:
                logging.warning(f"  -> No columns found for table '{table_name}'. Skipping.")
                continue

            # Explicitly append partitioning columns for hypertables
            if table_name in ("running_trades", "trade_book", "orderbook_snapshots"):
                columns.append("time")
            elif table_name == "ohlcv_data":
                columns.append("candle_time")
            elif table_name == "broker_summaries":
                columns.append("summary_date")
            elif table_name == "broker_daily_activity":
                columns.append("activity_date")

            # Read SQLite data
            lite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = lite_cursor.fetchall()
            total_rows = len(rows)
            
            if total_rows == 0:
                logging.info(f"  -> Table '{table_name}' is empty. Skipping rows copy.")
                continue

            logging.info(f"  -> Found {total_rows:,} rows in SQLite. Streaming to PostgreSQL...")

            # Prepare insert query
            cols_str = ", ".join(columns)
            query = f"INSERT INTO {table_name} ({cols_str}) VALUES %s ON CONFLICT DO NOTHING"

            # Stream in batches of 5000
            batch_size = 5000
            inserted_count = 0
            
            for i in range(0, total_rows, batch_size):
                batch_rows = rows[i:i + batch_size]
                data_tuples = []
                for r in batch_rows:
                    row_dict = dict(r)
                    if table_name in ("running_trades", "trade_book", "orderbook_snapshots"):
                        ts = row_dict.get("timestamp") or 0.0
                        from datetime import datetime, timezone
                        row_dict["time"] = datetime.fromtimestamp(ts, tz=timezone.utc)
                    elif table_name == "ohlcv_data":
                        ts = row_dict.get("unix_timestamp") or 0
                        from datetime import datetime, timezone
                        row_dict["candle_time"] = datetime.fromtimestamp(ts, tz=timezone.utc)
                    elif table_name == "broker_summaries":
                        d_str = row_dict.get("date") or "2000-01-01"
                        from datetime import datetime
                        try:
                            row_dict["summary_date"] = datetime.strptime(d_str, "%Y-%m-%d").date()
                        except Exception:
                            row_dict["summary_date"] = datetime.strptime("2000-01-01", "%Y-%m-%d").date()
                    elif table_name == "broker_daily_activity":
                        d_str = row_dict.get("date") or "2000-01-01"
                        from datetime import datetime
                        try:
                            row_dict["activity_date"] = datetime.strptime(d_str, "%Y-%m-%d").date()
                        except Exception:
                            row_dict["activity_date"] = datetime.strptime("2000-01-01", "%Y-%m-%d").date()
                    
                    data_tuples.append(tuple(row_dict[col] for col in columns))

                try:
                    execute_values(pg_cursor, query, data_tuples)
                    pg_conn.commit()
                    inserted_count += len(data_tuples)
                except Exception as e:
                    pg_conn.rollback()
                    logging.error(f"  -> Batch insertion failed for table '{table_name}': {e}")
                    raise e

            logging.info(f"  -> Completed. Successfully migrated {inserted_count:,} / {total_rows:,} rows.")

            # Resynchronize ID sequences for PostgreSQL auto-incrementing serial columns
            try:
                pg_cursor.execute(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                seq_row = pg_cursor.fetchone()
                if seq_row and seq_row[0]:
                    seq_name = seq_row[0]
                    # Update sequence to match maximum id in the table
                    pg_cursor.execute(f"SELECT setval('{seq_name}', COALESCE(MAX(id), 1)) FROM {table_name}")
                    new_seq_val = pg_cursor.fetchone()[0]
                    pg_conn.commit()
                    logging.info(f"  -> Resynced sequence '{seq_name}' to value {new_seq_val}.")
            except Exception as seq_err:
                pg_conn.rollback()
                logging.debug(f"  -> Sequence resync skipped or failed for '{table_name}' (normal if no SERIAL id): {seq_err}")

        logging.info("=" * 80)
        logging.info("MIGRATION COMPLETED SUCCESSFULLY!")
        logging.info("=" * 80)
        return True

    except Exception as e:
        logging.error(f"FATAL MIGRATION ERROR: {e}")
        return False
    finally:
        lite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate()
