-- Active: TimescaleDB + PostgreSQL

-- 1. Aktifkan ekstensi TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. Tentukan Skema Tabel Relasional

-- ============================================================================
-- DOMAIN: MARKET DATA (TIME-SERIES & MICROSTRUCTURE)
-- ============================================================================

-- A. Tabel Running Trade (Tick-by-tick)
CREATE TABLE IF NOT EXISTS running_trades (
    id BIGSERIAL,
    trade_id TEXT NOT NULL,
    trade_number BIGINT,
    timestamp DOUBLE PRECISION,
    time_str TEXT,
    symbol VARCHAR(10) NOT NULL,
    price INT,
    lot DOUBLE PRECISION,
    value BIGINT,
    action VARCHAR(10),
    market_board VARCHAR(20),
    buyer_broker VARCHAR(10),
    seller_broker VARCHAR(10),
    buyer_type VARCHAR(50),
    seller_type VARCHAR(50),
    buy_order_number VARCHAR(50),
    sell_order_number VARCHAR(50),
    group_order_number VARCHAR(50),
    is_broker_exists INT,
    change_percent VARCHAR(20),
    time TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_running_trades UNIQUE (time, trade_id)
);

-- B. Tabel Trade Book (Peta Likuiditas)
CREATE TABLE IF NOT EXISTS trade_book (
    id BIGSERIAL,
    timestamp DOUBLE PRECISION,
    symbol VARCHAR(10) NOT NULL,
    price INT,
    buy_lot BIGINT,
    buy_freq INT,
    sell_lot BIGINT,
    sell_freq INT,
    total_lot BIGINT,
    time TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_trade_book UNIQUE (symbol, price, timestamp, time)
);

-- C. Tabel Price Grids (Fraksi Harga Valid)
CREATE TABLE IF NOT EXISTS price_grids (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price INT NOT NULL,
    CONSTRAINT uq_price_grids UNIQUE (symbol, price)
);

-- D. Tabel OHLCV Data (Daily & Intraday 1-Min)
CREATE TABLE IF NOT EXISTS ohlcv_data (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    date VARCHAR(20) NOT NULL,
    time VARCHAR(20) NOT NULL,
    open INT,
    high INT,
    low INT,
    close INT,
    volume BIGINT,
    value DOUBLE PRECISION,
    frequency INT,
    foreign_buy BIGINT,
    foreign_sell BIGINT,
    unix_timestamp BIGINT,
    foreign_flow BIGINT,
    market_cap BIGINT,
    dividend DOUBLE PRECISION,
    shares_outstanding BIGINT,
    freq_analyzer DOUBLE PRECISION,
    candle_time TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_ohlcv UNIQUE (symbol, date, time, candle_time)
);

-- E. Tabel Orderbook Snapshots (Perekaman Snapshot Orderbook Depth)
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id BIGSERIAL,
    timestamp DOUBLE PRECISION,
    symbol VARCHAR(10) NOT NULL,
    close_price INT,
    total_bid_lot BIGINT,
    total_bid_freq INT,
    total_offer_lot BIGINT,
    total_offer_freq INT,
    ara_price INT,
    arb_price INT,
    foreign_buy_val DOUBLE PRECISION,
    foreign_sell_val DOUBLE PRECISION,
    foreign_net_val DOUBLE PRECISION,
    domestic_pct DOUBLE PRECISION,
    foreign_pct DOUBLE PRECISION,
    time TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_obs UNIQUE (symbol, timestamp, time)
);

-- F. Tabel Orderbook Ticks (Detail Baris Antrean Bid/Offer)
-- Catatan: Tanpa physical foreign key constraint ke orderbook_snapshots karena batasan hypertable, disinkronkan di level aplikasi
CREATE TABLE IF NOT EXISTS orderbook_ticks (
    id BIGSERIAL,
    snapshot_id BIGINT NOT NULL,
    type VARCHAR(10) NOT NULL, -- 'BID' / 'OFFER'
    price INT NOT NULL,
    volume BIGINT NOT NULL,
    que_num INT
);

-- G. Tabel Order Queues (Buku Antrean Tiket Order)
CREATE TABLE IF NOT EXISTS order_queues (
    id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    queue_number INT,
    time_str VARCHAR(50),
    action_type VARCHAR(50),
    price INT,
    status VARCHAR(50),
    open_lot BIGINT,
    total_lot BIGINT,
    broker_code VARCHAR(10),
    broker_group VARCHAR(50),
    order_number VARCHAR(50)
);

-- ============================================================================
-- DOMAIN: BROKER & CONGLOMERATION METADATA
-- ============================================================================

