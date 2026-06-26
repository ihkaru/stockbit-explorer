import json
import os
import requests
import urllib3
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Disable SSL verification warnings since we are using mitmproxy self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class StockbitApiClient:
    """
    Client API Mandiri untuk berinteraksi dengan exodus.stockbit.com
    menggunakan session token yang ditangkap oleh interceptor.
    """
    def __init__(self, headers_path=None):
        self.headers_path = headers_path or os.environ.get("STOCKBIT_HEADERS_PATH", "data/session_headers.json")
        self.headers = {}
        self.load_headers()

    def load_headers(self):
        """Membaca session headers terbaru yang ditangkap proxy."""
        if not os.path.exists(self.headers_path):
            raise FileNotFoundError(
                f"Session headers file tidak ditemukan di '{self.headers_path}'. "
                "Pastikan interceptor (proxy) sudah berjalan dan menangkap request dari Stockbit Desktop."
            )
        with open(self.headers_path, "r", encoding="utf-8") as f:
            self.headers = json.load(f)

    def _get(self, url, params=None):
        """Helper untuk melakukan HTTP GET request dengan error handling."""
        # Selalu reload headers terbaru untuk mengantisipasi auto-refresh token
        self.load_headers()
        
        try:
            # Menggunakan verify=False agar tidak SSL Error saat mitmproxy aktif
            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=10, proxies={"http": None, "https": None})
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"API Error [{response.status_code}] on GET {url}: {response.text}")
                response.raise_for_status()
        except Exception as e:
            logging.error(f"Request failed to {url}: {e}")
            raise

    def get_running_trade(self, symbols=None, limit=80, trade_number=None, cursor_direction=None, date=None):
        """
        Mengambil data running trade.
        symbols: list of str, contoh ['BBCA', 'TLKM'] atau None untuk semua saham
        limit: jumlah data yang diambil
        trade_number & cursor_direction: digunakan untuk pagination scroll (CURSOR_DIRECTION_NEXT)
        date: tanggal historis format 'YYYY-MM-DD'
        """
        url = "https://exodus.stockbit.com/order-trade/running-trade"
        params = {
            "limit": limit,
            "action_type": "RUNNING_TRADE_ACTION_TYPE_ALL",
            "market_board": "BOARD_TYPE_ALL",
            "sort": "desc",
            "order_by": "RUNNING_TRADE_ORDER_BY_TIME"
        }
        if symbols:
            # API mendukung symbols[] sebagai list parameter
            params["symbols[]"] = symbols
        if trade_number and cursor_direction:
            params["trade_number"] = trade_number
            params["cursor_direction"] = cursor_direction
        if date:
            params["date"] = date
            
        return self._get(url, params)

    def get_trade_book(self, symbol, group_by="GROUP_BY_PRICE"):
        """Mengambil data volume bid/offer berdasarkan harga (trade book)."""
        url = "https://exodus.stockbit.com/order-trade/trade-book"
        params = {
            "symbol": symbol,
            "group_by": group_by
        }
        return self._get(url, params)

    def get_order_queue(self, stock_code):
        """Mengambil antrean bid/offer detail (Order Queue)."""
        url = "https://exodus.stockbit.com/order-trade/order-queue"
        params = {
            "stock_code": stock_code
        }
        return self._get(url, params)

    def get_market_detector(self, stock_code, from_date, to_date, transaction_type="1"):
        """
        Mengambil data broker summary / bandar detector EOD.
        from_date & to_date: format 'YYYY-MM-DD'
        transaction_type: '1' untuk default regular transaction
        """
        url = f"https://exodus.stockbit.com/marketdetectors/{stock_code}"
        params = {
            "transaction_type": transaction_type,
            "from": from_date,
            "to": to_date
        }
        return self._get(url, params)

    def get_prices(self, stock_code):
        """Mengambil daftar fraksi harga (price grid) yang valid untuk saham tertentu."""
        url = "https://exodus.stockbit.com/company-price-feed/prices"
        params = {
            "stock_code": stock_code
        }
        return self._get(url, params)

    def get_brokers(self, limit=150):
        """Mengambil daftar katalog broker terdaftar."""
        url = "https://exodus.stockbit.com/findata-view/marketdetectors/brokers"
        params = {
            "page": 1,
            "limit": limit,
            "group": "GROUP_UNSPECIFIED"
        }
        return self._get(url, params)

    def get_watchlists(self):
        """Mengambil daftar watchlist milik pengguna."""
        url = "https://exodus.stockbit.com/watchlist"
        params = {
            "category_types": [
                "CATEGORY_TYPE_ALL_WATCHLIST",
                "CATEGORY_TYPE_PORTFOLIO",
                "CATEGORY_TYPE_NORMAL"
            ]
        }
        return self._get(url, params)

    def get_watchlist_detail(self, watchlist_id, limit=50):
        """Mengambil detail isi dari suatu watchlist berdasarkan ID."""
        url = f"https://exodus.stockbit.com/watchlist/{watchlist_id}"
        params = {
            "page": 1,
            "limit": limit
        }
        return self._get(url, params)

    def get_historical_summary(self, symbol, period="HS_PERIOD_DAILY", limit=30, page=1):
        """
        Mengambil ringkasan aktivitas broker harian historis (Broker Daily Activity / Foreign Flow).
        period: 'HS_PERIOD_DAILY', 'HS_PERIOD_WEEKLY', 'HS_PERIOD_MONTHLY'
        """
        url = f"https://exodus.stockbit.com/company-price-feed/historical/summary/{symbol}"
        params = {
            "period": period,
            "limit": limit,
            "page": page
        }
        return self._get(url, params)

    def get_orderbook(self, symbol):
        """Mengambil data orderbook bid/offer depth snapshot real-time."""
        url = f"https://exodus.stockbit.com/company-price-feed/v2/orderbook/companies/{symbol}"
        return self._get(url)

    def get_foreign_domestic_chart(self, symbol, period="PERIOD_RANGE_1D"):
        """Mengambil detail chart partisipasi asing vs lokal (volume, value, frequency)."""
        url = f"https://exodus.stockbit.com/findata-view/foreign-domestic/v1/chart-data/{symbol}"
        params = {
            "market_type": "MARKET_TYPE_REGULAR",
            "period": period
        }
        return self._get(url, params)

    def get_intraday_candles(self, symbol, from_unix=None, to_unix=None, limit=0):
        """
        Mengambil data chart intraday 1-menit (OHLCV + volume + frequency + foreign flow).
        from_unix & to_unix: UNIX timestamps
        """
        url = f"https://exodus.stockbit.com/chartbit/{symbol}/price/intraday"
        params = {
            "limit": limit
        }
        if from_unix:
            params["from"] = from_unix
        if to_unix:
            params["to"] = to_unix
        return self._get(url, params)

    def get_daily_candles(self, symbol, from_date=None, to_date=None, limit=0):
        """
        Mengambil data chart harian EOD (OHLCV + volume + frequency + foreign flow).
        from_date & to_date: format string 'YYYY-MM-DD'
        """
        url = f"https://exodus.stockbit.com/chartbit/{symbol}/price/daily"
        params = {
            "limit": limit
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._get(url, params)

    def get_company_profile(self, symbol):
        """Mengambil profil lengkap emiten (background, history, shareholders, key executives, UBO)."""
        url = f"https://exodus.stockbit.com/emitten/{symbol}/profile"
        return self._get(url)

    def get_company_info(self, symbol):
        """Mengambil data info sektoral dasar emiten (name, sector, sub-sector, followers, price)."""
        url = f"https://exodus.stockbit.com/emitten/{symbol}/info"
        return self._get(url)

    def get_insider_composition(self, symbol, period_start=None, period_end=None):
        """Mengambil komposisi kepemilikan saham sektoral (Bank, Ritel, Korporasi, dll.)."""
        url = f"https://exodus.stockbit.com/insider/shareholding/composition/companies/{symbol}"
        params = {}
        if period_start:
            params["period_start"] = period_start
        if period_end:
            params["period_end"] = period_end
        return self._get(url, params)

    def get_insider_majorholders(self, symbol, limit=20, page=1):
        """Mengambil histori transaksi jual/beli oleh pemegang saham pengendali atau insider."""
        url = "https://exodus.stockbit.com/insider/company/majorholder"
        params = {
            "symbols": symbol,
            "limit": limit,
            "page": page,
            "action_type": "ACTION_TYPE_UNSPECIFIED",
            "source_type": "SOURCE_TYPE_UNSPECIFIED",
            "period_type": "PERIOD_TYPE_UNSPECIFIED"
        }
        return self._get(url, params)

    def get_keystats(self, symbol, year_limit=10):
        """Mengambil histori rasio keuangan tahunan/kuartalan dan detail dividen."""
        url = f"https://exodus.stockbit.com/keystats/ratio/v1/{symbol}"
        params = {
            "year_limit": year_limit
        }
        return self._get(url, params)

    def get_analyst_consensus(self, symbol):
        """Mengambil rating analis consensus (Buy/Hold/Sell) dan target price."""
        url = f"https://exodus.stockbit.com/analyst-ratings/{symbol}/consensus"
        return self._get(url)

    def get_analyst_ratings(self, symbol):
        """Mengambil ringkasan rekomendasi analis (Buy/Hold/Sell, target price, dll.)."""
        url = f"https://exodus.stockbit.com/analyst-ratings/{symbol}"
        return self._get(url)
