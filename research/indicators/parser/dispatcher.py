from .market_data_handlers import (
    parse_running_trade,
    parse_trade_book,
    parse_price_grid,
    parse_chart_ohlcv,
    parse_chartbit_candles,
    parse_orderbook_snapshot,
    parse_order_queue
)
from .broker_handlers import (
    parse_brokers_catalog,
    parse_broker_summary,
    parse_broker_daily_activity,
    parse_foreign_domestic_flow
)
from .company_handlers import (
    parse_emiten_profile,
    parse_emiten_info,
    parse_shareholding_composition,
    parse_major_holder_movements,
    parse_keystats_and_dividends,
    parse_analyst_ratings,
    parse_analyst_consensus
)
from .config_handlers import (
    parse_watchlists,
    parse_watchlist_items
)

# Urutan Dispatcher Predicate list - SAMA PERSIS dengan urutan if/elif di parser lama.
DISPATCH_PATTERNS = [
    # 1. Running Trade
    (lambda p: p == "/order-trade/running-trade", parse_running_trade, "trades"),
    
    # 6. Brokers Catalog
    (lambda p: p == "/findata-view/marketdetectors/brokers", parse_brokers_catalog, None),
    
    # 2. Market Detector (EOD Broker Summary)
    (lambda p: p.startswith("/marketdetectors/"), parse_broker_summary, "broker_summaries"),
    
    # 3. Trade Book
    (lambda p: p == "/order-trade/trade-book", parse_trade_book, None),
    
    # 4. Price Grid
    (lambda p: p == "/company-price-feed/prices", parse_price_grid, None),
    
    # 5. Chart data (OHLCV)
    (lambda p: p.startswith("/order-trade/running-trade/chart/"), parse_chart_ohlcv, None),
    
    # 5b. Rich Chartbit candles
    (lambda p: p.startswith("/chartbit/") and "/price/" in p, parse_chartbit_candles, None),
    
    # 7. User Watchlists list
    (lambda p: p == "/watchlist", parse_watchlists, None),
    
    # 8. Watchlist Details
    (lambda p: p.startswith("/watchlist/"), parse_watchlist_items, None),
    
    # 9. Broker Daily Activity
    (lambda p: p.startswith("/company-price-feed/historical/summary/"), parse_broker_daily_activity, None),
    
    # 10. Foreign-Domestic Flow
    (lambda p: p.startswith("/findata-view/foreign-domestic/v1/chart-data/"), parse_foreign_domestic_flow, None),
    
    # 11. Orderbook Snapshot
    (lambda p: p.startswith("/company-price-feed/v2/orderbook/companies/"), parse_orderbook_snapshot, None),
    
    # 12. Order Queue
    (lambda p: p == "/order-trade/order-queue", parse_order_queue, None),
    
    # 13. Emiten Profile
    (lambda p: p.startswith("/emitten/") and p.endswith("/profile"), parse_emiten_profile, None),
    
    # 14. Emiten Info
    (lambda p: p.startswith("/emitten/") and p.endswith("/info"), parse_emiten_info, None),
    
    # 15. Insider Shareholding Composition
    (lambda p: p.startswith("/insider/shareholding/composition/companies/"), parse_shareholding_composition, None),
    
    # 16. Insider Company Major Holders Movements
    (lambda p: p == "/insider/company/majorholder", parse_major_holder_movements, None),
    
    # 17. Key Stats & Dividends
    (lambda p: p.startswith("/keystats/ratio/v1/"), parse_keystats_and_dividends, None),
    
    # 18. Analyst Ratings
    (lambda p: p.startswith("/analyst-ratings/") and not p.endswith("/consensus"), parse_analyst_ratings, None),
    
    # 19. Analyst Consensus
    (lambda p: p.startswith("/analyst-ratings/") and p.endswith("/consensus"), parse_analyst_consensus, None),
]

def dispatch(db, path, parsed_url, payload, timestamp):
    """
    Mengevaluasi predicate sekuensial untuk mencari handler yang cocok.
    Mengembalikan dict data jika handler membutuhkan batch insert (e.g. {"trades": [...]}),
    atau None jika handler langsung memproses insert ke DB secara mandiri.
    """
    for predicate_fn, handler_fn, batch_key in DISPATCH_PATTERNS:
        if predicate_fn(path):
            result = handler_fn(db, path, parsed_url, payload, timestamp)
            if batch_key:
                return {batch_key: result}
            return None
    return None
