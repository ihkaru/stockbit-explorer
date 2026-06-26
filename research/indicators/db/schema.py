import os
import logging


def initialize_schema(conn):
    """
    Inisialisasi skema PostgreSQL dan TimescaleDB secara eksplisit dan idempoten.

    Args:
        conn: psycopg2 connection object (raw, bukan context manager).
              Caller bertanggung jawab membuka dan menutup koneksi.
    """
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        init_sql_path = os.path.join(base_dir, "infra", "init.sql")

        if os.path.exists(init_sql_path):
            with open(init_sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()
            logging.info("Skema PostgreSQL & TimescaleDB berhasil diverifikasi/diinisialisasi.")
        else:
            logging.warning(
                f"Berkas infra/init.sql tidak ditemukan di {init_sql_path}. "
                "Inisialisasi skema dilewati."
            )
    except Exception as e:
        logging.error(f"Gagal menginisialisasi skema PostgreSQL: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

