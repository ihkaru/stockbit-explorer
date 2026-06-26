# Configuration for Stockbit Historical Backloader

import os

# Checkpoint file path to save progress
CHECKPOINT_PATH = os.path.join("data", "backload_progress.json")

# Default settings
DEFAULT_START_DATE = "2021-01-01"
DEFAULT_END_DATE = "2026-06-26"
DEFAULT_DELAY_MS = 50  # Throttle to avoid rate limits (HTTP 429)

# Pre-defined Ticker Groups for Backloading
TICKER_GROUPS = {
    "LQ45": [
        "ACES", "ADRO", "AKRA", "AMRT", "ANTM", "ARTO", "ASII", "BBCA", "BBNI", "BBRI",
        "BBTN", "BMRI", "BRIS", "BRPT", "BUKA", "CPIN", "EMTK", "ESSA", "EXCL", "GOTO",
        "HRUM", "ICBP", "INDF", "INKP", "INTP", "ITMG", "JSMR", "KLBF", "MDKA", "MEDC",
        "MIKA", "PGAS", "PTBA", "SIDO", "SMGR", "SRTG", "TLKM", "TOWR", "TPIA", "UNTR",
        "UNVR", "VALE", "PTRO", "CUAN", "BREN"
    ],
    "MSCI": [
        "BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "TLKM", "GOTO", "ICBP", "INDF", "UNVR",
        "ADRO", "UNTR", "PTBA", "MDKA", "ASII", "SMGR", "KLBF", "CPIN", "CTRA", "AMRT"
    ],
    "BLUECHIP": [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP", "INDF", "ADRO",
        "KLBF", "PGAS"
    ]
}

# Mapping of data types to their description and API paths
DATA_TYPE_METADATA = {
    "ohlcv": {
        "description": "Daily OHLCV Candlesticks (including Foreign Flow info)",
        "api_method": "get_daily_candles",
        "path_prefix": "/chartbit/"
    },
    "broker-summary": {
        "description": "EOD Broker Summary (Buyers & Sellers net transactions)",
        "api_method": "get_market_detector",
        "path_prefix": "/marketdetectors/"
    },
    "foreign-flow": {
        "description": "Historical Summary of Net Foreign Flow (Daily Broker Activity)",
        "api_method": "get_historical_summary",
        "path_prefix": "/company-price-feed/historical/summary/"
    }
}