-- H. Tabel Brokers (Master Data Sekuritas)
CREATE TABLE IF NOT EXISTS brokers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name TEXT,
    group_type VARCHAR(50),
    color VARCHAR(20),
    membership_type VARCHAR(50),
    retail_density VARCHAR(20),
    typical_style VARCHAR(50),
    tier INT
);

-- I. Tabel Broker Summaries (EOD Bandar Akumulasi)
CREATE TABLE IF NOT EXISTS broker_summaries (
    id BIGSERIAL,
    date VARCHAR(20) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    broker_code VARCHAR(10) NOT NULL,
    type VARCHAR(20),
    net_lot BIGINT,
    total_volume_lot BIGINT,
    avg_price DOUBLE PRECISION,
    net_value DOUBLE PRECISION,
    total_volume_value DOUBLE PRECISION,
    freq INT,
    activity VARCHAR(50),
    summary_date DATE NOT NULL,
    CONSTRAINT uq_broker_sum UNIQUE (date, symbol, broker_code, summary_date)
);

-- J. Tabel Broker Daily Activity (Data Historis Harian Saham & Foreign Flow)
CREATE TABLE IF NOT EXISTS broker_daily_activity (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    date VARCHAR(20) NOT NULL,
    close INT,
    change_val INT,
    value BIGINT,
    volume BIGINT,
    frequency INT,
    foreign_buy BIGINT,
    foreign_sell BIGINT,
    net_foreign BIGINT,
    domestic_buy BIGINT,
    domestic_sell BIGINT,
    net_domestic BIGINT,
    foreign_buy_volume BIGINT,
    foreign_sell_volume BIGINT,
    net_foreign_volume BIGINT,
    domestic_buy_volume BIGINT,
    domestic_sell_volume BIGINT,
    net_domestic_volume BIGINT,
    foreign_buy_freq INT,
    foreign_sell_freq INT,
    domestic_buy_freq INT,
    domestic_sell_freq INT,
    foreign_value_pct DOUBLE PRECISION,
    foreign_volume_pct DOUBLE PRECISION,
    foreign_freq_pct DOUBLE PRECISION,
    open INT,
    high INT,
    low INT,
    average INT,
    change_percentage DOUBLE PRECISION,
    net_foreign_nego BIGINT,
    net_foreign_all_market BIGINT,
    net_foreign_volume_nego BIGINT,
    net_foreign_volume_all_market BIGINT,
    activity_date DATE NOT NULL,
    CONSTRAINT uq_bda UNIQUE (symbol, date, activity_date)
);

-- K. Tabel Conglomerates (Master Group Konglomerat)
CREATE TABLE IF NOT EXISTS conglomerates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    owner_name TEXT,
    description TEXT
);

-- L. Tabel Conglomerate Stocks (Pemetaan Emiten Grup)
CREATE TABLE IF NOT EXISTS conglomerate_stocks (
    id SERIAL PRIMARY KEY,
    conglomerate_name VARCHAR(100) REFERENCES conglomerates(name) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    CONSTRAINT uq_congl_stock UNIQUE (conglomerate_name, symbol)
);

-- M. Tabel Conglomerate Brokers (Pemetaan Sekuritas Afiliasi)
CREATE TABLE IF NOT EXISTS conglomerate_brokers (
    id SERIAL PRIMARY KEY,
    conglomerate_name VARCHAR(100) REFERENCES conglomerates(name) ON DELETE CASCADE,
    broker_code VARCHAR(10) REFERENCES brokers(code) ON DELETE CASCADE,
    CONSTRAINT uq_congl_broker UNIQUE (conglomerate_name, broker_code)
);

-- N. Tabel MSCI Tracker (Konstituen Indeks MSCI)
CREATE TABLE IF NOT EXISTS msci_tracker (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    index_type VARCHAR(50),
    status VARCHAR(20),
    effective_date VARCHAR(20)
);

-- ============================================================================
-- DOMAIN: COMPANY PROFILES & KEY STATS (FUNDAMENTAL)
-- ============================================================================

-- O. Tabel Company Profiles
CREATE TABLE IF NOT EXISTS company_profiles (
    symbol VARCHAR(10) PRIMARY KEY,
    name TEXT,
    background TEXT,
    board VARCHAR(50),
    listing_date VARCHAR(20),
    price INT,
    shares TEXT,
    registrar TEXT,
    underwriters TEXT,
    administrative_bureau TEXT,
    free_float TEXT,
    sector TEXT,
    sub_sector TEXT,
    exchange VARCHAR(50),
    country VARCHAR(50),
    created_at VARCHAR(50),
    followers INT,
    market_cap BIGINT,
    enterprise_value BIGINT
);

-- P. Tabel Company Executives
CREATE TABLE IF NOT EXISTS company_executives (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    executive_id VARCHAR(50),
    last_update VARCHAR(50),
    CONSTRAINT uq_exec UNIQUE (symbol, name, role)
);

