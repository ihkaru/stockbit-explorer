from .base_repository import BaseRepository

class ConfigRepository(BaseRepository):
    def insert_watchlists(self, watchlists_list):
        """Batch insert watchlists."""
        query = """
            INSERT INTO watchlists (watchlist_id, name, description, is_default, is_favorite, category_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (watchlist_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                is_default = EXCLUDED.is_default,
                is_favorite = EXCLUDED.is_favorite,
                category_type = EXCLUDED.category_type
        """
        data_tuples = []
        for w in watchlists_list:
            data_tuples.append((
                w.get("watchlist_id"),
                w.get("name"),
                w.get("description"),
                1 if w.get("is_default") else 0,
                1 if w.get("is_favorite") else 0,
                w.get("category_type")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_watchlist_items(self, watchlist_id, symbols):
        """Insert symbols ke dalam watchlist."""
        # Hapus relasi lama terlebih dahulu untuk sync terbaru
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM watchlist_items WHERE watchlist_id = %s", (watchlist_id,))
                
                query = """
                    INSERT INTO watchlist_items (watchlist_id, symbol)
                    VALUES (%s, %s)
                    ON CONFLICT (watchlist_id, symbol) DO NOTHING
                """
                data_tuples = [(watchlist_id, sym) for sym in symbols]
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_trading_preferences(self, preferences_list):
        """Batch insert or replace trading preferences."""
        query = """
            INSERT INTO trading_preferences (
                strategy_name, max_entry_premium_pct, stop_loss_buffer_pct, 
                risk_reward_ratio, min_haka_ratio, min_smart_money_score, max_portfolio_allocation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(strategy_name) DO UPDATE SET
                max_entry_premium_pct = EXCLUDED.max_entry_premium_pct,
                stop_loss_buffer_pct = EXCLUDED.stop_loss_buffer_pct,
                risk_reward_ratio = EXCLUDED.risk_reward_ratio,
                min_haka_ratio = EXCLUDED.min_haka_ratio,
                min_smart_money_score = EXCLUDED.min_smart_money_score,
                max_portfolio_allocation = EXCLUDED.max_portfolio_allocation
        """
        data_tuples = []
        for p in preferences_list:
            data_tuples.append((
                p.get("strategy_name"),
                p.get("max_entry_premium_pct"),
                p.get("stop_loss_buffer_pct"),
                p.get("risk_reward_ratio"),
                p.get("min_haka_ratio"),
                p.get("min_smart_money_score"),
                p.get("max_portfolio_allocation")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def get_trading_preference(self, strategy_name):
        """Fetch trading preference by strategy name."""
        query = """
            SELECT strategy_name, max_entry_premium_pct, stop_loss_buffer_pct, 
                   risk_reward_ratio, min_haka_ratio, min_smart_money_score, max_portfolio_allocation
            FROM trading_preferences
            WHERE strategy_name = %s
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (strategy_name,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

