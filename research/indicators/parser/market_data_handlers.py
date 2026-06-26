from urllib.parse import parse_qs
from .utils import clean_int, clean_float

def parse_running_trade(db, path, parsed_url, payload, timestamp):
    """Memproses data running trade harian (market board RG)."""
    from datetime import datetime
    
    data = payload.get("data", {})
    running_trades = data.get("running_trade", [])
    
    # Ambil date query parameter dari URL
    qs = parse_qs(parsed_url.query)
    date_strs = qs.get("date")
    date_str = date_strs[0] if date_strs else None
    
    trades_list = []
    for rt in running_trades:
        # Hanya ambil Papan Regular (RG) untuk Tape Reading
        if rt.get("market_board") != "RG":
            continue
            
        price = clean_int(rt.get("price"))
        lot = clean_float(rt.get("lot"))
        
        # Nilai transaksi nominal
        val_raw = rt.get("value", {}).get("raw")
        if val_raw is None:
            val_raw = int(price * lot * 100)
        else:
            val_raw = int(val_raw)
            
        # Hitung timestamp eksak dengan menggabungkan query date + time transaksi
        time_str = rt.get("time")
        trade_ts = timestamp  # fallback
        if date_str and time_str:
            try:
                t_str = time_str.split(".")[0] if "." in time_str else time_str
                dt = datetime.strptime(f"{date_str} {t_str[:8]}", "%Y-%m-%d %H:%M:%S")
                trade_ts = dt.timestamp()
            except Exception:
                pass
            
        trades_list.append({
            "trade_id": rt.get("id"),
            "trade_number": clean_int(rt.get("trade_number")),
            "timestamp": trade_ts,
            "time_str": time_str,
            "symbol": rt.get("code"),
            "price": price,
            "lot": lot,
            "value": val_raw,
            "action": rt.get("action"),
            "market_board": rt.get("market_board"),
            "buyer_broker": rt.get("buyer"),
            "seller_broker": rt.get("seller"),
            "buyer_type": rt.get("buyer_type"),
            "seller_type": rt.get("seller_type"),
            "buy_order_number": rt.get("buy_order_number"),
            "sell_order_number": rt.get("sell_order_number"),
            "group_order_number": rt.get("group_order_number"),
            "is_broker_exists": 1 if rt.get("is_broker_exists") else 0,
            "change_percent": rt.get("change")
        })
    return trades_list


def parse_trade_book(db, path, parsed_url, payload, timestamp):
    """Memproses data trade book (antrean per harga)."""
    qs = parse_qs(parsed_url.query)
    symbol = qs.get("symbol", ["UNKNOWN"])[0]
    
    inner_data = payload.get("data", {})
    book_list = inner_data.get("book", [])
    
    book_items = []
    for item in book_list:
        price = clean_int(item.get("price"))
        buy_lot = clean_int(item.get("buy", {}).get("lot"))
        buy_freq = clean_int(item.get("buy", {}).get("frequency"))
        sell_lot = clean_int(item.get("sell", {}).get("lot"))
        sell_freq = clean_int(item.get("sell", {}).get("frequency"))
        total_lot = clean_int(item.get("total", {}).get("lot"))
        
        book_items.append({
            "price": price,
            "buy_lot": buy_lot,
            "buy_freq": buy_freq,
            "sell_lot": sell_lot,
            "sell_freq": sell_freq,
            "total_lot": total_lot
        })
    db.insert_trade_book(symbol, timestamp, book_items)


def parse_price_grid(db, path, parsed_url, payload, timestamp):
    """Memproses valid price grid fractions."""
    qs = parse_qs(parsed_url.query)
    symbol = qs.get("stock_code", ["UNKNOWN"])[0]
    
    inner_data = payload.get("data", {})
    prices = inner_data.get("prices", [])
    db.insert_price_grid(symbol, prices)


def parse_chart_ohlcv(db, path, parsed_url, payload, timestamp):
    """Memproses data historical chart basic OHLCV."""
    symbol = path.split("/")[-1]
    
    inner_data = payload.get("data", {})
    chart_list = inner_data.get("price_chart_data", [])
    
    ohlcv_list = []
    for c in chart_list:
        date_val = c.get("date")
        time_val = c.get("time", "EOD")
        
        open_p = clean_int(c.get("open", {}).get("raw"))
        high_p = clean_int(c.get("high", {}).get("raw"))
        low_p = clean_int(c.get("low", {}).get("raw"))
        close_p = clean_int(c.get("value", {}).get("raw"))
        
        ohlcv_list.append({
            "symbol": symbol,
            "date": date_val,
            "time": time_val,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p
        })
    
    if ohlcv_list:
        db.insert_ohlcv_data(ohlcv_list)


