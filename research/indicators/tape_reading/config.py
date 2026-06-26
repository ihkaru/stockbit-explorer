# ---------------------------------------------------------------------------
# Konfigurasi Ambang Batas (Threshold Configuration)
# ---------------------------------------------------------------------------

# Batas volume untuk kategorisasi pelaku pasar (dalam Lot)
VOLUME_THRESHOLD = {
    "semut": (0, 4),       # Retail kecil
    "kakap": (5, 49),      # Trader menengah
    "hiu":   (50, 499),    # Trader besar / fund kecil
    "paus":  (500, None),  # Smart Money / Bandar / Fund besar
}

# Ambang batas sinyal HAKA/HAKI
SIGNAL_THRESHOLD = {
    "strong_buy":  0.70,   # HAKA >= 70% -> Sinyal Beli Kuat
    "buy":         0.60,   # HAKA >= 60% -> Sinyal Beli
    "neutral":     0.40,   # 40% <= HAKA < 60% -> Neutral
    "sell":        0.30,   # HAKA <= 40% -> Sinyal Jual
    "strong_sell": 0.20,   # HAKA <= 20% -> Sinyal Jual Kuat
}

# Minimum jumlah transaksi sebelum sinyal valid
MIN_TRADE_COUNT = 10
