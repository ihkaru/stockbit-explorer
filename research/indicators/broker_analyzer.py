import json
from tabulate import tabulate

def estimate_broker_avg_price(broker_history):
    """
    Menghitung estimasi harga rata-rata (VWAP) dari broker akumulator.
    Hanya menghitung hari-hari di mana broker tersebut bertindak sebagai Net Buyer.
    
    broker_history: list of dict, contoh:
      [
        {"date": "2026-06-19", "net_lot": 5000, "vwap": 4020},
        {"date": "2026-06-22", "net_lot": 8000, "vwap": 4050},
        {"date": "2026-06-23", "net_lot": -2000, "vwap": 4070} # Hari net sell (diabaikan untuk akumulasi)
      ]
    """
    total_lot = 0
    total_value = 0

    for day in broker_history:
        net_lot = day.get('net_lot', 0)
        vwap = day.get('vwap', 0)
        
        # Sesuai strategi: Hanya hitung hari net buy
        if net_lot > 0:
            total_lot += net_lot
            total_value += net_lot * vwap

    if total_lot == 0:
        return 0, 0

    avg_price = total_value / total_lot
    return avg_price, total_lot

def analyze_broker_summary(stock_symbol, history_data):
    """
    Menganalisis histori transaksi broker untuk mendeteksi akumulasi, 
    menghitung harga rata-rata pelaku besar, serta mendeteksi tanda distribusi.
    """
    print("=" * 80)
    print(f" ANALISIS BANDARMOLOGI EOD UNTUK SAHAM: {stock_symbol}")
    print("=" * 80)
    
    # 1. Klasifikasi transaksi harian per broker
    # Kita petakan riwayat aktivitas masing-masing broker
    brokers_profile = {}
    
    for date, daily_summary in history_data.items():
        for broker, data in daily_summary.items():
            if broker not in brokers_profile:
                brokers_profile[broker] = []
            brokers_profile[broker].append({
                "date": date,
                "net_lot": data["net_lot"],
                "vwap": data["vwap"]
            })
            
    # 2. Hitung Profil Akumulasi & Rata-rata Harga untuk setiap broker
    analysis_report = []
    
    for broker, history in brokers_profile.items():
        # Hitung estimated average price
        avg_price, accum_lot = estimate_broker_avg_price(history)
        
        # Hitung net akumulasi kumulatif keseluruhan hari
        cumulative_net_lot = sum(day["net_lot"] for day in history)
        
        # Deteksi status distribusi (apakah hari terakhir net sell setelah akumulasi?)
        status = "NETRAL"
        warning = ""
        
        # Cek jika ada akumulasi di awal, tapi hari terakhir malah jualan
        history_sorted = sorted(history, key=lambda x: x["date"])
        last_day = history_sorted[-1] if history_sorted else None
        
        if cumulative_net_lot > 10000:
            status = "AKUMULASI KUAT"
        elif cumulative_net_lot < -10000:
            status = "DISTRIBUSI KUAT"
            
        if last_day and last_day["net_lot"] < 0 and accum_lot > 15000:
            warning = "[PERINGATAN] Mantan Akumulator mulai Jualan (Mulai Distribusi!)"
            
        analysis_report.append({
            "Broker": broker,
            "Net Kumulatif (Lot)": f"{cumulative_net_lot:+,}",
            "Lot Akumulasi": f"{accum_lot:,}",
            "Est. Avg Price": f"Rp {round(avg_price):,}" if avg_price > 0 else "-",
            "Status": status,
            "Warning/Keterangan": warning
        })
        
    # Urutkan berdasarkan Net Kumulatif terbesar
    analysis_report.sort(key=lambda x: int(x["Net Kumulatif (Lot)"].replace(",", "")), reverse=True)
    
    # Tampilkan Tabel Laporan
    headers = ["Broker", "Net Kumulatif (Lot)", "Lot Akumulasi", "Est. Avg Price", "Status", "Warning/Keterangan"]
    table_data = [[r[h] for h in headers] for r in analysis_report]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("\n[INFO] Rekomendasi Taktis Remora Trader:")
    
    # Rekomendasi berdasarkan Broker Kunci (BK)
    top_buyer = analysis_report[0]
    top_seller = analysis_report[-1]
    
    print(f"- Top Buyer Dominan: {top_buyer['Broker']} dengan Net Accum {top_buyer['Net Kumulatif (Lot)']} Lot pada {top_buyer['Est. Avg Price']}.")
    print(f"- Top Seller Dominan: {top_seller['Broker']} dengan Net Distribution {top_seller['Net Kumulatif (Lot)']} Lot.")
    
    if "[PERINGATAN]" in "".join(r["Warning/Keterangan"] for r in analysis_report):
        print("- Keputusan: Siapkan EXIT plan segera. Terdeteksi aksi distribusi tersembunyi dari broker kunci.")
    else:
        print(f"- Keputusan: Jika harga saham saat ini berada di kisaran {top_buyer['Est. Avg Price']} s.d +3% di atasnya, area ini adalah BUY ZONE aman karena disokong pertahanan {top_buyer['Broker']}.")
    print("=" * 80 + "\n")

# ---- MOCK DATA HISTORIS BROKER SUMMARY UNTUK PENGUJIAN ----
# Simulasikan data EOD selama 4 hari untuk saham 'TLKM'
mock_history_tlkm = {
    "2026-06-22": {
        "BK": {"net_lot": 15000, "vwap": 4010}, # BK akumulasi besar
        "YP": {"net_lot": -5000, "vwap": 4020},  # retail jualan
        "CC": {"net_lot": -10000, "vwap": 4015}
    },
    "2026-06-23": {
        "BK": {"net_lot": 20000, "vwap": 4030}, # BK tambah barang
        "YP": {"net_lot": -12000, "vwap": 4040},
        "CC": {"net_lot": -8000, "vwap": 4035}
    },
    "2026-06-24": {
        "BK": {"net_lot": 10000, "vwap": 4050}, # BK masih beli tapi melambat
        "YP": {"net_lot": -4000, "vwap": 4060},
        "CC": {"net_lot": -6000, "vwap": 4050}
    },
    "2026-06-25": {
        "BK": {"net_lot": -5000, "vwap": 4060}, # ⚠️ WARNING: BK mulai jualan tipis (distribusi tersembunyi)
        "YP": {"net_lot": 8000, "vwap": 4070},  # retail FOMO masuk
        "CC": {"net_lot": -3000, "vwap": 4065}
    }
}

if __name__ == "__main__":
    # Jalankan simulasi analisis
    analyze_broker_summary("TLKM", mock_history_tlkm)