def parse_chartbit_candles(db, path, parsed_url, payload, timestamp):
    """Memproses data Chartbit (1-menit intraday & daily EOD)."""
    path_parts = path.strip("/").split("/")
    if len(path_parts) >= 4:
        symbol = path_parts[1]
        timeframe = path_parts[3]
        
        inner_data = payload.get("data", {})
        chart_list = inner_data.get("chartbit", [])
        
        ohlcv_list = []
        for c in chart_list:
            open_p = clean_int(c.get("open"))
            high_p = clean_int(c.get("high"))
            low_p = clean_int(c.get("low"))
            close_p = clean_int(c.get("close"))
            volume = clean_int(c.get("volume"))
            value = clean_float(c.get("value"))
            frequency = clean_int(c.get("frequency"))
            
            foreign_buy = clean_int(c.get("foreign_buy") if c.get("foreign_buy") is not None else c.get("foreignbuy"))
            foreign_sell = clean_int(c.get("foreign_sell") if c.get("foreign_sell") is not None else c.get("foreignsell"))
            
            unix_ts = clean_int(c.get("unix_timestamp") if c.get("unix_timestamp") is not None else c.get("unixdate"))
            foreign_flow = clean_int(c.get("foreignflow")) if c.get("foreignflow") is not None else None
            market_cap = clean_int(c.get("soxclose")) if c.get("soxclose") is not None else None
            dividend = clean_float(c.get("dividend")) if c.get("dividend") is not None else None
            shares_out = clean_int(c.get("shareoutstanding")) if c.get("shareoutstanding") is not None else None
            freq_anal = clean_float(c.get("freq_analyzer")) if c.get("freq_analyzer") is not None else None
            
            if timeframe == "intraday":
                dt_str = c.get("datetime")
                if dt_str and " " in dt_str:
                    date_val, full_time = dt_str.split(" ", 1)
                    time_val = full_time[:5]
                else:
                    continue
            else:
                date_val = c.get("date")
                time_val = "EOD"
                
            if not date_val:
                continue
                
            ohlcv_list.append({
                "symbol": symbol,
                "date": date_val,
                "time": time_val,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
                "value": value,
                "frequency": frequency,
                "foreign_buy": foreign_buy,
                "foreign_sell": foreign_sell,
                "unix_timestamp": unix_ts,
                "foreign_flow": foreign_flow,
                "market_cap": market_cap,
                "dividend": dividend,
                "shares_outstanding": shares_out,
                "freq_analyzer": freq_anal
            })
        
        if ohlcv_list:
            db.insert_ohlcv_data(ohlcv_list)


def parse_orderbook_snapshot(db, path, parsed_url, payload, timestamp):
    """Memproses orderbook snapshot (kedalaman bid/offer)."""
    symbol = path.split("/")[-1]
    inner_data = payload.get("data", {})
    
    total_bo = inner_data.get("total_bid_offer", {})
    bid_total = total_bo.get("bid", {})
    offer_total = total_bo.get("offer", {})
    
    snap = {
        "close_price": clean_int(inner_data.get("close")),
        "total_bid_lot": clean_int(bid_total.get("lot")),
        "total_bid_freq": clean_int(bid_total.get("freq")),
        "total_offer_lot": clean_int(offer_total.get("lot")),
        "total_offer_freq": clean_int(offer_total.get("freq")),
        "ara_price": clean_int(inner_data.get("ara", {}).get("value")),
        "arb_price": clean_int(inner_data.get("arb", {}).get("value")),
        "foreign_buy_val": clean_float(inner_data.get("fbuy")),
        "foreign_sell_val": clean_float(inner_data.get("fsell")),
        "foreign_net_val": clean_float(inner_data.get("fnet")),
        "domestic_pct": clean_float(inner_data.get("domestic")),
        "foreign_pct": clean_float(inner_data.get("foreign")),
        "bids": [],
        "offers": []
    }
    
    for b in inner_data.get("bid", []):
        snap["bids"].append({
            "price": clean_int(b.get("price")),
            "volume": clean_int(b.get("volume")),
            "que_num": clean_int(b.get("que_num"))
        })
        
    for o in inner_data.get("offer", []):
        snap["offers"].append({
            "price": clean_int(o.get("price")),
            "volume": clean_int(o.get("volume")),
            "que_num": clean_int(o.get("que_num"))
        })
        
    db.insert_orderbook_snapshot(symbol, timestamp, snap)


def parse_order_queue(db, path, parsed_url, payload, timestamp):
    """Memproses antrean order (Order Queue)."""
    inner_data = payload.get("data", {})
    orders = inner_data.get("orders", [])
    orders_list = []
    for o in orders:
        orders_list.append({
            "id": o.get("id"),
            "symbol": o.get("stock_code"),
            "queue_number": clean_int(o.get("queue_number")),
            "time_str": o.get("time"),
            "action_type": o.get("action_type"),
            "price": clean_int(o.get("price")),
            "status": o.get("status"),
            "open_lot": clean_int(o.get("open")),
            "total_lot": clean_int(o.get("lot")),
            "broker_code": o.get("broker_code"),
            "broker_group": o.get("broker_group"),
            "order_number": o.get("order_number")
        })
    if orders_list:
        db.insert_order_queues(orders_list)
