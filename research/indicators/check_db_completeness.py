import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
import argparse
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_dsn(dsn):
    """Enforces fail-fast validation to ensure the database connection string uses PostgreSQL."""
    if not (dsn.startswith("postgres://") or dsn.startswith("postgresql://")):
        raise ValueError(
            f"FAIL-FAST: Invalid Database DSN. Connection string must use postgres:// or postgresql:// scheme. Got: {dsn}"
        )

def get_trading_days(start_date_str, end_date_str):
    """Returns a list of date strings (YYYY-MM-DD) representing weekdays (Monday-Friday) in the range."""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    current_dt = start_dt
    trading_days = []
    while current_dt <= end_dt:
        # Weekday check: 0=Monday, 6=Sunday. Weekdays are 0 to 4.
        if current_dt.weekday() < 5:
            trading_days.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=1)
    return trading_days

def check_ticker_completeness(conn, symbol, date_str, eod_only=False):
    """
    Standard check for 1 ticker's data completeness in 1 day.
    
    Returns a dictionary containing row counts and boolean completeness flags.
    """
    cursor = conn.cursor()
    
    # 1. Parse date for running trade timestamp bounds (in local/UTC epoch)
    try:
        dt_start = datetime.strptime(date_str, "%Y-%m-%d")
        start_ts = dt_start.timestamp()
        end_ts = start_ts + 86400
    except Exception as e:
        raise ValueError(f"Invalid date format: {date_str}. Must be YYYY-MM-DD. Error: {e}")

    # 2. Check daily OHLCV EOD candle count and volume
    cursor.execute(
        "SELECT COUNT(*), COALESCE(SUM(volume), 0) FROM ohlcv_data WHERE symbol = %s AND date = %s AND time = 'EOD'",
        (symbol, date_str)
    )
    res_eod = cursor.fetchone()
    ohlcv_count = res_eod[0]
    eod_volume = res_eod[1]

    # Check daily OHLCV Intraday (1-min) candle count
    cursor.execute(
        "SELECT COUNT(*) FROM ohlcv_data WHERE symbol = %s AND date = %s AND time != 'EOD'",
        (symbol, date_str)
    )
    intraday_count = cursor.fetchone()[0]

    # 3. Check Broker Summary count
    cursor.execute(
        "SELECT COUNT(*) FROM broker_summaries WHERE symbol = %s AND date = %s",
        (symbol, date_str)
    )
    bs_count = cursor.fetchone()[0]

    # 4. Check Net Foreign Flow count
    cursor.execute(
        "SELECT COUNT(*) FROM broker_daily_activity WHERE symbol = %s AND date = %s",
        (symbol, date_str)
    )
    bda_count = cursor.fetchone()[0]

    # 5. Check Running Trades count (optional / live only)
    cursor.execute(
        "SELECT COUNT(*) FROM running_trades WHERE symbol = %s AND timestamp >= %s AND timestamp < %s",
        (symbol, start_ts, end_ts)
    )
    rt_count = cursor.fetchone()[0]

    # Completeness flags
    has_ohlcv = ohlcv_count > 0
    is_zero_volume_day = has_ohlcv and eod_volume == 0
    
    has_intraday = intraday_count > 0 or is_zero_volume_day
    # IHSG is an index, it does not have broker summary data.
    has_broker_summary = bs_count > 0 or symbol.upper() == "IHSG" or is_zero_volume_day
    has_foreign_flow = bda_count > 0 or is_zero_volume_day
    has_running_trades = rt_count > 0 or is_zero_volume_day

    # EOD-only completeness requires EOD candles, Broker Summary (for stocks), and Foreign Flow.
    is_eod_complete = has_ohlcv and has_broker_summary and has_foreign_flow
    
    # Full completeness (Default) requires all EOD data + Intraday candles + Running Trades
    # NOTE: IHSG index does not have running trade tick-by-tick data in standard feeds.
    has_running_trades_check = has_running_trades or symbol.upper() == "IHSG"
    has_intraday_check = has_intraday or symbol.upper() == "IHSG"
    is_full_complete = is_eod_complete and has_running_trades_check and has_intraday_check

    is_complete = is_eod_complete if eod_only else is_full_complete

    return {
        "symbol": symbol,
        "date": date_str,
        "ohlcv_count": ohlcv_count,
        "intraday_count": intraday_count,
        "broker_summary_count": bs_count,
        "foreign_flow_count": bda_count,
        "running_trades_count": rt_count,
        "has_ohlcv": has_ohlcv,
        "has_intraday": has_intraday,
        "has_broker_summary": bs_count > 0,
        "has_foreign_flow": has_foreign_flow,
        "has_running_trades": has_running_trades,
        "is_eod_complete": is_eod_complete,
        "is_full_complete": is_full_complete,
        "is_complete": is_complete
    }

def main():
    parser = argparse.ArgumentParser(description="Standardized Data Completeness Audit Tool for Stockbit Explorer.")
    parser.add_argument("--symbol", type=str, default=None, help="Ticker symbol to check (e.g. BBCA). If omitted, checks all tickers.")
    parser.add_argument("--date", type=str, default=None, help="Check completeness for a single date (YYYY-MM-DD).")
    parser.add_argument("--start-date", type=str, default=None, help="Start date of range audit (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=str, default=None, help="End date of range audit (YYYY-MM-DD).")
    parser.add_argument("--eod-only", action="store_true", help="Audit EOD data only (EOD candles, Broker Summaries, Net Foreign Flow) and skip Running Trade/Intraday check.")
    parser.add_argument("--db", type=str, default=None, help="PostgreSQL DSN. Defaults to DATABASE_URL environment variable.")
    parser.add_argument("--json", action="store_true", help="Print report output in machine-readable JSON format.")
    args = parser.parse_args()

    # DSN setup
    dsn = args.db or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
    )
    
    # Fail-fast validation
    try:
        validate_dsn(dsn)
    except ValueError as val_err:
        print(str(val_err), file=sys.stderr)
        sys.exit(1)

    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve date range
    today_str = datetime.now().strftime("%Y-%m-%d")
    if args.date:
        start_date = args.date
        end_date = args.date
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        # Default: check today only
        start_date = today_str
        end_date = today_str

    trading_days = get_trading_days(start_date, end_date)
    if not trading_days:
        print(f"No trading days (weekdays) found in the range {start_date} to {end_date}.")
        conn.close()
        sys.exit(0)

    # Resolve symbol(s)
    symbols = []
    if args.symbol:
        symbols = [s.strip().upper() for s in args.symbol.split(",") if s.strip()]
    else:
        # Fetch all unique symbols currently present in the database across main tables
        symbol_set = set()
        for table in ["ohlcv_data", "broker_summaries", "broker_daily_activity", "running_trades"]:
            try:
                cursor.execute(f"SELECT DISTINCT symbol FROM {table}")
                for row in cursor.fetchall():
                    if row[0]:
                        symbol_set.add(row[0].upper())
            except Exception:
                pass # Table might be empty or missing schema
        symbols = sorted(list(symbol_set))

    if not symbols:
        if args.json:
            print(json.dumps({"error": "No symbols found in database.", "results": []}))
        else:
            print("No symbols found in the database.")
        conn.close()
        sys.exit(0)

    # Perform audit
    results = []
    missing_by_ticker = {}
    
    for symbol in symbols:
        for date_str in trading_days:
            try:
                res = check_ticker_completeness(conn, symbol, date_str, eod_only=args.eod_only)
                results.append(res)
                
                if not res["is_complete"]:
                    if symbol not in missing_by_ticker:
                        missing_by_ticker[symbol] = []
                    missing_by_ticker[symbol].append(date_str)
            except Exception as e:
                # Log error and continue
                results.append({
                    "symbol": symbol,
                    "date": date_str,
                    "error": str(e),
                    "is_complete": False
                })

    conn.close()

    # Output formatting
    if args.json:
        print(json.dumps({
            "dsn": dsn,
            "checked_range": {"start": start_date, "end": end_date},
            "total_checked": len(results),
            "total_missing": sum(1 for r in results if not r.get("is_complete", False)),
            "results": results
        }, indent=2))
        sys.exit(0)

    # Human-readable report
    print("=" * 120)
    print(f" STANDARDIZED DATA COMPLETENESS AUDIT REPORT")
    print(f" Checked Range: {start_date} to {end_date} ({len(trading_days)} trading days)")
    print(f" Criteria     : {'EOD (OHLCV EOD + Broker Sum + Foreign Flow)' if args.eod_only else 'Full (OHLCV EOD + Intraday 1m + Broker Sum + Foreign Flow + Running Trades)'}")
    print(f" Database     : {dsn}")
    print("=" * 120)
    
    print(f" {'Ticker':<8} | {'Date':<10} | {'OHLCV EOD':<9} | {'Intraday':<8} | {'BrokerSum':<9} | {'ForeignFlw':<10} | {'RunTrades':<9} | {'Status'}")
    print("-" * 120)

    complete_count = 0
    incomplete_count = 0

    for r in results:
        if "error" in r:
            print(f" {r['symbol']:<8} | {r['date']:<10} | {'ERROR':<53} | FAILED")
            incomplete_count += 1
            continue
            
        ohlcv_status = "OK" if r["has_ohlcv"] else "MISSING"
        intraday_status = f"{r['intraday_count']:,}" if r["has_intraday"] else "MISSING"
        bs_status = "OK" if r["has_broker_summary"] else "MISSING"
        ff_status = "OK" if r["has_foreign_flow"] else "MISSING"
        rt_status = f"{r['running_trades_count']:,}" if r["has_running_trades"] else "MISSING"
        
        status_str = "LENGKAP" if r["is_complete"] else "BELUM LENGKAP"
        
        if r["is_complete"]:
            complete_count += 1
        else:
            incomplete_count += 1

        print(f" {r['symbol']:<8} | {r['date']:<10} | {ohlcv_status:<9} | {intraday_status:<8} | {bs_status:<9} | {ff_status:<10} | {rt_status:<9} | {status_str}")

    print("-" * 120)
    print(f" SUMMARY: Total Checked: {len(results)} | Complete: {complete_count} | Incomplete: {incomplete_count}")
    print("=" * 120)
    
    if incomplete_count > 0:
        print("\n[RECOMMENDATION] Run the backloader for these missing tickers:")
        print(f"Symbols list for CLI: {','.join(missing_by_ticker.keys())}")
        print("Command suggestion:")
        print(f"  $env:DATABASE_URL=\"{dsn}\"; python research/indicators/backloader.py --symbols {','.join(missing_by_ticker.keys())} --start-date {start_date} --end-date {end_date} --workers 16")
    else:
        print("\n SUCCESS: 100% data completeness achieved across all checked items!")
    print("=" * 110)

if __name__ == "__main__":
    main()

