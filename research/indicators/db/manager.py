from .base_repository import BaseRepository
from .schema import initialize_schema
from .market_data_repository import MarketDataRepository
from .broker_repository import BrokerRepository
from .company_repository import CompanyRepository
from .config_repository import ConfigRepository
from .maintenance_repository import MaintenanceRepository

class StockbitDbManager(BaseRepository):
    def __init__(self, db_dsn=None, initialize=False):
        super().__init__(db_dsn)
        if initialize:
            # Inisialisasi skema tabel database — ambil raw conn dari pool, lalu kembalikan
            with self.get_connection() as conn:
                initialize_schema(conn)
        
        # Instansiasi repository per domain
        self.market = MarketDataRepository(db_dsn)
        self.broker = BrokerRepository(db_dsn)
        self.company = CompanyRepository(db_dsn)
        self.config = ConfigRepository(db_dsn)
        self.maintenance = MaintenanceRepository(db_dsn)


    # --- DELEGASI MARKET DATA DOMAIN ---
    def insert_ohlcv_data(self, ohlcv_list):
        return self.market.insert_ohlcv_data(ohlcv_list)

    def insert_running_trades(self, trades):
        return self.market.insert_running_trades(trades)

    def insert_trade_book(self, symbol, timestamp, book_items):
        return self.market.insert_trade_book(symbol, timestamp, book_items)

    def insert_price_grid(self, symbol, prices):
        return self.market.insert_price_grid(symbol, prices)

    def insert_orderbook_snapshot(self, symbol, timestamp, snap):
        return self.market.insert_orderbook_snapshot(symbol, timestamp, snap)

    def insert_order_queues(self, orders_list):
        return self.market.insert_order_queues(orders_list)

    # --- DELEGASI BROKER DOMAIN ---
    def insert_brokers(self, brokers_list):
        return self.broker.insert_brokers(brokers_list)

    def insert_conglomerates(self, conglomerates_list):
        return self.broker.insert_conglomerates(conglomerates_list)

    def insert_conglomerate_stocks(self, stocks_list):
        return self.broker.insert_conglomerate_stocks(stocks_list)

    def insert_conglomerate_brokers(self, brokers_list):
        return self.broker.insert_conglomerate_brokers(brokers_list)

    def insert_msci_stocks(self, msci_list):
        return self.broker.insert_msci_stocks(msci_list)

    def update_broker_profiles(self, profiles_list):
        return self.broker.update_broker_profiles(profiles_list)

    def insert_broker_summaries(self, summaries):
        return self.broker.insert_broker_summaries(summaries)

    def insert_broker_daily_activity(self, symbol, activity_list):
        return self.broker.insert_broker_daily_activity(symbol, activity_list)

    # --- DELEGASI COMPANY DOMAIN ---
    def insert_company_profile(self, p):
        return self.company.insert_company_profile(p)

    def insert_company_executives(self, symbol, execs):
        return self.company.insert_company_executives(symbol, execs)

    def insert_company_shareholders(self, symbol, holders):
        return self.company.insert_company_shareholders(symbol, holders)

    def insert_company_beneficiaries(self, symbol, beneficiaries):
        return self.company.insert_company_beneficiaries(symbol, beneficiaries)

    def insert_company_shareholder_stats(self, symbol, stats):
        return self.company.insert_company_shareholder_stats(symbol, stats)

    def insert_company_shareholding_compositions(self, symbol, report_date, compositions):
        return self.company.insert_company_shareholding_compositions(symbol, report_date, compositions)

    def insert_company_insider_transactions(self, symbol, movements):
        return self.company.insert_company_insider_transactions(symbol, movements)

    def insert_company_keystats(self, symbol, keystats_list):
        return self.company.insert_company_keystats(symbol, keystats_list)

    def insert_company_dividends(self, symbol, dividends):
        return self.company.insert_company_dividends(symbol, dividends)

    def insert_company_analyst_ratings(self, symbol, rating):
        return self.company.insert_company_analyst_ratings(symbol, rating)

    # --- DELEGASI CONFIG DOMAIN ---
    def insert_watchlists(self, watchlists_list):
        return self.config.insert_watchlists(watchlists_list)

    def insert_watchlist_items(self, watchlist_id, symbols):
        return self.config.insert_watchlist_items(watchlist_id, symbols)

    def insert_trading_preferences(self, preferences_list):
        return self.config.insert_trading_preferences(preferences_list)

    def get_trading_preference(self, strategy_name):
        return self.config.get_trading_preference(strategy_name)

    # --- DELEGASI MAINTENANCE DOMAIN ---
    def clean_database(self):
        return self.maintenance.clean_database()

    def verify_integrity(self):
        return self.maintenance.verify_integrity()

    def optimize_database(self):
        return self.maintenance.optimize_database()