-- Q. Tabel Company Shareholders
CREATE TABLE IF NOT EXISTS company_shareholders (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    name TEXT NOT NULL,
    percentage DOUBLE PRECISION,
    value TEXT,
    badges TEXT,
    location TEXT,
    nationality TEXT,
    domicile TEXT,
    classification TEXT,
    scripless VARCHAR(20),
    scrip VARCHAR(20),
    type VARCHAR(50),
    parent_id VARCHAR(50),
    date VARCHAR(20) NOT NULL,
    CONSTRAINT uq_holder UNIQUE (symbol, name, date)
);

-- R. Tabel Company Beneficiaries
CREATE TABLE IF NOT EXISTS company_beneficiaries (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    name TEXT NOT NULL,
    CONSTRAINT uq_benef UNIQUE (symbol, name)
);

-- S. Tabel Company Shareholder Stats
CREATE TABLE IF NOT EXISTS company_shareholder_stats (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    shareholder_date VARCHAR(20) NOT NULL,
    total_shareholder INT,
    change_value INT,
    change_formatted TEXT,
    CONSTRAINT uq_sh_stats UNIQUE (symbol, shareholder_date)
);

-- T. Tabel Company Shareholding Compositions
CREATE TABLE IF NOT EXISTS company_shareholding_compositions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    report_date VARCHAR(20) NOT NULL,
    label TEXT NOT NULL,
    shares BIGINT,
    percentage DOUBLE PRECISION,
    CONSTRAINT uq_composition UNIQUE (symbol, report_date, label)
);

-- U. Tabel Company Insider Transactions
CREATE TABLE IF NOT EXISTS company_insider_transactions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    name TEXT NOT NULL,
    date VARCHAR(20) NOT NULL,
    previous_value BIGINT,
    previous_percentage DOUBLE PRECISION,
    current_value BIGINT,
    current_percentage DOUBLE PRECISION,
    changes_value BIGINT,
    changes_percentage DOUBLE PRECISION,
    action_type TEXT,
    nationality TEXT,
    data_source TEXT,
    price INT,
    broker_code VARCHAR(10),
    CONSTRAINT uq_insider UNIQUE (symbol, name, date, changes_value, action_type)
);

-- V. Tabel Company Keystats (Financial metrics)
CREATE TABLE IF NOT EXISTS company_keystats (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    year VARCHAR(20) NOT NULL,
    period VARCHAR(20) NOT NULL,
    metric_name TEXT NOT NULL,
    value TEXT,
    CONSTRAINT uq_keystats UNIQUE (symbol, year, period, metric_name)
);

-- W. Tabel Company Dividends
CREATE TABLE IF NOT EXISTS company_dividends (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    year INT NOT NULL,
    dividend DOUBLE PRECISION,
    ex_date VARCHAR(20) NOT NULL,
    payment_date VARCHAR(20),
    CONSTRAINT uq_dividends UNIQUE (symbol, ex_date, year)
);

-- X. Tabel Company Analyst Ratings
CREATE TABLE IF NOT EXISTS company_analyst_ratings (
    symbol VARCHAR(10) PRIMARY KEY REFERENCES company_profiles(symbol) ON DELETE CASCADE,
    consensus_rating VARCHAR(50),
    target_price DOUBLE PRECISION,
    buy_count INT,
    hold_count INT,
    sell_count INT,
    last_update VARCHAR(50)
);

-- ============================================================================
-- DOMAIN: CONFIGURATION & USER PREFERENCES
-- ============================================================================

-- Y. Tabel Watchlists
CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    watchlist_id INT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_default INT,
    is_favorite INT,
    category_type VARCHAR(50)
);

-- Z. Tabel Watchlist Items
CREATE TABLE IF NOT EXISTS watchlist_items (
    id SERIAL PRIMARY KEY,
    watchlist_id INT REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    CONSTRAINT uq_wl_item UNIQUE (watchlist_id, symbol)
);

-- AA. Tabel Trading Preferences
CREATE TABLE IF NOT EXISTS trading_preferences (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(50) UNIQUE NOT NULL,
    max_entry_premium_pct DOUBLE PRECISION,
    stop_loss_buffer_pct DOUBLE PRECISION,
    risk_reward_ratio DOUBLE PRECISION,
    min_haka_ratio DOUBLE PRECISION,
    min_smart_money_score DOUBLE PRECISION,
    max_portfolio_allocation DOUBLE PRECISION
);

-- ============================================================================
-- AUTOMATED TRIGGERS FOR DATETIME NORMALIZATION (SQLITE-COMPATIBILITY SHIM)
-- ============================================================================

