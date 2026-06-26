from .utils import clean_int, clean_float

def parse_emiten_profile(db, path, parsed_url, payload, timestamp):
    """Memproses profil dasar emiten, direksi, pemegang saham utama, dan UBO."""
    symbol = path.split("/")[2]
    inner_data = payload.get("data", {})
    
    history = inner_data.get("history", {})
    profile_obj = {
        "symbol": symbol,
        "background": inner_data.get("background"),
        "board": history.get("board"),
        "listing_date": history.get("date"),
        "price": clean_int(history.get("price")),
        "shares": history.get("shares"),
        "registrar": history.get("registrar"),
        "underwriters": history.get("underwriters"),
        "administrative_bureau": history.get("administrative_bureau"),
        "free_float": history.get("free_float")
    }
    db.insert_company_profile(profile_obj)
    
    # Key Executives
    execs = []
    execs_section = inner_data.get("key_executive", {})
    for role_type, people in execs_section.items():
        if isinstance(people, list):
            for p in people:
                execs.append({
                    "name": p.get("value"),
                    "role": role_type,
                    "executive_id": p.get("id"),
                    "last_update": p.get("lastupdate")
                })
    if execs:
        db.insert_company_executives(symbol, execs)
        
    # Shareholders (>1% and controllers)
    holders = []
    for h in inner_data.get("shareholder", []):
        holders.append({
            "name": h.get("name"),
            "percentage": clean_float(h.get("percentage")),
            "value": h.get("value"),
            "badges": h.get("badges"),
            "location": h.get("location"),
            "nationality": h.get("nationality"),
            "domicile": h.get("domicile"),
            "classification": h.get("classification"),
            "scripless": h.get("scripless"),
            "scrip": h.get("scrip"),
            "type": h.get("type"),
            "parent_id": h.get("id"),
            "date": inner_data.get("shareholder_one_percent", {}).get("last_updated") or "Unknown"
        })
        
    # Shareholders (One percent list)
    one_pct_holders = inner_data.get("shareholder_one_percent", {}).get("shareholder", [])
    for h in one_pct_holders:
        holders.append({
            "name": h.get("name"),
            "percentage": clean_float(h.get("percentage")),
            "value": h.get("value"),
            "badges": h.get("badges"),
            "location": h.get("location"),
            "nationality": h.get("nationality"),
            "domicile": h.get("domicile"),
            "classification": h.get("classification"),
            "scripless": h.get("scripless"),
            "scrip": h.get("scrip"),
            "type": h.get("type"),
            "parent_id": h.get("id"),
            "date": inner_data.get("shareholder_one_percent", {}).get("last_updated") or "Unknown"
        })
    if holders:
        db.insert_company_shareholders(symbol, holders)
        
    # Beneficiaries (UBO)
    benefs = [b.get("name") for b in inner_data.get("beneficiary", []) if b.get("name")]
    if benefs:
        db.insert_company_beneficiaries(symbol, benefs)
        
    # Shareholder Numbers Stats
    sh_stats = []
    for s in inner_data.get("shareholder_numbers", []):
        sh_stats.append({
            "shareholder_date": s.get("shareholder_date"),
            "total_shareholder": clean_int(s.get("total_share") or s.get("total_shares")),
            "change_value": clean_int(s.get("change_value") or s.get("change")),
            "change_formatted": s.get("change_formatted")
        })
    if sh_stats:
        db.insert_company_shareholder_stats(symbol, sh_stats)


def parse_emiten_info(db, path, parsed_url, payload, timestamp):
    """Memproses info industri emiten, sektor, dan kapitalisasi harga."""
    symbol = path.split("/")[2]
    inner_data = payload.get("data", {})
    
    profile_obj = {
        "symbol": symbol,
        "name": inner_data.get("name"),
        "sector": inner_data.get("sector"),
        "sub_sector": inner_data.get("sub_sector"),
        "exchange": inner_data.get("exchange"),
        "country": inner_data.get("country"),
        "created_at": inner_data.get("created"),
        "followers": clean_int(inner_data.get("followers")),
        "price": clean_int(inner_data.get("price"))
    }
    db.insert_company_profile(profile_obj)


def parse_shareholding_composition(db, path, parsed_url, payload, timestamp):
    """Memproses komposisi kepemilikan saham insider per periode."""
    symbol = path.split("/")[-1]
    inner_data = payload.get("data", {})
    
    for period in inner_data.get("periods", []):
        report_date = period.get("report_date")
        compositions = []
        for comp in period.get("compositions", []):
            compositions.append({
                "label": comp.get("label"),
                "shares": clean_int(comp.get("shares", {}).get("raw") if isinstance(comp.get("shares"), dict) else comp.get("shares")),
                "percentage": clean_float(comp.get("percentage", {}).get("raw") if isinstance(comp.get("percentage"), dict) else comp.get("percentage"))
            })
        if compositions and report_date:
            db.insert_company_shareholding_compositions(symbol, report_date, compositions)


