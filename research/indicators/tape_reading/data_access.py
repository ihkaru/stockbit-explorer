import psycopg2
from psycopg2.extras import DictCursor
import os
from typing import List, Optional
from dotenv import load_dotenv
from .models import TradeTick

# Load environment variables
load_dotenv()

class TapeReadingRepository:
    """Repository class handling all PostgreSQL query executions for Tape Reading analysis."""
    
    def __init__(self, db_dsn: str = None):
        self.dsn = db_dsn or os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
        )
        if self.dsn and not (self.dsn.startswith("postgres://") or self.dsn.startswith("postgresql://")):
            raise ValueError(
                f"Invalid database connection: '{self.dsn}'. "
                "SQLite file-based database paths are no longer supported. "
                "Please provide a valid PostgreSQL DSN starting with 'postgres://' or 'postgresql://'."
            )
        self.conglomerate_stocks = {} # symbol -> conglom_name
        self.conglomerate_brokers = {} # broker_code -> conglom_name
        self.msci_tracker = {} # symbol -> (index_type, status)
        self.swing_pref = None
        self._load_metadata()
        self._load_swing_preference()

    def get_connection(self):
        conn = psycopg2.connect(self.dsn)
        conn.cursor_factory = DictCursor
        return conn

    def _load_swing_preference(self):
        """Memuat parameter strategi REMORA_SWING dari database dengan fallback default."""
        try:
            conn = self.get_connection()
            query = """
                SELECT max_entry_premium_pct, stop_loss_buffer_pct, 
                       risk_reward_ratio, min_haka_ratio, min_smart_money_score, max_portfolio_allocation
                FROM trading_preferences
                WHERE strategy_name = 'REMORA_SWING'
            """
            with conn.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    self.swing_pref = dict(row)
            conn.close()
        except Exception:
            pass
            
        if not self.swing_pref:
            self.swing_pref = {
                "max_entry_premium_pct": 0.05,
                "stop_loss_buffer_pct": 0.04,
                "risk_reward_ratio": 2.5,
                "min_haka_ratio": 0.60,
                "min_smart_money_score": 1000.0,
                "max_portfolio_allocation": 0.20
            }

    def _load_metadata(self):
        """Memuat data master konglomerasi dan indeks MSCI ke dalam memori cache."""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Load conglomerate stocks
                cursor.execute("SELECT symbol, conglomerate_name FROM conglomerate_stocks")
                for r in cursor.fetchall():
                    self.conglomerate_stocks[r["symbol"].upper()] = r["conglomerate_name"]
                    
                # Load conglomerate brokers
                cursor.execute("SELECT broker_code, conglomerate_name FROM conglomerate_brokers")
                for r in cursor.fetchall():
                    self.conglomerate_brokers[r["broker_code"].upper()] = r["conglomerate_name"]
                    
                # Load MSCI tracker
                cursor.execute("SELECT symbol, index_type, status FROM msci_tracker")
                for r in cursor.fetchall():
                    self.msci_tracker[r["symbol"].upper()] = (r["index_type"], r["status"])
            conn.close()
        except Exception:
            # Tabel belum diinisialisasi (misal saat running pertama kali sebelum seeding)
            pass

    def get_recent_trades(
        self,
        symbol: str,
        limit: int = 500,
        min_trade_number: Optional[int] = None
    ) -> List[TradeTick]:
        """
        Mengambil N transaksi terakhir untuk saham tertentu dari database.
        Data diurutkan dari yang terlama ke yang terbaru untuk analisis rolling.
        """
        conn = self.get_connection()
        
        query = """
            SELECT
                t.trade_id, t.trade_number, t.timestamp, t.time_str, t.symbol,
                t.price, t.lot, t.value, t.action,
                t.buyer_broker, t.seller_broker, t.buyer_type, t.seller_type,
                t.group_order_number, t.buy_order_number, t.sell_order_number,
                b_buy.retail_density AS buyer_retail_density,
                b_buy.typical_style AS buyer_typical_style,
                b_buy.tier AS buyer_tier,
                b_sell.retail_density AS seller_retail_density,
                b_sell.typical_style AS seller_typical_style,
                b_sell.tier AS seller_tier
            FROM running_trades t
            LEFT JOIN brokers b_buy ON SUBSTR(t.buyer_broker, 1, 2) = b_buy.code
            LEFT JOIN brokers b_sell ON SUBSTR(t.seller_broker, 1, 2) = b_sell.code
            WHERE t.symbol = %s
        """
        params = [symbol]
        
        if min_trade_number:
            query += " AND t.trade_number > %s"
            params.append(min_trade_number)
        
        query += " ORDER BY t.trade_number DESC LIMIT %s"
        params.append(limit)
        
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for r in reversed(rows):  # Balikkan agar urutan kronologis
            trades.append(TradeTick(
                trade_id=r["trade_id"],
                trade_number=r["trade_number"] or 0,
                timestamp=r["timestamp"] or 0.0,
                time_str=r["time_str"] or "",
                symbol=r["symbol"] or symbol,
                price=r["price"] or 0,
                lot=r["lot"] or 0.0,
                value=r["value"] or 0,
                action="B" if (r["action"] or "").upper() in ("B", "BUY") else "S",
                buyer_broker=r["buyer_broker"] or "",
                seller_broker=r["seller_broker"] or "",
                buyer_type=r["buyer_type"] or "",
                seller_type=r["seller_type"] or "",
                group_order_number=r["group_order_number"] or "",
                buy_order_number=r["buy_order_number"] or "",
                sell_order_number=r["sell_order_number"] or "",
                buyer_retail_density=r["buyer_retail_density"],
                buyer_typical_style=r["buyer_typical_style"],
                buyer_tier=r["buyer_tier"],
                seller_retail_density=r["seller_retail_density"],
                seller_typical_style=r["seller_typical_style"],
                seller_tier=r["seller_tier"]
            ))
        return trades

    def get_multi_day_broker_summary(self, symbol: str, days_limit: int = 10):
        """
        Menghitung akumulasi broker kumulatif selama N hari bursa terakhir.
        Mengembalikan broker akumulator utama (net buyer) dan harga rata-rata modalnya.
        """
        conn = self.get_connection()
        
        # 1. Cari tanggal-tanggal terakhir yang tersedia untuk saham ini
        dates_query = """
            SELECT DISTINCT date FROM broker_summaries 
            WHERE symbol = %s 
            ORDER BY date DESC LIMIT %s
        """
        with conn.cursor() as cursor:
            cursor.execute(dates_query, [symbol, days_limit])
            rows = cursor.fetchall()
            
        if not rows:
            conn.close()
            return None
            
        target_dates = [r["date"] for r in rows]
        
        # 2. Ambil data akumulasi/distribusi kumulatif per broker pada tanggal tersebut
        placeholders = ",".join("%s" for _ in target_dates)
        query = f"""
            SELECT 
                broker_code,
                SUM(net_lot) AS cum_net_lot,
                SUM(net_value) AS cum_net_value
            FROM broker_summaries
            WHERE symbol = %s AND date IN ({placeholders})
            GROUP BY broker_code
            ORDER BY cum_net_lot DESC
        """
        params = [symbol] + target_dates
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            broker_rows = cursor.fetchall()
        conn.close()
        
        # Filter broker net buyer utama (akumulator)
        buyers = []
        for r in broker_rows:
            net_lot = float(r["cum_net_lot"] or 0)
            net_val = float(r["cum_net_value"] or 0.0)
            if net_lot > 0:
                # vwap = value / (lot * 100)
                avg_price = net_val / (net_lot * 100) if net_lot > 0 else 0
                buyers.append({
                    "broker_code": r["broker_code"],
                    "net_lot": net_lot,
                    "avg_price": round(avg_price, 2)
                })
                
        return buyers

