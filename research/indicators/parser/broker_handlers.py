from .utils import clean_int, clean_float, parse_date_str

def parse_brokers_catalog(db, path, parsed_url, payload, timestamp):
    """Memproses katalog data broker terdaftar."""
    inner_data = payload.get("data", [])
    brokers_list = []
    for b in inner_data:
        brokers_list.append({
            "code": b.get("code"),
            "name": b.get("name"),
            "group_type": b.get("group"),
            "color": b.get("color"),
            "membership_type": b.get("membership_type")
        })
    if brokers_list:
        db.insert_brokers(brokers_list)


def parse_broker_summary(db, path, parsed_url, payload, timestamp):
    """Memproses broker summaries (Buyers & Sellers) untuk batch insert."""
    inner_data = payload.get("data", {})
    broker_summary = inner_data.get("broker_summary", {})
    symbol = broker_summary.get("symbol", path.split("/")[-1])
    
    raw_date_from = inner_data.get("from")
    date_str = parse_date_str(raw_date_from) if raw_date_from else "Unknown"
    
    summaries = []
    
    # Buyers
    for b in broker_summary.get("brokers_buy", []):
        net_lot = clean_int(b.get("blot"))
        total_vol_lot = clean_int(b.get("blotv"))
        avg_price = clean_float(b.get("netbs_buy_avg_price"))
        net_val = clean_float(b.get("bval"))
        total_vol_val = clean_float(b.get("bvalv"))
        freq = clean_int(b.get("freq"))
        broker_code = b.get("netbs_broker_code") or b.get("net_broker_code")
        
        item_date = parse_date_str(b.get("netbs_date")) if b.get("netbs_date") else date_str
        item_symbol = b.get("netbs_stock_code") or symbol
        
        summaries.append({
            "date": item_date,
            "symbol": item_symbol,
            "broker_code": broker_code,
            "type": b.get("type"),
            "net_lot": net_lot,
            "total_volume_lot": total_vol_lot,
            "avg_price": avg_price,
            "net_value": net_val,
            "total_volume_value": total_vol_val,
            "freq": freq,
            "activity": "AKUMULASI"
        })
        
    # Sellers
    for s in broker_summary.get("brokers_sell", []):
        net_lot = clean_int(s.get("slot"))
        total_vol_lot = clean_int(s.get("slotv"))
        avg_price = clean_float(s.get("netbs_sell_avg_price"))
        net_val = clean_float(s.get("sval"))
        total_vol_val = clean_float(s.get("svalv"))
        freq = clean_int(s.get("freq"))
        broker_code = s.get("netbs_broker_code") or s.get("net_broker_code")
        
        item_date = parse_date_str(s.get("netbs_date")) if s.get("netbs_date") else date_str
        item_symbol = s.get("netbs_stock_code") or symbol
        
        summaries.append({
            "date": item_date,
            "symbol": item_symbol,
            "broker_code": broker_code,
            "type": s.get("type"),
            "net_lot": net_lot,
            "total_volume_lot": total_vol_lot,
            "avg_price": avg_price,
            "net_value": net_val,
            "total_volume_value": total_vol_val,
            "freq": freq,
            "activity": "DISTRIBUSI"
        })
        
    return summaries


def parse_broker_daily_activity(db, path, parsed_url, payload, timestamp):
    """Memproses aktivitas harian broker / data historis summary."""
    symbol = path.split("/")[-1]
    inner_data = payload.get("data", {})
    summary_list = inner_data.get("result", [])
    activity_list = []
    for s in summary_list:
        activity_list.append({
            "date": s.get("date"),
            "close": clean_int(s.get("close")),
            "change_val": clean_int(s.get("change")),
            "value": clean_int(s.get("value")),
            "volume": clean_int(s.get("volume")),
            "frequency": clean_int(s.get("frequency")),
            "foreign_buy": clean_int(s.get("foreign_buy")),
            "foreign_sell": clean_int(s.get("foreign_sell")),
            "net_foreign": clean_int(s.get("net_foreign")),
            "open": clean_int(s.get("open")),
            "high": clean_int(s.get("high")),
            "low": clean_int(s.get("low")),
            "average": clean_int(s.get("average")),
            "change_percentage": clean_float(s.get("change_percentage"))
        })
    if activity_list and symbol:
        db.insert_broker_daily_activity(symbol, activity_list)


def parse_foreign_domestic_flow(db, path, parsed_url, payload, timestamp):
    """Memproses chart-data aliran dana asing vs domestik."""
    symbol = path.split("/")[-1]
    inner_data = payload.get("data", {})
    summary = inner_data.get("summary", {})
    volume_summary = summary.get("volume", {})
    
    value_data = inner_data.get("value", {})
    volume_data = inner_data.get("volume", {})
    freq_data = inner_data.get("frequency", {})
    
    date_str = inner_data.get("from")
    
    # Ekstrak Tunai/Nego dan All Market (nominal Rupiah) dari all_markets_summary list
    all_mkts = summary.get("all_markets_summary", [])
    net_foreign_all_market = None
    net_foreign_nego = None
    
    for item in all_mkts:
        label = item.get("label", "")
        raw_val = clean_int(item.get("value", {}).get("raw"))
        if "All Market" in label:
            net_foreign_all_market = raw_val
        elif "Tunai & Nego" in label:
            net_foreign_nego = raw_val
            
    # Ekstrak Tunai/Nego dan All Market (volume lembar saham)
    net_foreign_volume_nego = clean_int(volume_summary.get("net_foreign_tunai_nego", {}).get("value", {}).get("raw"))
    net_foreign_volume_all_market = clean_int(volume_summary.get("net_foreign_all_market", {}).get("value", {}).get("raw"))
    
    if date_str:
        act_item = {
            "date": date_str,
            "close": None,
            "change_val": None,
            "value": clean_int(value_data.get("total", {}).get("raw")),
            "volume": clean_int(volume_data.get("total", {}).get("raw")),
            "frequency": clean_int(freq_data.get("total", {}).get("raw")),
            "foreign_buy": clean_int(summary.get("foreign_buy", {}).get("value", {}).get("raw")),
            "foreign_sell": clean_int(summary.get("foreign_sell", {}).get("value", {}).get("raw")),
            "net_foreign": clean_int(summary.get("net_foreign", {}).get("value", {}).get("raw")),
            "domestic_buy": clean_int(summary.get("domestic_buy", {}).get("value", {}).get("raw")),
            "domestic_sell": clean_int(summary.get("domestic_sell", {}).get("value", {}).get("raw")),
            "net_domestic": clean_int(summary.get("net_domestic", {}).get("value", {}).get("raw")),
            
            "foreign_buy_volume": clean_int(volume_summary.get("foreign_buy", {}).get("value", {}).get("raw")),
            "foreign_sell_volume": clean_int(volume_summary.get("foreign_sell", {}).get("value", {}).get("raw")),
            "net_foreign_volume": clean_int(volume_summary.get("net_foreign_reguler", {}).get("value", {}).get("raw")),
            "domestic_buy_volume": clean_int(volume_summary.get("domestic_buy", {}).get("value", {}).get("raw")),
            "domestic_sell_volume": clean_int(volume_summary.get("domestic_sell", {}).get("value", {}).get("raw")),
            "net_domestic_volume": clean_int(volume_summary.get("net_domestic", {}).get("value", {}).get("raw")),
            
            "foreign_buy_freq": clean_int(freq_data.get("foreign_buy", {}).get("value", {}).get("raw")),
            "foreign_sell_freq": clean_int(freq_data.get("foreign_sell", {}).get("value", {}).get("raw")),
            "domestic_buy_freq": clean_int(freq_data.get("domestic_buy", {}).get("value", {}).get("raw")),
            "domestic_sell_freq": clean_int(freq_data.get("domestic_sell", {}).get("value", {}).get("raw")),
            
            "foreign_value_pct": clean_float(value_data.get("foreign_total", {}).get("percentage", {}).get("raw")),
            "foreign_volume_pct": clean_float(volume_data.get("foreign_total", {}).get("percentage", {}).get("raw")),
            "foreign_freq_pct": clean_float(freq_data.get("foreign_total", {}).get("percentage", {}).get("raw")),
            "open": None,
            "high": None,
            "low": None,
            "average": None,
            "change_percentage": None,
            
            "net_foreign_nego": net_foreign_nego,
            "net_foreign_all_market": net_foreign_all_market,
            "net_foreign_volume_nego": net_foreign_volume_nego,
            "net_foreign_volume_all_market": net_foreign_volume_all_market
        }
        db.insert_broker_daily_activity(symbol, [act_item])
