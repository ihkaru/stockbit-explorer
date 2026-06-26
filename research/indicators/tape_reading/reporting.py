from .models import HAKAHAKIResult

def print_report(result: HAKAHAKIResult, risk_reward_ratio: float = 2.5) -> None:
    """Mencetak laporan analisis Tape Reading ke konsol secara terformat."""
    vc = result.volume_category
    
    print("\n" + "=" * 70)
    print(f"  TAPE READING ANALYSIS REPORT: {result.symbol}")
    print("=" * 70)
    print(f"  Analisis Window  : {result.analysis_window} transaksi")
    print(f"  Harga Terakhir   : Rp {result.last_price:,}")
    print(f"  Range Harga      : {result.price_range_low:,} - {result.price_range_high:,}")
    
    # Cetak info Conglomerate & MSCI jika ada
    if result.conglomerate_name:
        print(f"  Grup Konglo      : {result.conglomerate_name}")
    if result.is_msci_stock:
        print(f"  Status MSCI      : {result.msci_index_type} ({result.msci_status})")
        
    print("\n  -- HAKA/HAKI RATIO --------------------------------------------------")
    haka_bar_len = int(result.haka_ratio * 40)
    haki_bar_len = 40 - haka_bar_len
    haka_bar = "#" * haka_bar_len + "." * haki_bar_len
    print(f"  HAKA (Akumulasi) : {result.haka_lot:>10.1f} lot | {result.haka_count:>5} tx | Rp {result.haka_value:>20,.0f}")
    print(f"  HAKI (Distribusi): {result.haki_lot:>10.1f} lot | {result.haki_count:>5} tx | Rp {result.haki_value:>20,.0f}")
    print(f"  Rasio HAKA       : {result.haka_ratio:.1%}  [{haka_bar}]")
    
    print(f"\n  -- SINYAL ------------------------------------------------------------")
    signal_icon = {"BUY": "[BUY]", "SELL": "[SELL]", "NEUTRAL": "[NTRL]", "HOLD": "[HOLD]"}.get(result.signal, "[?]")
    print(f"  {signal_icon} {result.signal} ({result.signal_strength})")
    print(f"  Smart Money Score: {result.smart_money_score:+,.1f} lot (Positif = Akumulasi Institusi)")
    
    if result.insider_activity_detected:
        print(f"\n  [WARNING] DETEKSI AKTIVITAS INSIDER GRUP KONGLO (KANAN-KIRI):")
        for detail in result.insider_activity_details[:5]:
            print(f"  • {detail}")
        if len(result.insider_activity_details) > 5:
            print(f"  • Dan {len(result.insider_activity_details) - 5} transaksi grup lainnya...")
            
    if result.msci_flow_detected:
        print(f"\n  [INFO] DETEKSI REBALANCING INDEX MSCI FLOW (CLOSING SESSION):")
        for detail in result.msci_flow_details[:5]:
            print(f"  • {detail}")
        if len(result.msci_flow_details) > 5:
            print(f"  • Dan {len(result.msci_flow_details) - 5} transaksi MSCI lainnya...")
    
    # Cetak Swing Execution Plan jika terhitung
    if result.bandar_avg_price:
        print(f"\n  -- REMORA SWING EXECUTION PLAN (40-Day Hold) -------------------------")
        print(f"  Modal Rata-rata Bandar : Rp {result.bandar_avg_price:,.2f} (EOD 10-Hari)")
        
        # Tentukan apakah harga saat ini masih dalam Cheap Entry Zone
        if result.last_price > result.cheap_entry_high:
            zone_status = "[JANGAN ENTRY / KEJAUHAN (OVERVALUED)]"
        elif result.last_price < result.stop_loss:
            zone_status = "[THESIS BATAL / DI BAWAH STOP LOSS (INVALIDATED)]"
        else:
            zone_status = "[ZONA LAYAK ENTRY (CHEAP ACCUMULATION ZONE)]"
            
        print(f"  Zona Layak Beli (Cheap): Rp {result.bandar_avg_price:,.0f} - Rp {result.cheap_entry_high:,.0f} {zone_status}")
        print(f"  Stop Loss (Batas Rugi) : Rp {result.stop_loss:,.0f} (4% di bawah modal bandar)")
        print(f"  Take Profit (Target)   : Rp {result.take_profit:,.0f} (Target R:R 1:{risk_reward_ratio})")
    
    print(f"\n  -- KATEGORISASI VOLUME PELAKU ----------------------------------------")
    print(f"  {'Kategori':<10} {'Lot Beli':>12} {'Lot Jual':>12} {'Jml TX':>8}")
    print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*8}")
    print(f"  {'Semut':<10} {vc.semut_buy_lot:>12.1f} {vc.semut_sell_lot:>12.1f} {vc.semut_count:>8}")
    print(f"  {'Kakap':<10} {vc.kakap_buy_lot:>12.1f} {vc.kakap_sell_lot:>12.1f} {vc.kakap_count:>8}")
    print(f"  {'Hiu':<10} {vc.hiu_buy_lot:>12.1f} {vc.hiu_sell_lot:>12.1f} {vc.hiu_count:>8}")
    print(f"  {'Paus (SM)':<10} {vc.paus_buy_lot:>12.1f} {vc.paus_sell_lot:>12.1f} {vc.paus_count:>8}")
    
    if result.s_lot_groups:
        print(f"\n  -- DETEKSI S-LOT (Split Order Bandar) --------------------------------")
        print(f"  Total S-Lot Terdeteksi: {len(result.s_lot_groups)} grup | {result.total_s_lot:.1f} lot total")
        for i, sg in enumerate(result.s_lot_groups[:5]):  # Tampilkan 5 terbesar
            action_str = "BELI" if sg.action == "B" else "JUAL"
            print(f"  [{i+1}] {action_str} {sg.total_lot:.1f} lot ({sg.tick_count} pecahan) "
                  f"@ avg Rp {sg.avg_price:,} | {sg.first_time} - {sg.last_time} | Broker: {sg.broker}")
    else:
        print(f"\n  -- DETEKSI S-LOT -----------------------------------------------------")
        print(f"  Tidak ada S-Lot signifikan terdeteksi.")
    
    print("=" * 70)
