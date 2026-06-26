from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TradeTick:
    """Representasi satu transaksi running trade."""
    trade_id: str
    trade_number: int
    timestamp: float
    time_str: str
    symbol: str
    price: int
    lot: float
    value: int
    action: str           # 'B' = Buy, 'S' = Sell
    buyer_broker: str
    seller_broker: str
    buyer_type: str
    seller_type: str
    group_order_number: str
    buy_order_number: str
    sell_order_number: str
    buyer_retail_density: Optional[str] = None
    buyer_typical_style: Optional[str] = None
    buyer_tier: Optional[int] = None
    seller_retail_density: Optional[str] = None
    seller_typical_style: Optional[str] = None
    seller_tier: Optional[int] = None


@dataclass
class VolumeCategory:
    """Rincian volume berdasarkan kategori pelaku."""
    semut_buy_lot: float = 0.0
    semut_sell_lot: float = 0.0
    kakap_buy_lot: float = 0.0
    kakap_sell_lot: float = 0.0
    hiu_buy_lot: float = 0.0
    hiu_sell_lot: float = 0.0
    paus_buy_lot: float = 0.0
    paus_sell_lot: float = 0.0
    semut_count: int = 0
    kakap_count: int = 0
    hiu_count: int = 0
    paus_count: int = 0


@dataclass
class SLotGroup:
    """Detail satu grup S-Lot (split order dari pelaku besar)."""
    group_order_number: str
    symbol: str
    action: str
    total_lot: float
    total_value: int
    tick_count: int
    avg_price: float
    first_time: str
    last_time: str
    broker: str


@dataclass
class HAKAHAKIResult:
    """Hasil analisis HAKA/HAKI untuk satu saham."""
    symbol: str
    analysis_window: int       # Jumlah transaksi yang dianalisis
    
    # ---- HAKA (Akumulasi - Buy Aggressive) ----
    haka_lot: float = 0.0
    haka_value: int = 0
    haka_count: int = 0
    
    # ---- HAKI (Distribusi - Sell Aggressive) ----
    haki_lot: float = 0.0
    haki_value: int = 0
    haki_count: int = 0
    
    # ---- Rasio ----
    haka_ratio: float = 0.0    # HAKA / (HAKA + HAKI)
    
    # ---- Sinyal ----
    signal: str = "NEUTRAL"    # BUY / SELL / NEUTRAL / HOLD
    signal_strength: str = ""  # STRONG / MODERATE / WEAK
    
    # ---- Kategori Volume ----
    volume_category: VolumeCategory = field(default_factory=VolumeCategory)
    
    # ---- S-Lot ----
    s_lot_groups: List[SLotGroup] = field(default_factory=list)
    total_s_lot: float = 0.0
    
    # ---- Metadata Harga ----
    last_price: int = 0
    price_range_high: int = 0
    price_range_low: int = 0

    # ---- Profiling Konglomerat & MSCI Index ----
    conglomerate_name: Optional[str] = None
    is_msci_stock: bool = False
    msci_index_type: Optional[str] = None
    msci_status: Optional[str] = None
    insider_activity_detected: bool = False
    insider_activity_details: List[str] = field(default_factory=list)
    msci_flow_detected: bool = False
    msci_flow_details: List[str] = field(default_factory=list)
    smart_money_score: float = 0.0  # Indeks bobot smart money (positif = akumulasi institusi/low-retail)

    # ---- Swing Execution Plan (40 Hari Holding) ----
    bandar_avg_price: Optional[float] = None
    cheap_entry_high: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    swing_invalidation_flag: bool = False
