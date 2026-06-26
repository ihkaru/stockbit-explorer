from .base_repository import BaseRepository
import psycopg2

class MarketDataRepository(BaseRepository):
    def insert_ohlcv_data(self, ohlcv_list):
        """Batch insert candles OHLCV menggunakan PostgreSQL Upsert untuk merge data dasar & data kaya."""
        if not ohlcv_list:
            return 0
            
        query = """
            INSERT INTO ohlcv_data (
                symbol, date, time, open, high, low, close,
                volume, value, frequency, foreign_buy, foreign_sell,
                unix_timestamp, foreign_flow, market_cap, dividend, shares_outstanding, freq_analyzer,
                candle_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(symbol, date, time, candle_time) DO UPDATE SET
                open = COALESCE(EXCLUDED.open, ohlcv_data.open),
                high = COALESCE(EXCLUDED.high, ohlcv_data.high),
                low = COALESCE(EXCLUDED.low, ohlcv_data.low),
                close = COALESCE(EXCLUDED.close, ohlcv_data.close),
                volume = COALESCE(EXCLUDED.volume, ohlcv_data.volume),
                value = COALESCE(EXCLUDED.value, ohlcv_data.value),
                frequency = COALESCE(EXCLUDED.frequency, ohlcv_data.frequency),
                foreign_buy = COALESCE(EXCLUDED.foreign_buy, ohlcv_data.foreign_buy),
                foreign_sell = COALESCE(EXCLUDED.foreign_sell, ohlcv_data.foreign_sell),
                unix_timestamp = COALESCE(EXCLUDED.unix_timestamp, ohlcv_data.unix_timestamp),
                foreign_flow = COALESCE(EXCLUDED.foreign_flow, ohlcv_data.foreign_flow),
                market_cap = COALESCE(EXCLUDED.market_cap, ohlcv_data.market_cap),
                dividend = COALESCE(EXCLUDED.dividend, ohlcv_data.dividend),
                shares_outstanding = COALESCE(EXCLUDED.shares_outstanding, ohlcv_data.shares_outstanding),
                freq_analyzer = COALESCE(EXCLUDED.freq_analyzer, ohlcv_data.freq_analyzer)
        """
        from datetime import datetime, timezone
        data_tuples = []
        for c in ohlcv_list:
            # Hitung candle_time secara aman
            ts = c.get("unix_timestamp")
            if ts:
                candle_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                d_str = c.get("date")
                t_str = c.get("time") or "00:00"
                try:
                    if not t_str or t_str == "00:00":
                        dt = datetime.strptime(d_str, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H:%M")
                    candle_time = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    candle_time = datetime.now(timezone.utc)

            data_tuples.append((
                c.get("symbol"),
                c.get("date"),
                c.get("time"),
                c.get("open"),
                c.get("high"),
                c.get("low"),
                c.get("close"),
                c.get("volume"),
                c.get("value"),
                c.get("frequency"),
                c.get("foreign_buy"),
                c.get("foreign_sell"),
                c.get("unix_timestamp"),
                c.get("foreign_flow"),
                c.get("market_cap"),
                c.get("dividend"),
                c.get("shares_outstanding"),
                c.get("freq_analyzer"),
                candle_time
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_running_trades(self, trades):
        """Batch insert running trades menggunakan ON CONFLICT DO NOTHING untuk deduplikasi instan."""
        if not trades:
            return 0
            
        query = """
            INSERT INTO running_trades (
                trade_id, trade_number, timestamp, time_str, symbol, price, lot, value,
                action, market_board, buyer_broker, seller_broker, buyer_type, seller_type,
                buy_order_number, sell_order_number, group_order_number, is_broker_exists,
                change_percent, time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, trade_id) DO NOTHING
        """
        from datetime import datetime, timezone
        data_tuples = []
        for t in trades:
            ts = t.get("timestamp") or 0.0
            trade_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            data_tuples.append((
                t.get("trade_id"),
                t.get("trade_number"),
                t.get("timestamp"),
                t.get("time_str"),
                t.get("symbol"),
                t.get("price"),
                t.get("lot"),
                t.get("value"),
                t.get("action"),
                t.get("market_board"),
                t.get("buyer_broker"),
                t.get("seller_broker"),
                t.get("buyer_type"),
                t.get("seller_type"),
                t.get("buy_order_number"),
                t.get("call_order_number") or t.get("sell_order_number"), # fallback safe
                t.get("group_order_number"),
                t.get("is_broker_exists"),
                t.get("change_percent"),
                trade_time
            ))
            
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                inserted_count = cursor.rowcount
                conn.commit()
                return inserted_count

    def insert_trade_book(self, symbol, timestamp, book_items):
        """Insert data trade book."""
        if not book_items:
            return 0
            
        query = """
            INSERT INTO trade_book (timestamp, symbol, price, buy_lot, buy_freq, sell_lot, sell_freq, total_lot, time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, price, timestamp, time) DO UPDATE SET
                buy_lot = EXCLUDED.buy_lot,
                buy_freq = EXCLUDED.buy_freq,
                sell_lot = EXCLUDED.sell_lot,
                sell_freq = EXCLUDED.sell_freq,
                total_lot = EXCLUDED.total_lot
        """
        from datetime import datetime, timezone
        trade_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        data_tuples = []
        for item in book_items:
            data_tuples.append((
                timestamp,
                symbol,
                item.get("price"),
                item.get("buy_lot"),
                item.get("buy_freq"),
                item.get("sell_lot"),
                item.get("sell_freq"),
                item.get("total_lot"),
                trade_time
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Bersihkan data lama dengan timestamp & symbol yang sama demi mencegah data ganda
                cursor.execute("DELETE FROM trade_book WHERE symbol = %s AND timestamp = %s", (symbol, timestamp))
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount
            
    def insert_price_grid(self, symbol, prices):
        """Insert harga fraksi valid."""
        if not prices:
            return 0
            
        query = "INSERT INTO price_grids (symbol, price) VALUES (%s, %s) ON CONFLICT(symbol, price) DO NOTHING"
        data_tuples = [(symbol, p) for p in prices]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_orderbook_snapshot(self, symbol, timestamp, snap):
        """Insert snapshot orderbook dan baris-baris ticks-nya."""
        snap_query = """
            INSERT INTO orderbook_snapshots (
                timestamp, symbol, close_price, total_bid_lot, total_bid_freq,
                total_offer_lot, total_offer_freq, ara_price, arb_price,
                foreign_buy_val, foreign_sell_val, foreign_net_val,
                domestic_pct, foreign_pct, time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp, time) DO UPDATE SET
                close_price = EXCLUDED.close_price,
                total_bid_lot = EXCLUDED.total_bid_lot,
                total_bid_freq = EXCLUDED.total_bid_freq,
                total_offer_lot = EXCLUDED.total_offer_lot,
                total_offer_freq = EXCLUDED.total_offer_freq,
                ara_price = EXCLUDED.ara_price,
                arb_price = EXCLUDED.arb_price,
                foreign_buy_val = EXCLUDED.foreign_buy_val,
                foreign_sell_val = EXCLUDED.foreign_sell_val,
                foreign_net_val = EXCLUDED.foreign_net_val,
                domestic_pct = EXCLUDED.domestic_pct,
                foreign_pct = EXCLUDED.foreign_pct
            RETURNING id
        """
        from datetime import datetime, timezone
        snap_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Hapus ticks lama yang berasosiasi dengan snapshot (symbol, timestamp) yang sama demi mencegah orphan ticks
                cursor.execute("""
                    DELETE FROM orderbook_ticks 
                    WHERE snapshot_id IN (
                        SELECT id FROM orderbook_snapshots WHERE symbol = %s AND timestamp = %s
                    )
                """, (symbol, timestamp))
                
                cursor.execute(snap_query, (
                    timestamp,
                    symbol,
                    snap.get("close_price"),
                    snap.get("total_bid_lot"),
                    snap.get("total_bid_freq"),
                    snap.get("total_offer_lot"),
                    snap.get("total_offer_freq"),
                    snap.get("ara_price"),
                    snap.get("arb_price"),
                    snap.get("foreign_buy_val"),
                    snap.get("foreign_sell_val"),
                    snap.get("foreign_net_val"),
                    snap.get("domestic_pct"),
                    snap.get("foreign_pct"),
                    snap_time
                ))
                
                snapshot_id = cursor.fetchone()[0]
                
                # Ticks (Bid & Offer queue details)
                ticks_query = """
                    INSERT INTO orderbook_ticks (snapshot_id, type, price, volume, que_num)
                    VALUES (%s, %s, %s, %s, %s)
                """
                tick_tuples = []
                for item in snap.get("bids", []):
                    tick_tuples.append((snapshot_id, "BID", item.get("price"), item.get("volume"), item.get("que_num")))
                for item in snap.get("offers", []):
                    tick_tuples.append((snapshot_id, "OFFER", item.get("price"), item.get("volume"), item.get("que_num")))
                    
                if tick_tuples:
                    cursor.executemany(ticks_query, tick_tuples)
                
                conn.commit()
                return snapshot_id

    def insert_order_queues(self, orders_list):
        """Batch insert order queues."""
        if not orders_list:
            return 0
            
        query = """
            INSERT INTO order_queues (
                id, symbol, queue_number, time_str, action_type, price, status,
                open_lot, total_lot, broker_code, broker_group, order_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                symbol = EXCLUDED.symbol,
                queue_number = EXCLUDED.queue_number,
                time_str = EXCLUDED.time_str,
                action_type = EXCLUDED.action_type,
                price = EXCLUDED.price,
                status = EXCLUDED.status,
                open_lot = EXCLUDED.open_lot,
                total_lot = EXCLUDED.total_lot,
                broker_code = EXCLUDED.broker_code,
                broker_group = EXCLUDED.broker_group,
                order_number = EXCLUDED.order_number
        """
        data_tuples = []
        for o in orders_list:
            data_tuples.append((
                o.get("id"),
                o.get("symbol"),
                o.get("queue_number"),
                o.get("time_str"),
                o.get("action_type"),
                o.get("price"),
                o.get("status"),
                o.get("open_lot"),
                o.get("total_lot"),
                o.get("broker_code"),
                o.get("broker_group"),
                o.get("order_number")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount
