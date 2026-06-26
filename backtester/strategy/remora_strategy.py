import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure research/indicators is in Python path for importing modules
current_dir = os.path.dirname(os.path.abspath(__file__))
research_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "research", "indicators"))
if research_dir not in sys.path:
    sys.path.append(research_dir)

from tape_reading.analyzer import TapeReadingAnalyzer
from tape_reading.models import TradeTick, HAKAHAKIResult

class RemoraStrategy:
    """
    Remora Strategy Backtest Engine.
    Simulates portfolio entry and exit signals based on rolling intraday tape reading
    and dynamically calculated prior 10-day EOD Broker Summaries (no look-ahead bias).
    """
    def __init__(self, symbol: str, initial_cash: float = 100000000.0, db_dsn=None, window_size: int = 300):
        self.symbol = symbol.upper()
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.window_size = window_size
        self.dsn = db_dsn or os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
        )
        self.analyzer = TapeReadingAnalyzer(self.dsn)
        
        # Strategy state
        self.rolling_trades = []
        self.position = None  # None or dict with keys: entry_price, entry_time, lot, stop_loss, take_profit
        self.trades_log = []
        
        # Cache EOD broker summaries and unique dates to calculate dynamically
        self.broker_summaries_by_date = {}
        self.unique_dates = []
        self._load_eod_summaries_cache()
        
    def _load_eod_summaries_cache(self):
        """Loads all EOD broker summaries for this symbol in memory for fast prior date calculations."""
        conn = psycopg2.connect(self.dsn)
        conn.cursor_factory = DictCursor
        
        query = """
            SELECT date, broker_code, net_lot, net_value, avg_price
            FROM broker_summaries
            WHERE symbol = %s
            ORDER BY date ASC
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, [self.symbol])
                rows = cursor.fetchall()
                
            for r in rows:
                d = r["date"]
                if d not in self.broker_summaries_by_date:
                    self.broker_summaries_by_date[d] = []
                    self.unique_dates.append(d)
                self.broker_summaries_by_date[d].append(dict(r))
            
            # Sort unique dates chronologically
            self.unique_dates.sort()
            print(f"[STRATEGY] Loaded {len(self.unique_dates)} dates of EOD summaries for {self.symbol}.")
        except Exception as e:
            print(f"[WARNING] Failed to load EOD summaries cache for {self.symbol}: {e}")
        finally:
            conn.close()

    def get_prior_buyers(self, target_date: str, days_limit: int = 10) -> list:
        """
        Gets the cumulative net buyers for the last N days prior to target_date.
        Prevents look-ahead bias by only utilizing historical data before target_date.
        """
        # Find dates that are strictly less than target_date
        prior_dates = [d for d in self.unique_dates if d < target_date][-days_limit:]
        if not prior_dates:
            return []
            
        cum_buyers = {}
        for d in prior_dates:
            for r in self.broker_summaries_by_date.get(d, []):
                bc = r["broker_code"]
                net_lot = float(r["net_lot"] or 0)
                net_val = float(r["net_value"] or 0.0)
                if bc not in cum_buyers:
                    cum_buyers[bc] = {"net_lot": 0.0, "net_val": 0.0}
                cum_buyers[bc]["net_lot"] += net_lot
                cum_buyers[bc]["net_val"] += net_val
                
        buyers = []
        for bc, data in cum_buyers.items():
            net_lot = data["net_lot"]
            net_val = data["net_val"]
            if net_lot > 0:
                avg_price = net_val / (net_lot * 100) if net_lot > 0 else 0
                buyers.append({
                    "broker_code": bc,
                    "net_lot": net_lot,
                    "avg_price": round(avg_price, 2)
                })
                
        # Sort by net lot descending
        buyers.sort(key=lambda x: x["net_lot"], reverse=True)
        return buyers

    def process_tick(self, tick: TradeTick) -> HAKAHAKIResult:
        """
        Processes a single running trade tick.
        Maintains the rolling window, runs the signal engine, and triggers trade decisions.
        """
        # Convert timestamp to date string
        tick_time = datetime.fromtimestamp(tick.timestamp, tz=timezone.utc)
        tick_date = tick_time.strftime("%Y-%m-%d")
        
        # 1. Update rolling window
        self.rolling_trades.append(tick)
        if len(self.rolling_trades) > self.window_size:
            self.rolling_trades.pop(0)
            
        # We need at least 10 trades before running signal engine (MIN_TRADE_COUNT)
        if len(self.rolling_trades) < 10:
            return None
            
        # 2. Get prior EOD average price of bandar up to this tick date
        prior_buyers = self.get_prior_buyers(tick_date, days_limit=10)
        
        # 3. Compute HAKA/HAKI signal
        result = self.analyzer.engine.compute(self.symbol, self.rolling_trades, prior_buyers)
        
        # 4. Check trade triggers
        self._check_trade_logic(result, tick, tick_time)
        
        return result

    def _check_trade_logic(self, result: HAKAHAKIResult, tick: TradeTick, tick_time: datetime):
        price = tick.price
        
        # Handle Open Position
        if self.position:
            pos = self.position
            # Expiry: hold max 40 calendar days
            days_held = (tick_time - pos["entry_time"]).days
            
            # Check exit conditions
            is_stop_loss = price <= pos["stop_loss"]
            is_take_profit = price >= pos["take_profit"]
            is_sell_signal = result.signal == "SELL"
            is_expired = days_held >= 40
            
            if is_stop_loss or is_take_profit or is_sell_signal or is_expired:
                # Sell and close position
                exit_price = price
                lots = pos["lot"]
                pnl = (exit_price - pos["entry_price"]) * lots * 100
                return_pct = (exit_price - pos["entry_price"]) / pos["entry_price"]
                
                self.cash += exit_price * lots * 100
                
                reason = "STOP_LOSS" if is_stop_loss else \
                         "TAKE_PROFIT" if is_take_profit else \
                         "SELL_SIGNAL" if is_sell_signal else "EXPIRED"
                         
                self.trades_log.append({
                    "symbol": self.symbol,
                    "entry_time": pos["entry_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": tick_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "entry_price": pos["entry_price"],
                    "exit_price": exit_price,
                    "lot": lots,
                    "pnl": pnl,
                    "return_pct": round(return_pct * 100, 2),
                    "exit_reason": reason,
                    "days_held": days_held
                })
                
                print(f"[TRADE] CLOSED {self.symbol} at Rp {exit_price:,} | Reason: {reason} | PnL: Rp {pnl:+,} ({return_pct:+.2%})")
                self.position = None
                
        # Handle Entry Logic
        else:
            # Entry condition: BUY signal and price within Cheap Entry Zone
            is_buy = result.signal == "BUY" and (result.signal_strength in ("STRONG", "MODERATE", "MODERATE (INSTITUTIONAL ACCUMULATION)"))
            
            # Cheap Entry Zone validation
            cheap_high = result.cheap_entry_high
            if not cheap_high:
                # Fallback cheap entry zone high = 5% above price if no broker summaries
                cheap_high = price * 1.05
                
            is_in_cheap_zone = price <= cheap_high
            
            if is_buy and is_in_cheap_zone:
                # Determine buy budget based on max allocation (e.g. 100% of cash for single stock)
                # Ensure we have enough cash
                if self.cash > (price * 100):
                    lots_to_buy = int(self.cash / (price * 100))
                    if lots_to_buy > 0:
                        buy_val = price * lots_to_buy * 100
                        self.cash -= buy_val
                        
                        # Set SL / TP
                        sl = result.stop_loss
                        tp = result.take_profit
                        
                        # Fallback if no prior EOD summaries
                        if not sl:
                            sl = price * 0.96  # 4% Stop Loss
                        if not tp:
                            sl_dist = price - sl
                            tp = price + (sl_dist * 2.5) if sl_dist > 0 else price * 1.10
                            
                        self.position = {
                            "symbol": self.symbol,
                            "entry_price": price,
                            "entry_time": tick_time,
                            "lot": lots_to_buy,
                            "stop_loss": sl,
                            "take_profit": tp
                        }
                        
                        print(f"[TRADE] OPENED {self.symbol} at Rp {price:,} | Lots: {lots_to_buy} | SL: Rp {sl:.1f} | TP: Rp {tp:.1f}")

    def get_summary_metrics(self) -> dict:
        """Computes performance metrics of the backtest."""
        trades = self.trades_log
        if not trades:
            return {
                "initial_cash": self.initial_cash,
                "final_portfolio_value": self.cash,
                "net_profit": 0.0,
                "return_pct": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0
            }
            
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        
        win_rate = len(wins) / len(trades) if trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 1.0
        
        # Calculate maximum drawdown from equity curve
        equity = self.initial_cash
        equity_curve = [equity]
        for t in trades:
            equity += t["pnl"]
            equity_curve.append(equity)
            
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
                
        net_profit = equity - self.initial_cash
        return_pct = (net_profit / self.initial_cash) * 100
        
        return {
            "initial_cash": self.initial_cash,
            "final_portfolio_value": equity,
            "net_profit": net_profit,
            "return_pct": round(return_pct, 2),
            "total_trades": len(trades),
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "Infinite",
            "max_drawdown": round(max_dd * 100, 2)
        }
