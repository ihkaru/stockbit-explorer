from .data_access import TapeReadingRepository
from .signal_engine import SignalEngine
from .models import HAKAHAKIResult
from .reporting import print_report as run_print_report

class TapeReadingAnalyzer:
    """
    Engine analisis Tape Reading berbasis database PostgreSQL.
    Mengimplementasikan metodologi HAKA/HAKI dari Hengky Adinata.
    """
    
    def __init__(self, db_path: str = None):
        self.repo = TapeReadingRepository(db_path)
        self.engine = SignalEngine(
            conglomerate_stocks=self.repo.conglomerate_stocks,
            conglomerate_brokers=self.repo.conglomerate_brokers,
            msci_tracker=self.repo.msci_tracker,
            swing_pref=self.repo.swing_pref
        )

    # Delegasi properti untuk kompatibilitas backward jika ada yang mengakses secara langsung
    @property
    def db_path(self):
        return self.repo.db_path

    @property
    def conglomerate_stocks(self):
        return self.repo.conglomerate_stocks

    @property
    def conglomerate_brokers(self):
        return self.repo.conglomerate_brokers

    @property
    def msci_tracker(self):
        return self.repo.msci_tracker

    @property
    def swing_pref(self):
        return self.repo.swing_pref

    def get_connection(self):
        return self.repo.get_connection()

    def get_recent_trades(self, symbol, limit=500, min_trade_number=None):
        return self.repo.get_recent_trades(symbol, limit, min_trade_number)

    def get_multi_day_broker_summary(self, symbol, days_limit=10):
        return self.repo.get_multi_day_broker_summary(symbol, days_limit)

    def categorize_volume(self, lot):
        return self.engine.categorize_volume(lot)

    def detect_s_lots(self, trades):
        return self.engine.detect_s_lots(trades)

    def compute_haka_haki(self, symbol, trades):
        buyers = self.get_multi_day_broker_summary(symbol, days_limit=10)
        return self.engine.compute(symbol, trades, buyers)

    def analyze(self, symbol: str, limit: int = 300) -> HAKAHAKIResult:
        """
        Analisis lengkap untuk satu saham: ambil data, hitung HAKA/HAKI,
        deteksi S-Lot, dan hasilkan sinyal.
        """
        trades = self.get_recent_trades(symbol=symbol, limit=limit)
        return self.compute_haka_haki(symbol, trades)

    def print_report(self, result: HAKAHAKIResult) -> None:
        risk_reward = self.swing_pref.get("risk_reward_ratio", 2.5) if self.swing_pref else 2.5
        run_print_report(result, risk_reward)
