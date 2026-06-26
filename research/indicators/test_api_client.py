import json
import logging
from api_client import StockbitApiClient

# Configure basic logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    print("=" * 80)
    print(" STOCKBIT API CLIENT INTEGRATION TEST (MULTIPLE TICKERS)")
    print("=" * 80)
    
    try:
        client = StockbitApiClient()
    except Exception as e:
        print(f"FAILED initialization: {e}")
        return

    # General Test A: Brokers Catalog
    print("\n" + "=" * 60)
    print(" TESTING GENERAL API ENDPOINTS")
    print("=" * 60)
    print("\n[TEST A] Fetching Brokers Catalog...")
    try:
        b_data = client.get_brokers(limit=5)
        brokers = b_data.get("data", [])
        print(f"  [SUCCESS] Received {len(brokers)} brokers in catalog.")
        if len(brokers) > 0:
            print(f"  Sample Broker: {brokers[0].get('code')} - {brokers[0].get('name')}")
    except Exception as e:
        print(f"  [FAILED] Brokers Catalog: {e}")

    # General Test B: User Watchlists
    watchlist_id = None
    print("\n[TEST B] Fetching User Watchlists...")
    try:
        w_data = client.get_watchlists()
        watchlists = w_data.get("data", [])
        print(f"  [SUCCESS] Received {len(watchlists)} watchlists.")
        if len(watchlists) > 0:
            watchlist_id = watchlists[0].get("watchlist_id")
            print(f"  Sample Watchlist: {watchlists[0].get('name')} (ID: {watchlist_id})")
    except Exception as e:
        print(f"  [FAILED] User Watchlists: {e}")

    # General Test C: Watchlist Detail (if watchlist found)
    if watchlist_id:
        print(f"\n[TEST C] Fetching Watchlist Details (ID: {watchlist_id})...")
        try:
            wd_data = client.get_watchlist_detail(watchlist_id=watchlist_id, limit=5)
            items = wd_data.get("data", {}).get("result", [])
            print(f"  [SUCCESS] Received {len(items)} items in watchlist.")
            if len(items) > 0:
                print(f"  Sample Ticker in Watchlist: {items[0].get('symbol')} - {items[0].get('name')}")
        except Exception as e:
            print(f"  [FAILED] Watchlist Details: {e}")

    tickers = ["BBCA", "TLKM", "GOTO", "ASII"]

    for symbol in tickers:
        print("\n" + "#" * 60)
        print(f" TESTING TICKER: {symbol}")
        print("#" * 60)

        # Test 1: Running Trade
        print(f"\n[TEST 1] Fetching Running Trade ({symbol})...")
        try:
            rt_data = client.get_running_trade(symbols=[symbol], limit=2)
            rt_list = rt_data.get("data", {}).get("running_trade", [])
            print(f"  [SUCCESS] Received {len(rt_list)} trades.")
            if len(rt_list) > 0:
                print(f"  Sample Trade ID: {rt_list[0].get('id')} | Price: {rt_list[0].get('price')} | Lot: {rt_list[0].get('lot')}")
        except Exception as e:
            print(f"  [FAILED] Running Trade: {e}")

        # Test 2: Trade Book
        print(f"\n[TEST 2] Fetching Trade Book ({symbol})...")
        try:
            tb_data = client.get_trade_book(symbol=symbol)
            book = tb_data.get("data", {}).get("book", [])
            print(f"  [SUCCESS] Received {len(book)} price levels in trade book.")
            if len(book) > 0:
                print(f"  Sample Price Level: {book[0].get('price')} | Buy Lot: {book[0].get('buy', {}).get('lot')}")
        except Exception as e:
            print(f"  [FAILED] Trade Book: {e}")

        # Test 3: Order Queue
        print(f"\n[TEST 3] Fetching Order Queue ({symbol})...")
        try:
            oq_data = client.get_order_queue(stock_code=symbol)
            orders = oq_data.get("data", {}).get("orders", [])
            print(f"  [SUCCESS] Order Queue request succeeded. orders list size: {len(orders)}")
        except Exception as e:
            print(f"  [FAILED] Order Queue: {e}")

        # Test 4: Market Detector (EOD Broker Summary & Date Ranges)
        print(f"\n[TEST 4] Fetching Market Detector ({symbol})...")
        try:
            # Test 4a: Single-day
            md_data = client.get_market_detector(stock_code=symbol, from_date="2026-06-25", to_date="2026-06-25")
            inner_data = md_data.get("data", {})
            bd = inner_data.get("bandar_detector", {})
            bs = inner_data.get("broker_summary", {})
            print(f"  [SUCCESS] Single-day Market Detector retrieved (2026-06-25 to 2026-06-25).")
            print(f"    Bandar Verdict: {bd.get('broker_accdist')} | Net Value: Rp {bd.get('value'):,}")
            print(f"    Buyers count: {len(bs.get('brokers_buy', []))} | Sellers count: {len(bs.get('brokers_sell', []))}")
            if len(bs.get('brokers_buy', [])) > 0:
                b_sample = bs.get('brokers_buy', [])[0]
                print(f"    Top Buyer: {b_sample.get('netbs_broker_code')} | Net Lot: {b_sample.get('blot')} | Avg Price: {round(float(b_sample.get('netbs_buy_avg_price', 0)))}")

            # Test 4b: Multi-day range (last 7 days approx)
            md_data_multi = client.get_market_detector(stock_code=symbol, from_date="2026-06-19", to_date="2026-06-25")
            inner_data_multi = md_data_multi.get("data", {})
            bd_multi = inner_data_multi.get("bandar_detector", {})
            bs_multi = inner_data_multi.get("broker_summary", {})
            print(f"  [SUCCESS] Multi-day Market Detector retrieved (2026-06-19 to 2026-06-25).")
            print(f"    Bandar Verdict: {bd_multi.get('broker_accdist')} | Cumulative Net Value: Rp {bd_multi.get('value'):,}")
            print(f"    Buyers count: {len(bs_multi.get('brokers_buy', []))} | Sellers count: {len(bs_multi.get('brokers_sell', []))}")
            if len(bs_multi.get('brokers_buy', [])) > 0:
                b_sample_multi = bs_multi.get('brokers_buy', [])[0]
                print(f"    Top Cumulative Buyer: {b_sample_multi.get('netbs_broker_code')} | Net Lot: {b_sample_multi.get('blot')} | Avg Price: {round(float(b_sample_multi.get('netbs_buy_avg_price', 0)))}")
        except Exception as e:
            print(f"  [FAILED] Market Detector: {e}")

        # Test 4c: Company Info & Profile (Fundamental Metadata)
        print(f"\n[TEST 4c] Fetching Company Info & Profile ({symbol})...")
        try:
            info = client.get_company_info(symbol=symbol)
            print(f"  [SUCCESS] Info: Sector: {info.get('data', {}).get('sector')} | Followers: {info.get('data', {}).get('followers')}")
            
            profile = client.get_company_profile(symbol=symbol)
            print(f"  [SUCCESS] Profile background length: {len(profile.get('data', {}).get('background') or '')} chars")
            
            ins_comp = client.get_insider_composition(symbol=symbol)
            print(f"  [SUCCESS] Insider Composition periods count: {len(ins_comp.get('data', {}).get('periods', []))}")
            
            ins_maj = client.get_insider_majorholders(symbol=symbol, limit=2)
            print(f"  [SUCCESS] Insider Majorholders movements count: {len(ins_maj.get('data', {}).get('movement', []))}")
            
            keystats = client.get_keystats(symbol=symbol)
            print(f"  [SUCCESS] Keystats groups count: {len(keystats.get('data', {}).get('closure_fin_items_results', []))}")
            
            consensus = client.get_analyst_consensus(symbol=symbol)
            print(f"  [SUCCESS] Analyst Consensus metrics count: {len(consensus.get('data', []))}")

            ratings = client.get_analyst_ratings(symbol=symbol)
            print(f"  [SUCCESS] Analyst Ratings recommendation: {ratings.get('data', {}).get('recommendation')} | Target: {ratings.get('data', {}).get('price_target', {}).get('best_target')}")
        except Exception as e:
            print(f"  [FAILED] Company Metadata: {e}")

        # Test 5: Prices (Price grid fraction)
        print(f"\n[TEST 5] Fetching Price Grid ({symbol})...")
        try:
            p_data = client.get_prices(stock_code=symbol)
            prices = p_data.get("data", {}).get("prices", [])
            print(f"  [SUCCESS] Received {len(prices)} price fractions in price grid.")
            if len(prices) > 0:
                print(f"  Sample fraction: {prices[0]} s.d {prices[-1]}")
        except Exception as e:
            print(f"  [FAILED] Price Grid: {e}")

        # Test 6: Historical Summary (Broker Daily Activity / Foreign Flow)
        print(f"\n[TEST 6] Fetching Historical Summary / Broker Daily Activity ({symbol})...")
        try:
            hs_data = client.get_historical_summary(symbol=symbol, limit=5)
            result = hs_data.get("data", {}).get("result", [])
            print(f"  [SUCCESS] Received {len(result)} daily records.")
            if len(result) > 0:
                print(f"  Sample Record: Date: {result[0].get('date')} | Close: {result[0].get('close')} | Net Foreign: {result[0].get('net_foreign')}")
        except Exception as e:
            print(f"  [FAILED] Historical Summary: {e}")

        # Test 7: Orderbook Depth Snapshot
        print(f"\n[TEST 7] Fetching Orderbook Snapshot ({symbol})...")
        try:
            ob_data = client.get_orderbook(symbol=symbol)
            data = ob_data.get("data", {})
            print(f"  [SUCCESS] Orderbook close: {data.get('close')} | ARA: {data.get('ara', {}).get('value')} | ARB: {data.get('arb', {}).get('value')}")
            bids = data.get("bid", [])
            if bids:
                print(f"    Sample Bid Level: Price: {bids[0].get('price')} | Lot: {bids[0].get('volume')} | Queue count: {bids[0].get('que_num')}")
        except Exception as e:
            print(f"  [FAILED] Orderbook Snapshot: {e}")

        # Test 8: Foreign-Domestic Flow Detailed Chart Data
        print(f"\n[TEST 8] Fetching Foreign-Domestic Chart ({symbol})...")
        try:
            fd_data = client.get_foreign_domestic_chart(symbol=symbol)
            summary = fd_data.get("data", {}).get("summary", {})
            print(f"  [SUCCESS] Net Foreign (Regular): {summary.get('net_foreign', {}).get('value', {}).get('raw')} IDR")
            vol_sum = summary.get("volume", {})
            print(f"    Net Foreign Volume: {vol_sum.get('net_foreign_reguler', {}).get('value', {}).get('raw')} shares")
        except Exception as e:
            print(f"  [FAILED] Foreign-Domestic Chart: {e}")

        # Test 9: Intraday Candles (Chartbit)
        print(f"\n[TEST 9] Fetching Chartbit Intraday Candles ({symbol})...")
        try:
            import time
            from_unix = int(time.time())
            to_unix = from_unix - (5 * 24 * 3600)  # 5 days ago
            ic_data = client.get_intraday_candles(symbol=symbol, from_unix=from_unix, to_unix=to_unix, limit=0)
            ic_list = ic_data.get("data", {}).get("chartbit", [])
            print(f"  [SUCCESS] Received {len(ic_list)} intraday candles.")
            if len(ic_list) > 0:
                print(f"    Sample: Datetime: {ic_list[0].get('datetime')} | Close: {ic_list[0].get('close')} | Vol: {ic_list[0].get('volume')} | Freq: {ic_list[0].get('frequency')}")
        except Exception as e:
            print(f"  [FAILED] Chartbit Intraday Candles: {e}")

        # Test 10: Daily Candles (Chartbit)
        print(f"\n[TEST 10] Fetching Chartbit Daily Candles ({symbol})...")
        try:
            from datetime import datetime, timedelta
            today_str = datetime.now().strftime("%Y-%m-%d")
            past_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            dc_data = client.get_daily_candles(symbol=symbol, from_date=today_str, to_date=past_str, limit=0)
            dc_list = dc_data.get("data", {}).get("chartbit", [])
            print(f"  [SUCCESS] Received {len(dc_list)} daily candles.")
            if len(dc_list) > 0:
                print(f"    Sample: Date: {dc_list[0].get('date')} | Close: {dc_list[0].get('close')} | Vol: {dc_list[0].get('volume')} | Freq: {dc_list[0].get('frequency')}")
        except Exception as e:
            print(f"  [FAILED] Chartbit Daily Candles: {e}")

    print("\n" + "=" * 80)
    print(" ALL TICKERS INTEGRATION TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
