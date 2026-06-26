import os
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure research/indicators is in Python path for importing models
current_dir = os.path.dirname(os.path.abspath(__file__))
research_dir = os.path.abspath(os.path.join(current_dir, "..", "research", "indicators"))
if research_dir not in sys.path:
    sys.path.append(research_dir)

from simulator.replay import HistoricalReplaySimulator
from strategy.remora_strategy import RemoraStrategy

def run_backtest_for_symbol(symbol: str, start_date: str, end_date: str, initial_cash: float, db_dsn: str, window: int):
    symbol = symbol.upper()
    print("\n" + "=" * 80)
    print(f" RUNNING REMORA STRATEGY BACKTEST FOR: {symbol}")
    print(f" Period: {start_date} to {end_date}")
    print(f" Database: {db_dsn}")
    print("=" * 80)

    # 1. Initialize simulator & strategy
    simulator = HistoricalReplaySimulator(db_dsn=db_dsn)
    strategy = RemoraStrategy(symbol=symbol, initial_cash=initial_cash, db_dsn=db_dsn, window_size=window)
    
    # 2. Replay ticks
    tick_generator = simulator.get_ticks(symbol, start_date, end_date)
    
    ticks_processed = 0
    print("[BACKTEST] Simulating trades. Please wait...")
    
    for tick in tick_generator:
        ticks_processed += 1
        strategy.process_tick(tick)
        
    print(f"[BACKTEST] Simulation finished. Processed {ticks_processed:,} ticks.")
    
    # 3. Calculate metrics
    metrics = strategy.get_summary_metrics()
    
    print("\n" + "-" * 40)
    print(f" BACKTEST RESULTS SUMMARY: {symbol}")
    print("-" * 40)
    print(f" Total Ticks Processed: {ticks_processed:,}")
    print(f" Initial Capital      : Rp {metrics['initial_cash']:,}")
    print(f" Final Portfolio Value: Rp {metrics['final_portfolio_value']:,}")
    print(f" Net Profit           : Rp {metrics['net_profit']:+,}")
    print(f" Total Trades Executed: {metrics['total_trades']}")
    
    if metrics['total_trades'] > 0:
        print(f" Win Rate             : {metrics['win_rate']}%")
        print(f" Profit Factor        : {metrics['profit_factor']}")
        print(f" Maximum Drawdown     : {metrics['max_drawdown']}%")
    else:
        print(" Win Rate             : N/A")
        print(" Profit Factor        : N/A")
        print(" Maximum Drawdown     : N/A")
    print("-" * 40)
    
    # Return metrics and trade logs
    return {
        "symbol": symbol,
        "metrics": metrics,
        "trades": strategy.trades_log,
        "ticks_processed": ticks_processed
    }

def main():
    parser = argparse.ArgumentParser(description="Stockbit Explorer Remora Strategy Backtester.")
    parser.add_argument("--symbols", type=str, default="VKTR", help="Comma-separated ticker list (e.g. VKTR,PANI,BUMI,PTRO,SINI)")
    parser.add_argument("--start-date", type=str, default="2026-06-20", help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2026-06-26", help="End Date (YYYY-MM-DD)")
    parser.add_argument("--initial-cash", type=float, default=100000000.0, help="Initial Cash Capital (default: 100M IDR)")
    parser.add_argument("--window", type=int, default=300, help="Rolling Tape Reading window size")
    parser.add_argument("--db", type=str, default=None, help="PostgreSQL DSN")
    args = parser.parse_args()

    # Load parameters
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    db_dsn = args.db or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
    )
    
    reports_dir = os.path.join(current_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    results = {}
    
    for sym in symbols:
        try:
            res = run_backtest_for_symbol(
                symbol=sym,
                start_date=args.start_date,
                end_date=args.end_date,
                initial_cash=args.initial_cash,
                db_dsn=db_dsn,
                window=args.window
            )
            results[sym] = res
            
            # Save individual report
            report_file = os.path.join(reports_dir, f"report_{sym}_{args.start_date}_to_{args.end_date}.json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=4)
            print(f"[REPORTS] Individual backtest report saved to: {os.path.basename(report_file)}")
            
        except Exception as e:
            print(f"[ERROR] Failed running backtest for {sym}: {e}")
            
    # Save overall summary
    if len(symbols) > 1:
        summary_file = os.path.join(reports_dir, f"summary_multi_{args.start_date}_to_{args.end_date}.json")
        summary_data = {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "initial_cash_per_symbol": args.initial_cash,
            "run_time": datetime.now().isoformat(),
            "tickers": {}
        }
        for sym, data in results.items():
            summary_data["tickers"][sym] = data["metrics"]
            
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=4)
        print(f"\n[REPORTS] Multi-symbol summary report saved to: {os.path.basename(summary_file)}")

if __name__ == "__main__":
    main()
