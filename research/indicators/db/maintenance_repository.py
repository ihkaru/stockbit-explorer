from .base_repository import BaseRepository

class MaintenanceRepository(BaseRepository):
    def clean_database(self):
        """
        Membersihkan data tidak valid yang mengancam integritas data secara berkala.
        Menghapus duplikat trade_book dan ticks orderbook yang yatim.
        """
        report = {"trade_book_duplicates_deleted": 0, "orphan_orderbook_ticks_deleted": 0}
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Bersihkan duplikat di trade_book
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_book
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM trade_book
                        GROUP BY symbol, timestamp, price, time
                    )
                """)
                dup_trade_book = cursor.fetchone()[0]
                if dup_trade_book > 0:
                    cursor.execute("""
                        DELETE FROM trade_book
                        WHERE id NOT IN (
                            SELECT MIN(id)
                            FROM trade_book
                            GROUP BY symbol, timestamp, price, time
                        )
                    """)
                    report["trade_book_duplicates_deleted"] = dup_trade_book
                
                # 2. Bersihkan ticks orderbook yang yatim (orphan ticks)
                cursor.execute("""
                    SELECT COUNT(*) FROM orderbook_ticks
                    WHERE snapshot_id NOT IN (
                        SELECT id FROM orderbook_snapshots
                    )
                """)
                orphan_ticks = cursor.fetchone()[0]
                if orphan_ticks > 0:
                    cursor.execute("""
                        DELETE FROM orderbook_ticks
                        WHERE snapshot_id NOT IN (
                            SELECT id FROM orderbook_snapshots
                        )
                    """)
                    report["orphan_orderbook_ticks_deleted"] = orphan_ticks
                    
                conn.commit()
        return report

    def verify_integrity(self):
        """
        Melakukan pemeriksaan integritas database PostgreSQL & TimescaleDB.
        """
        report = {"integrity_ok": True, "integrity_errors": [], "hypertables": []}
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. Cek koneksi sederhana
                    cursor.execute("SELECT 1")
                    # 2. Ambil daftar hypertable TimescaleDB
                    cursor.execute("SELECT hypertable_name FROM timescaledb_information.hypertables")
                    rows = cursor.fetchall()
                    report["hypertables"] = [r[0] for r in rows]
        except Exception as e:
            report["integrity_ok"] = False
            report["integrity_errors"].append(str(e))
        return report

    def optimize_database(self):
        """
        Merampingkan dan mengoptimalkan performa index database (VACUUM & ANALYZE).

        VACUUM membutuhkan AUTOCOMMIT mode dan tidak bisa dijalankan di dalam
        transaction block. Koneksi diambil dari pool, di-set AUTOCOMMIT, lalu
        dikembalikan ke pool setelah selesai.
        """
        # Ambil raw connection dari pool tanpa context manager
        # agar bisa set isolation_level AUTOCOMMIT
        raw_conn = self._pool._pool.getconn()
        try:
            raw_conn.set_isolation_level(0)  # AUTOCOMMIT untuk VACUUM
            with raw_conn.cursor() as cursor:
                cursor.execute("VACUUM")
                cursor.execute("ANALYZE")
            return True
        finally:
            # Reset isolation level ke default sebelum dikembalikan ke pool
            try:
                raw_conn.set_isolation_level(1)  # READ COMMITTED
            except Exception:
                pass
            self._pool._pool.putconn(raw_conn)

