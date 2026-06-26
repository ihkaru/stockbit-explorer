from .base_repository import BaseRepository

class BrokerRepository(BaseRepository):
    def insert_brokers(self, brokers_list):
        """Batch insert brokers menggunakan ON CONFLICT untuk menghindari penimpaan kolom kustom (profil)."""
        query = """
            INSERT INTO brokers (code, name, group_type, color, membership_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(code) DO UPDATE SET
                name = COALESCE(EXCLUDED.name, brokers.name),
                group_type = COALESCE(EXCLUDED.group_type, brokers.group_type),
                color = COALESCE(EXCLUDED.color, brokers.color),
                membership_type = COALESCE(EXCLUDED.membership_type, brokers.membership_type)
        """
        data_tuples = []
        for b in brokers_list:
            data_tuples.append((
                b.get("code"),
                b.get("name"),
                b.get("group_type"),
                b.get("color"),
                b.get("membership_type")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_conglomerates(self, conglomerates_list):
        """Batch insert conglomerates."""
        query = """
            INSERT INTO conglomerates (name, owner_name, description)
            VALUES (%s, %s, %s)
            ON CONFLICT(name) DO UPDATE SET
                owner_name = COALESCE(EXCLUDED.owner_name, conglomerates.owner_name),
                description = COALESCE(EXCLUDED.description, conglomerates.description)
        """
        data_tuples = [(c.get("name"), c.get("owner_name"), c.get("description")) for c in conglomerates_list]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_conglomerate_stocks(self, stocks_list):
        """Batch insert conglomerate stocks."""
        query = """
            INSERT INTO conglomerate_stocks (conglomerate_name, symbol)
            VALUES (%s, %s)
            ON CONFLICT (conglomerate_name, symbol) DO NOTHING
        """
        data_tuples = [(s.get("conglomerate_name"), s.get("symbol")) for s in stocks_list]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_conglomerate_brokers(self, brokers_list):
        """Batch insert conglomerate brokers."""
        query = """
            INSERT INTO conglomerate_brokers (conglomerate_name, broker_code)
            VALUES (%s, %s)
            ON CONFLICT (conglomerate_name, broker_code) DO NOTHING
        """
        data_tuples = [(b.get("conglomerate_name"), b.get("broker_code")) for b in brokers_list]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_msci_stocks(self, msci_list):
        """Batch insert MSCI stocks."""
        query = """
            INSERT INTO msci_tracker (symbol, index_type, status, effective_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(symbol) DO UPDATE SET
                index_type = COALESCE(EXCLUDED.index_type, msci_tracker.index_type),
                status = COALESCE(EXCLUDED.status, msci_tracker.status),
                effective_date = COALESCE(EXCLUDED.effective_date, msci_tracker.effective_date)
        """
        data_tuples = [(m.get("symbol"), m.get("index_type"), m.get("status"), m.get("effective_date")) for m in msci_list]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def update_broker_profiles(self, profiles_list):
        """Update broker custom profiles (retail_density, typical_style, tier)."""
        query = """
            UPDATE brokers
            SET retail_density = %s,
                typical_style = %s,
                tier = %s
            WHERE code = %s
        """
        data_tuples = []
        for p in profiles_list:
            data_tuples.append((p.get("retail_density"), p.get("typical_style"), p.get("tier"), p.get("code")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_broker_summaries(self, summaries):
        """Batch insert broker summaries menggunakan ON CONFLICT DO UPDATE untuk memperbarui data EOD."""
        query = """
            INSERT INTO broker_summaries (
                date, symbol, broker_code, type, net_lot, total_volume_lot, 
                avg_price, net_value, total_volume_value, freq, activity, summary_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(date, symbol, broker_code, summary_date) DO UPDATE SET
                type = EXCLUDED.type,
                net_lot = EXCLUDED.net_lot,
                total_volume_lot = EXCLUDED.total_volume_lot,
                avg_price = EXCLUDED.avg_price,
                net_value = EXCLUDED.net_value,
                total_volume_value = EXCLUDED.total_volume_value,
                freq = EXCLUDED.freq,
                activity = EXCLUDED.activity
        """
        from datetime import datetime
        data_tuples = []
        for s in summaries:
            d_str = s.get("date") or "2000-01-01"
            try:
                summary_date = datetime.strptime(d_str, "%Y-%m-%d").date()
            except Exception:
                summary_date = datetime.strptime("2000-01-01", "%Y-%m-%d").date()

            data_tuples.append((
                s.get("date"),
                s.get("symbol"),
                s.get("broker_code"),
                s.get("type"),
                s.get("net_lot"),
                s.get("total_volume_lot"),
                s.get("avg_price"),
                s.get("net_value"),
                s.get("total_volume_value"),
                s.get("freq"),
                s.get("activity"),
                summary_date
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_broker_daily_activity(self, symbol, activity_list):
        """Batch insert broker daily activity menggunakan Upsert agar tidak saling menimpa kolom."""
        query = """
            INSERT INTO broker_daily_activity (
                symbol, date, close, change_val, value, volume, frequency,
                foreign_buy, foreign_sell, net_foreign, 
                domestic_buy, domestic_sell, net_domestic,
                foreign_buy_volume, foreign_sell_volume, net_foreign_volume,
                domestic_buy_volume, domestic_sell_volume, net_domestic_volume,
                foreign_buy_freq, foreign_sell_freq,
                domestic_buy_freq, domestic_sell_freq,
                foreign_value_pct, foreign_volume_pct, foreign_freq_pct,
                open, high, low, average, change_percentage,
                net_foreign_nego, net_foreign_all_market,
                net_foreign_volume_nego, net_foreign_volume_all_market,
                activity_date
            ) VALUES (
                %(symbol)s, %(date)s, %(close)s, %(change_val)s, %(value)s, %(volume)s, %(frequency)s,
                %(foreign_buy)s, %(foreign_sell)s, %(net_foreign)s,
                %(domestic_buy)s, %(domestic_sell)s, %(net_domestic)s,
                %(foreign_buy_volume)s, %(foreign_sell_volume)s, %(net_foreign_volume)s,
                %(domestic_buy_volume)s, %(domestic_sell_volume)s, %(net_domestic_volume)s,
                %(foreign_buy_freq)s, %(foreign_sell_freq)s,
                %(domestic_buy_freq)s, %(domestic_sell_freq)s,
                %(foreign_value_pct)s, %(foreign_volume_pct)s, %(foreign_freq_pct)s,
                %(open)s, %(high)s, %(low)s, %(average)s, %(change_percentage)s,
                %(net_foreign_nego)s, %(net_foreign_all_market)s,
                %(net_foreign_volume_nego)s, %(net_foreign_volume_all_market)s,
                %(activity_date)s
            ) ON CONFLICT(symbol, date, activity_date) DO UPDATE SET
                close = COALESCE(EXCLUDED.close, broker_daily_activity.close),
                change_val = COALESCE(EXCLUDED.change_val, broker_daily_activity.change_val),
                value = COALESCE(EXCLUDED.value, broker_daily_activity.value),
                volume = COALESCE(EXCLUDED.volume, broker_daily_activity.volume),
                frequency = COALESCE(EXCLUDED.frequency, broker_daily_activity.frequency),
                foreign_buy = COALESCE(EXCLUDED.foreign_buy, broker_daily_activity.foreign_buy),
                foreign_sell = COALESCE(EXCLUDED.foreign_sell, broker_daily_activity.foreign_sell),
                net_foreign = COALESCE(EXCLUDED.net_foreign, broker_daily_activity.net_foreign),
                domestic_buy = COALESCE(EXCLUDED.domestic_buy, broker_daily_activity.domestic_buy),
                domestic_sell = COALESCE(EXCLUDED.domestic_sell, broker_daily_activity.domestic_sell),
                net_domestic = COALESCE(EXCLUDED.net_domestic, broker_daily_activity.net_domestic),
                foreign_buy_volume = COALESCE(EXCLUDED.foreign_buy_volume, broker_daily_activity.foreign_buy_volume),
                foreign_sell_volume = COALESCE(EXCLUDED.foreign_sell_volume, broker_daily_activity.foreign_sell_volume),
                net_foreign_volume = COALESCE(EXCLUDED.net_foreign_volume, broker_daily_activity.net_foreign_volume),
                domestic_buy_volume = COALESCE(EXCLUDED.domestic_buy_volume, broker_daily_activity.domestic_buy_volume),
                domestic_sell_volume = COALESCE(EXCLUDED.domestic_sell_volume, broker_daily_activity.domestic_sell_volume),
                net_domestic_volume = COALESCE(EXCLUDED.net_domestic_volume, broker_daily_activity.net_domestic_volume),
                foreign_buy_freq = COALESCE(EXCLUDED.foreign_buy_freq, broker_daily_activity.foreign_buy_freq),
                foreign_sell_freq = COALESCE(EXCLUDED.foreign_sell_freq, broker_daily_activity.foreign_sell_freq),
                domestic_buy_freq = COALESCE(EXCLUDED.domestic_buy_freq, broker_daily_activity.domestic_buy_freq),
                domestic_sell_freq = COALESCE(EXCLUDED.domestic_sell_freq, broker_daily_activity.domestic_sell_freq),
                foreign_value_pct = COALESCE(EXCLUDED.foreign_value_pct, broker_daily_activity.foreign_value_pct),
                foreign_volume_pct = COALESCE(EXCLUDED.foreign_volume_pct, broker_daily_activity.foreign_volume_pct),
                foreign_freq_pct = COALESCE(EXCLUDED.foreign_freq_pct, broker_daily_activity.foreign_freq_pct),
                open = COALESCE(EXCLUDED.open, broker_daily_activity.open),
                high = COALESCE(EXCLUDED.high, broker_daily_activity.high),
                low = COALESCE(EXCLUDED.low, broker_daily_activity.low),
                average = COALESCE(EXCLUDED.average, broker_daily_activity.average),
                change_percentage = COALESCE(EXCLUDED.change_percentage, broker_daily_activity.change_percentage),
                net_foreign_nego = COALESCE(EXCLUDED.net_foreign_nego, broker_daily_activity.net_foreign_nego),
                net_foreign_all_market = COALESCE(EXCLUDED.net_foreign_all_market, broker_daily_activity.net_foreign_all_market),
                net_foreign_volume_nego = COALESCE(EXCLUDED.net_foreign_volume_nego, broker_daily_activity.net_foreign_volume_nego),
                net_foreign_volume_all_market = COALESCE(EXCLUDED.net_foreign_volume_all_market, broker_daily_activity.net_foreign_volume_all_market)
        """
        from datetime import datetime
        data_dicts = []
        for act in activity_list:
            d_str = act.get("date") or "2000-01-01"
            try:
                activity_date = datetime.strptime(d_str, "%Y-%m-%d").date()
            except Exception:
                activity_date = datetime.strptime("2000-01-01", "%Y-%m-%d").date()

            data_dicts.append({
                "symbol": symbol,
                "date": act.get("date"),
                "close": act.get("close"),
                "change_val": act.get("change_val"),
                "value": act.get("value"),
                "volume": act.get("volume"),
                "frequency": act.get("frequency"),
                "foreign_buy": act.get("foreign_buy"),
                "foreign_sell": act.get("foreign_sell"),
                "net_foreign": act.get("net_foreign"),
                "domestic_buy": act.get("domestic_buy"),
                "domestic_sell": act.get("domestic_sell"),
                "net_domestic": act.get("net_domestic"),
                "foreign_buy_volume": act.get("foreign_buy_volume"),
                "foreign_sell_volume": act.get("foreign_sell_volume"),
                "net_foreign_volume": act.get("net_foreign_volume"),
                "domestic_buy_volume": act.get("domestic_buy_volume"),
                "domestic_sell_volume": act.get("domestic_sell_volume"),
                "net_domestic_volume": act.get("net_domestic_volume"),
                "foreign_buy_freq": act.get("foreign_buy_freq"),
                "foreign_sell_freq": act.get("foreign_sell_freq"),
                "domestic_buy_freq": act.get("domestic_buy_freq"),
                "domestic_sell_freq": act.get("domestic_sell_freq"),
                "foreign_value_pct": act.get("foreign_value_pct"),
                "foreign_volume_pct": act.get("foreign_volume_pct"),
                "foreign_freq_pct": act.get("foreign_freq_pct"),
                "open": act.get("open"),
                "high": act.get("high"),
                "low": act.get("low"),
                "average": act.get("average"),
                "change_percentage": act.get("change_percentage"),
                "net_foreign_nego": act.get("net_foreign_nego"),
                "net_foreign_all_market": act.get("net_foreign_all_market"),
                "net_foreign_volume_nego": act.get("net_foreign_volume_nego"),
                "net_foreign_volume_all_market": act.get("net_foreign_volume_all_market"),
                "activity_date": activity_date
            })
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_dicts)
                conn.commit()
                return cursor.rowcount