-- 1. Trigger Function: Epoch Float -> TIMESTAMPTZ (untuk running_trades, trade_book, orderbook_snapshots)
CREATE OR REPLACE FUNCTION set_time_from_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.time IS NULL THEN
        NEW.time := COALESCE(to_timestamp(NEW.timestamp), NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_running_trades_time ON running_trades;
CREATE TRIGGER trg_running_trades_time
BEFORE INSERT ON running_trades
FOR EACH ROW EXECUTE FUNCTION set_time_from_timestamp();

DROP TRIGGER IF EXISTS trg_trade_book_time ON trade_book;
CREATE TRIGGER trg_trade_book_time
BEFORE INSERT ON trade_book
FOR EACH ROW EXECUTE FUNCTION set_time_from_timestamp();

DROP TRIGGER IF EXISTS trg_orderbook_snapshots_time ON orderbook_snapshots;
CREATE TRIGGER trg_orderbook_snapshots_time
BEFORE INSERT ON orderbook_snapshots
FOR EACH ROW EXECUTE FUNCTION set_time_from_timestamp();


-- 2. Trigger Function: Unix Timestamp Int -> TIMESTAMPTZ (untuk ohlcv_data)
CREATE OR REPLACE FUNCTION set_candle_time_from_unix()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.candle_time IS NULL THEN
        IF NEW.unix_timestamp IS NOT NULL THEN
            NEW.candle_time := to_timestamp(NEW.unix_timestamp);
        ELSIF NEW.date IS NOT NULL THEN
            NEW.candle_time := COALESCE(to_date(NEW.date, 'YYYY-MM-DD'), NOW());
        ELSE
            NEW.candle_time := NOW();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ohlcv_data_time ON ohlcv_data;
CREATE TRIGGER trg_ohlcv_data_time
BEFORE INSERT ON ohlcv_data
FOR EACH ROW EXECUTE FUNCTION set_candle_time_from_unix();


-- 3. Trigger Function: Date String (YYYY-MM-DD) -> DATE (untuk broker_summaries, broker_daily_activity)
CREATE OR REPLACE FUNCTION set_date_cols()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.summary_date IS NULL THEN
        NEW.summary_date := COALESCE(to_date(NEW.date, 'YYYY-MM-DD'), CURRENT_DATE);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_broker_summaries_date ON broker_summaries;
CREATE TRIGGER trg_broker_summaries_date
BEFORE INSERT ON broker_summaries
FOR EACH ROW EXECUTE FUNCTION set_date_cols();

CREATE OR REPLACE FUNCTION set_activity_date_cols()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.activity_date IS NULL THEN
        NEW.activity_date := COALESCE(to_date(NEW.date, 'YYYY-MM-DD'), CURRENT_DATE);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_broker_daily_activity_date ON broker_daily_activity;
CREATE TRIGGER trg_broker_daily_activity_date
BEFORE INSERT ON broker_daily_activity
FOR EACH ROW EXECUTE FUNCTION set_activity_date_cols();


-- ============================================================================
-- TIMESCALEDB HYPERTABLES SETUP
-- ============================================================================

-- Konversi tabel time-series ke Hypertables
SELECT create_hypertable('running_trades', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('ohlcv_data', 'candle_time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('broker_daily_activity', 'activity_date', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('broker_summaries', 'summary_date', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('trade_book', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('orderbook_snapshots', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================================================
-- INDEXES FOR HIGH-PERFORMANCE QUERYING
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_trades_symbol_num ON running_trades(symbol, trade_number DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_time ON ohlcv_data(symbol, candle_time DESC);
CREATE INDEX IF NOT EXISTS idx_broker_sum_sym_date ON broker_summaries(symbol, summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_bda_sym_date ON broker_daily_activity(symbol, activity_date DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_ticks_snap ON orderbook_ticks(snapshot_id);

-- ============================================================================
-- TIMESCALEDB COMPRESSION POLICY
-- ============================================================================
-- Aktifkan kompresi kolumnar untuk hemat disk space (rasio ~5x-10x)
ALTER TABLE running_trades SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC, trade_number DESC'
);

ALTER TABLE ohlcv_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'candle_time DESC'
);

ALTER TABLE broker_summaries SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, broker_code',
    timescaledb.compress_orderby = 'summary_date DESC'
);

ALTER TABLE broker_daily_activity SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'activity_date DESC'
);

-- Jalankan kebijakan kompresi otomatis untuk data > 14 hari
SELECT add_compression_policy('running_trades', INTERVAL '14 days', if_not_exists => TRUE);
SELECT add_compression_policy('ohlcv_data', INTERVAL '14 days', if_not_exists => TRUE);
SELECT add_compression_policy('broker_summaries', INTERVAL '14 days', if_not_exists => TRUE);
SELECT add_compression_policy('broker_daily_activity', INTERVAL '14 days', if_not_exists => TRUE);
