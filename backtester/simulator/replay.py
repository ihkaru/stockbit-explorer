import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure research/indicators is in Python path for importing models
current_dir = os.path.dirname(os.path.abspath(__file__))
research_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "research", "indicators"))
if research_dir not in sys.path:
    sys.path.append(research_dir)

from tape_reading.models import TradeTick

class HistoricalReplaySimulator:
    """
    Simulator to load historical running trades for a ticker and replay them
    sequentially (tick-by-tick) to emulate a live WebSocket feed.
    """
    def __init__(self, db_dsn=None):
        # Default fallback to PgBouncer port 6432
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
        
    def get_connection(self):
        conn = psycopg2.connect(self.dsn)
        conn.cursor_factory = DictCursor
        return conn

    def get_ticks(self, symbol: str, start_date: str, end_date: str):
        """
        Loads trades from PostgreSQL between start_date and end_date (inclusive)
        and yields TradeTick objects sequentially.
        """
        symbol = symbol.upper()
        
        # Format start and end date to ISO timestamps
        try:
            start_dt = datetime.strptime(f"{start_date} 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}")

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
            WHERE t.symbol = %s AND t.time >= %s AND t.time <= %s
            ORDER BY t.time ASC, t.trade_number ASC
        """
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (symbol, start_dt, end_dt))
                
                count = 0
                for r in cursor:
                    count += 1
                    yield TradeTick(
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
                    )
                
                print(f"[REPLAY] Loaded {count:,} ticks for {symbol} from {start_date} to {end_date}.")
        finally:
            conn.close()
