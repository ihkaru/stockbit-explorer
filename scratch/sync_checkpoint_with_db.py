import os
import sys
import json
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:6432/stockbit_explorer")
CHECKPOINT_PATH = os.path.join("data", "backload_progress.json")

def get_trading_days(conn, start_date_str, end_date_str):
    """Returns weekdays in the range."""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    current_dt = start_dt
    trading_days = []
    while current_dt <= end_dt:
        if current_dt.weekday() < 5:
            trading_days.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=1)
    return trading_days

def main():
    print(f"Connecting to database: {DB_URL}")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    # 36 Ticker list
    symbols = [
        "ARTO","ASII","AXIO","BBCA","BBRM","BIPI","BREN","BRPT","BUMI","DCII","FORE","GOTO",
        "KBLV","KOPI","KOTA","LEAD","LSIP","NCKL","PANI","PTBA","PTRO","RAJA","RBMS","RGAS",
        "SIDO","SINI","SKRN","SMIL","TLKM","TOOL","TOWR","TPIA","UDNG","VKTR","WINR","YELO"
    ]
    
    start_date = "2026-06-19"
    end_date = "2026-06-26"
    trading_days = get_trading_days(conn, start_date, end_date)
    print(f"Trading days in range: {trading_days}")
    
    # Load existing checkpoint if any, to preserve other keys if necessary
    checkpoint = {"completed_tickers": {}}
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            print("Loaded existing checkpoint. Will overwrite target symbols progress based on DB.")
        except Exception as e:
            print(f"Could not load existing checkpoint: {e}. Starting fresh.")

    for symbol in symbols:
        print(f"Syncing checkpoint for {symbol}...")
        
        # 1. Check if OHLCV EOD is completed for the range
        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(volume), 0) FROM ohlcv_data WHERE symbol = %s AND date >= %s AND date <= %s AND time = 'EOD'",
            (symbol, start_date, end_date)
        )
        res_ohlcv = cur.fetchone()
        ohlcv_count = res_ohlcv[0]
        
        ohlcv_completed = ohlcv_count >= len(trading_days)
        
        # 2. Check if foreign flow is completed for the range
        cur.execute(
            "SELECT COUNT(*) FROM broker_daily_activity WHERE symbol = %s AND date >= %s AND date <= %s",
            (symbol, start_date, end_date)
        )
        ff_count = cur.fetchone()[0]
        # Foreign flow is completed if we have at least one record per trading day (or if it's a zero volume suspended stock, we might have fewer but let's check >= trading days count)
        foreign_flow_completed = ff_count >= len(trading_days)
        
        broker_summary_dates = []
        intraday_dates = []
        running_trades_dates = []
        
        for d in trading_days:
            # Check if this day is a zero volume day (e.g. suspended stock like DCII)
            cur.execute(
                "SELECT COALESCE(SUM(volume), 0) FROM ohlcv_data WHERE symbol = %s AND date = %s AND time = 'EOD'",
                (symbol, d)
            )
            eod_vol_res = cur.fetchone()
            is_zero_vol = (eod_vol_res is not None) and (eod_vol_res[0] == 0)
            
            # Check broker summary
            cur.execute(
                "SELECT COUNT(*) FROM broker_summaries WHERE symbol = %s AND date = %s",
                (symbol, d)
            )
            bs_count = cur.fetchone()[0]
            if bs_count > 0 or is_zero_vol or symbol.upper() == "IHSG":
                broker_summary_dates.append(d)
                
            # Check intraday candles (time != 'EOD')
            cur.execute(
                "SELECT COUNT(*) FROM ohlcv_data WHERE symbol = %s AND date = %s AND time != 'EOD'",
                (symbol, d)
            )
            intra_count = cur.fetchone()[0]
            if intra_count >= 100 or is_zero_vol:
                intraday_dates.append(d)
                
            # Check running trades
            dt_start = datetime.strptime(d, "%Y-%m-%d")
            start_ts = dt_start.timestamp()
            end_ts = start_ts + 86400
            cur.execute(
                "SELECT COUNT(*) FROM running_trades WHERE symbol = %s AND timestamp >= %s AND timestamp < %s",
                (symbol, start_ts, end_ts)
            )
            rt_count = cur.fetchone()[0]
            if rt_count > 0 or is_zero_vol:
                running_trades_dates.append(d)
                
        # Update checkpoint entry
        checkpoint["completed_tickers"][symbol] = {
            "ohlcv_completed": ohlcv_completed,
            "foreign_flow_completed": foreign_flow_completed,
            "broker_summary_dates": sorted(list(set(broker_summary_dates))),
            "broker_summary_completed": len(broker_summary_dates) >= len(trading_days),
            "intraday_dates": sorted(list(set(intraday_dates))),
            "intraday_completed": len(intraday_dates) >= len(trading_days),
            "running_trades_dates": sorted(list(set(running_trades_dates))),
            "running_trade_completed": len(running_trades_dates) >= len(trading_days)
        }
        
    # Save checkpoint back
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)
        
    print(f"Successfully synced and wrote checkpoint to {CHECKPOINT_PATH}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
