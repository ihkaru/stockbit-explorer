import os
import sys
import json
import time
from datetime import datetime

def generate_mock_trade(trade_id: int, price: int, lot: float, action: str, buyer: str, seller: str, gon: str = "0"):
    """Helper to generate a mock running trade item in Stockbit API payload format."""
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    trade_num = 2000000 + trade_id
    
    return {
        "id": str(1000000000 + trade_id),
        "time": time_str,
        "action": action.lower(), # "buy" or "sell"
        "code": "BBCA",
        "price": f"{price:,}",
        "change": "+1.69%",
        "lot": str(lot),
        "is_broker_exists": True,
        "buyer": f"{buyer} [D]",
        "seller": f"{seller} [D]",
        "trade_number": str(trade_num),
        "buyer_type": "BROKER_TYPE_LOCAL",
        "seller_type": "BROKER_TYPE_LOCAL",
        "market_board": "RG",
        "buy_order_number": f"888{trade_id}",
        "sell_order_number": f"999{trade_id}",
        "group_order_number": gon,
        "value": {
            "raw": int(price * lot * 100),
            "formatted": f"{int(price * lot * 100) / 1000000:.1f}M"
        }
    }

def main():
    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)
    
    live_file = os.path.join(raw_dir, "live_test_stream.jsonl")
    print(f"[*] Simulating real-time WebSocket stream into: {live_file}")
    
    # 5 test ticks with HAKA (buy) of varying sizes (Semut, Paus/Smart Money, and S-Lot)
    test_ticks = [
        # 1. Semut Buy
        {"price": 6025, "lot": 2.0, "action": "buy", "buyer": "YP", "seller": "CC", "gon": "0"},
        # 2. Hiu Buy
        {"price": 6025, "lot": 75.0, "action": "buy", "buyer": "DR", "seller": "YP", "gon": "0"},
        # 3. Paus Buy (Smart Money)
        {"price": 6025, "lot": 600.0, "action": "buy", "buyer": "CP", "seller": "PD", "gon": "111222"},
        # 4. S-Lot Buy Group (Pecahan 1/3)
        {"price": 6025, "lot": 150.0, "action": "buy", "buyer": "CP", "seller": "PD", "gon": "111222"},
        # 5. S-Lot Buy Group (Pecahan 2/3)
        {"price": 6025, "lot": 200.0, "action": "buy", "buyer": "CP", "seller": "PD", "gon": "111222"},
    ]
    
    for i, tick_data in enumerate(test_ticks):
        trade_item = generate_mock_trade(
            trade_id=i + 5000,
            price=tick_data["price"],
            lot=tick_data["lot"],
            action=tick_data["action"],
            buyer=tick_data["buyer"],
            seller=tick_data["seller"],
            gon=tick_data["gon"]
        )
        
        # Wrap into the full captured log message schema
        log_entry = {
            "timestamp": time.time(),
            "url": "https://exodus.stockbit.com/order-trade/running-trade?limit=10&symbols%5B%5D=BBCA&action_type=RUNNING_TRADE_ACTION_TYPE_ALL&market_board=BOARD_TYPE_ALL&sort=desc&order_by=RUNNING_TRADE_ORDER_BY_TIME",
            "payload": {
                "message": "Successfully loaded running trade data",
                "data": {
                    "is_open_market": True,
                    "running_trade": [trade_item],
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
            }
        }
        
        # Append to live stream file
        with open(live_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        print(f"[+] Appended mock tick {i+1}/5: {tick_data['action'].upper()} {tick_data['lot']} lot of BBCA at Rp {tick_data['price']:,} (Group: {tick_data['gon']})")
        time.sleep(1.0)
        
    print("[*] Stream simulation completed successfully.")

if __name__ == "__main__":
    main()