def parse_major_holder_movements(db, path, parsed_url, payload, timestamp):
    """Memproses transaksi insider pemegang saham mayoritas (>5%)."""
    inner_data = payload.get("data", {})
    movements = inner_data.get("movement", [])
    
    grouped_movements = {}
    for m in movements:
        sym = m.get("symbol")
        if not sym:
            continue
        if sym not in grouped_movements:
            grouped_movements[sym] = []
        
        grouped_movements[sym].append({
            "name": m.get("name"),
            "date": m.get("date"),
            "previous_value": clean_int(m.get("previous", {}).get("value") if isinstance(m.get("previous"), dict) else m.get("previous")),
            "previous_percentage": clean_float(m.get("previous", {}).get("percentage") if isinstance(m.get("previous"), dict) else m.get("previous_percentage")),
            "current_value": clean_int(m.get("current", {}).get("value") if isinstance(m.get("current"), dict) else m.get("current")),
            "current_percentage": clean_float(m.get("current", {}).get("percentage") if isinstance(m.get("current"), dict) else m.get("current_percentage")),
            "changes_value": clean_int(m.get("changes", {}).get("value") if isinstance(m.get("changes"), dict) else m.get("changes_value")),
            "changes_percentage": clean_float(m.get("changes", {}).get("percentage") if isinstance(m.get("changes"), dict) else m.get("changes_percentage")),
            "action_type": m.get("action_type"),
            "nationality": m.get("nationality"),
            "data_source": m.get("data_source", {}).get("label") if isinstance(m.get("data_source"), dict) else m.get("data_source"),
            "price": clean_int(m.get("price_formatted")),
            "broker_code": m.get("broker_detail", {}).get("code") if isinstance(m.get("broker_detail"), dict) else m.get("broker_code")
        })
        
    for sym, items in grouped_movements.items():
        db.insert_company_insider_transactions(sym, items)


def parse_keystats_and_dividends(db, path, parsed_url, payload, timestamp):
    """Memproses metrik rasio keuangan (Keystats) dan histori dividen emiten."""
    symbol = path.split("/")[-1]
    inner_data = payload.get("data", {})
    
    # Update market cap & enterprise value in profile
    stats = inner_data.get("stats", {})
    profile_obj = {
        "symbol": symbol,
        "market_cap": clean_int(stats.get("market_cap")),
        "enterprise_value": clean_int(stats.get("enterprise_value"))
    }
    db.insert_company_profile(profile_obj)
    
    # Financial metric values
    keystats_list = []
    
    # Basic Valuation etc.
    for fin_group in inner_data.get("closure_fin_items_results", []):
        group_name = fin_group.get("keystats_name")
        for item in fin_group.get("fin_name_results", []):
            fitem = item.get("fitem", {})
            keystats_list.append({
                "year": "Current",
                "period": "TTM" if "(TTM)" in fitem.get("name", "") else "Quarter",
                "metric_name": fitem.get("name"),
                "value": fitem.get("value")
            })
            
    # Historical Net Income, EPS, Revenue
    fin_year_parent = inner_data.get("financial_year_parent", {})
    for group in fin_year_parent.get("financial_year_groups", []):
        metric_name = group.get("fitem_name")
        for yr_val in group.get("financial_year_values", []):
            year = yr_val.get("year")
            if yr_val.get("ttm_value"):
                keystats_list.append({
                    "year": str(year),
                    "period": "TTM",
                    "metric_name": metric_name,
                    "value": yr_val.get("ttm_value")
                })
            if yr_val.get("annualised_value"):
                keystats_list.append({
                    "year": str(year),
                    "period": "Annualised",
                    "metric_name": metric_name,
                    "value": yr_val.get("annualised_value")
                })
            for q_val in yr_val.get("period_values", []):
                keystats_list.append({
                    "year": str(year),
                    "period": q_val.get("period"),
                    "metric_name": metric_name,
                    "value": q_val.get("quarter_value")
                })
    if keystats_list:
        db.insert_company_keystats(symbol, keystats_list)
        
    # Dividends
    div_group = inner_data.get("dividend_group", {})
    dividends = []
    for div_yr in div_group.get("dividend_year_values", []):
        dividends.append({
            "year": clean_int(div_yr.get("period")),
            "dividend": clean_float(div_yr.get("dividend")),
            "ex_date": div_yr.get("ex_date"),
            "payment_date": div_yr.get("payment_date")
        })
    if dividends:
        db.insert_company_dividends(symbol, dividends)


def parse_analyst_ratings(db, path, parsed_url, payload, timestamp):
    """Memproses konsensus rekomendasi analis & target harga saham."""
    symbol = path.split("/")[2]
    inner_data = payload.get("data", {})
    
    rating = {
        "consensus_rating": inner_data.get("recommendation"),
        "target_price": clean_float(inner_data.get("price_target", {}).get("best_target") if isinstance(inner_data.get("price_target"), dict) else None),
        "buy_count": clean_int(inner_data.get("total_buy")),
        "hold_count": clean_int(inner_data.get("total_hold")),
        "sell_count": clean_int(inner_data.get("total_sell")),
        "last_update": inner_data.get("last_updated")
    }
    db.insert_company_analyst_ratings(symbol, rating)


def parse_analyst_consensus(db, path, parsed_url, payload, timestamp):
    """Memproses forecast EPS & Revenue konsensus analis sebagai data keystats."""
    symbol = path.split("/")[2]
    inner_data = payload.get("data", [])
    if isinstance(inner_data, list):
        keystats_list = []
        for metric in inner_data:
            metric_name = metric.get("name")
            for item in metric.get("items", []):
                year = str(item.get("year"))
                is_est = item.get("is_estimate", False)
                period = "Estimate" if is_est else "Actual"
                keystats_list.append({
                    "year": year,
                    "period": period,
                    "metric_name": f"Analyst Consensus {metric_name}",
                    "value": str(item.get("value"))
                })
        if keystats_list:
            db.insert_company_keystats(symbol, keystats_list)
