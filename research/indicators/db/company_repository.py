from .base_repository import BaseRepository

class CompanyRepository(BaseRepository):
    def insert_company_profile(self, p):
        query = """
            INSERT INTO company_profiles (
                symbol, name, background, board, listing_date, price, shares,
                registrar, underwriters, administrative_bureau, free_float,
                sector, sub_sector, exchange, country, created_at, followers,
                market_cap, enterprise_value
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(symbol) DO UPDATE SET
                name = COALESCE(EXCLUDED.name, company_profiles.name),
                background = COALESCE(EXCLUDED.background, company_profiles.background),
                board = COALESCE(EXCLUDED.board, company_profiles.board),
                listing_date = COALESCE(EXCLUDED.listing_date, company_profiles.listing_date),
                price = COALESCE(EXCLUDED.price, company_profiles.price),
                shares = COALESCE(EXCLUDED.shares, company_profiles.shares),
                registrar = COALESCE(EXCLUDED.registrar, company_profiles.registrar),
                underwriters = COALESCE(EXCLUDED.underwriters, company_profiles.underwriters),
                administrative_bureau = COALESCE(EXCLUDED.administrative_bureau, company_profiles.administrative_bureau),
                free_float = COALESCE(EXCLUDED.free_float, company_profiles.free_float),
                sector = COALESCE(EXCLUDED.sector, company_profiles.sector),
                sub_sector = COALESCE(EXCLUDED.sub_sector, company_profiles.sub_sector),
                exchange = COALESCE(EXCLUDED.exchange, company_profiles.exchange),
                country = COALESCE(EXCLUDED.country, company_profiles.country),
                created_at = COALESCE(EXCLUDED.created_at, company_profiles.created_at),
                followers = COALESCE(EXCLUDED.followers, company_profiles.followers),
                market_cap = COALESCE(EXCLUDED.market_cap, company_profiles.market_cap),
                enterprise_value = COALESCE(EXCLUDED.enterprise_value, company_profiles.enterprise_value)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    p.get("symbol"), p.get("name"), p.get("background"), p.get("board"),
                    p.get("listing_date"), p.get("price"), p.get("shares"), p.get("registrar"),
                    ",".join(p.get("underwriters", [])) if isinstance(p.get("underwriters"), list) else p.get("underwriters"),
                    p.get("administrative_bureau"), p.get("free_float"), p.get("sector"),
                    p.get("sub_sector"), p.get("exchange"), p.get("country"), p.get("created_at"),
                    p.get("followers"), p.get("market_cap"), p.get("enterprise_value")
                ))
                conn.commit()
                return cursor.rowcount

    def insert_company_executives(self, symbol, execs):
        query = """
            INSERT INTO company_executives (symbol, name, role, executive_id, last_update)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(symbol, name, role) DO UPDATE SET
                executive_id = EXCLUDED.executive_id,
                last_update = EXCLUDED.last_update
        """
        data_tuples = []
        for e in execs:
            data_tuples.append((symbol, e.get("name"), e.get("role"), e.get("executive_id"), e.get("last_update")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_shareholders(self, symbol, holders):
        query = """
            INSERT INTO company_shareholders (
                symbol, name, percentage, value, badges, location, nationality,
                domicile, classification, scripless, scrip, type, parent_id, date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(symbol, name, date) DO UPDATE SET
                percentage = EXCLUDED.percentage,
                value = EXCLUDED.value,
                badges = EXCLUDED.badges,
                location = EXCLUDED.location,
                nationality = EXCLUDED.nationality,
                domicile = EXCLUDED.domicile,
                classification = EXCLUDED.classification,
                scripless = EXCLUDED.scripless,
                scrip = EXCLUDED.scrip,
                type = EXCLUDED.type,
                parent_id = EXCLUDED.parent_id
        """
        data_tuples = []
        for h in holders:
            badges_val = h.get("badges")
            if isinstance(badges_val, list):
                badges_str = ",".join(badges_val)
            else:
                badges_str = badges_val
            data_tuples.append((
                symbol, h.get("name"), h.get("percentage"), h.get("value"), badges_str,
                h.get("location"), h.get("nationality"), h.get("domicile"), h.get("classification"),
                h.get("scripless"), h.get("scrip"), h.get("type"), h.get("parent_id"), h.get("date")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_beneficiaries(self, symbol, beneficiaries):
        query = """
            INSERT INTO company_beneficiaries (symbol, name)
            VALUES (%s, %s)
            ON CONFLICT (symbol, name) DO NOTHING
        """
        data_tuples = [(symbol, b) for b in beneficiaries]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_shareholder_stats(self, symbol, stats):
        query = """
            INSERT INTO company_shareholder_stats (
                symbol, shareholder_date, total_shareholder, change_value, change_formatted
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (symbol, shareholder_date) DO UPDATE SET
                total_shareholder = EXCLUDED.total_shareholder,
                change_value = EXCLUDED.change_value,
                change_formatted = EXCLUDED.change_formatted
        """
        data_tuples = []
        for s in stats:
            data_tuples.append((symbol, s.get("shareholder_date"), s.get("total_shareholder"), s.get("change_value"), s.get("change_formatted")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_shareholding_compositions(self, symbol, report_date, compositions):
        query = """
            INSERT INTO company_shareholding_compositions (
                symbol, report_date, label, shares, percentage
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (symbol, report_date, label) DO UPDATE SET
                shares = EXCLUDED.shares,
                percentage = EXCLUDED.percentage
        """
        data_tuples = []
        for c in compositions:
            data_tuples.append((symbol, report_date, c.get("label"), c.get("shares"), c.get("percentage")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_insider_transactions(self, symbol, movements):
        query = """
            INSERT INTO company_insider_transactions (
                symbol, name, date, previous_value, previous_percentage,
                current_value, current_percentage, changes_value, changes_percentage,
                action_type, nationality, data_source, price, broker_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, name, date, changes_value, action_type) DO UPDATE SET
                previous_value = EXCLUDED.previous_value,
                previous_percentage = EXCLUDED.previous_percentage,
                current_value = EXCLUDED.current_value,
                current_percentage = EXCLUDED.current_percentage,
                changes_percentage = EXCLUDED.changes_percentage,
                nationality = EXCLUDED.nationality,
                data_source = EXCLUDED.data_source,
                price = EXCLUDED.price,
                broker_code = EXCLUDED.broker_code
        """
        data_tuples = []
        for m in movements:
            data_tuples.append((
                symbol, m.get("name"), m.get("date"), m.get("previous_value"), m.get("previous_percentage"),
                m.get("current_value"), m.get("current_percentage"), m.get("changes_value"), m.get("changes_percentage"),
                m.get("action_type"), m.get("nationality"), m.get("data_source"), m.get("price"), m.get("broker_code")
            ))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_keystats(self, symbol, keystats_list):
        query = """
            INSERT INTO company_keystats (symbol, year, period, metric_name, value)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (symbol, year, period, metric_name) DO UPDATE SET
                value = EXCLUDED.value
        """
        data_tuples = []
        for k in keystats_list:
            data_tuples.append((symbol, k.get("year"), k.get("period"), k.get("metric_name"), k.get("value")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_dividends(self, symbol, dividends):
        query = """
            INSERT INTO company_dividends (symbol, year, dividend, ex_date, payment_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (symbol, ex_date, year) DO UPDATE SET
                dividend = EXCLUDED.dividend,
                payment_date = EXCLUDED.payment_date
        """
        data_tuples = []
        for d in dividends:
            data_tuples.append((symbol, d.get("year"), d.get("dividend"), d.get("ex_date"), d.get("payment_date")))
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, data_tuples)
                conn.commit()
                return cursor.rowcount

    def insert_company_analyst_ratings(self, symbol, rating):
        query = """
            INSERT INTO company_analyst_ratings (
                symbol, consensus_rating, target_price, buy_count, hold_count, sell_count, last_update
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                consensus_rating = EXCLUDED.consensus_rating,
                target_price = EXCLUDED.target_price,
                buy_count = EXCLUDED.buy_count,
                hold_count = EXCLUDED.hold_count,
                sell_count = EXCLUDED.sell_count,
                last_update = EXCLUDED.last_update
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    symbol, rating.get("consensus_rating"), rating.get("target_price"),
                    rating.get("buy_count"), rating.get("hold_count"), rating.get("sell_count"), rating.get("last_update")
                ))
                conn.commit()
                return cursor.rowcount

