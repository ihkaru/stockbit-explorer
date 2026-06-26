from typing import List, Optional
from .models import TradeTick, VolumeCategory, SLotGroup, HAKAHAKIResult
from .config import VOLUME_THRESHOLD, SIGNAL_THRESHOLD, MIN_TRADE_COUNT

class SignalEngine:
    """Mesin kalkulasi sinyal trading berdasarkan HAKA/HAKI, volume pelaku, S-Lot, dan status broker."""
    
    def __init__(
        self,
        conglomerate_stocks: dict,
        conglomerate_brokers: dict,
        msci_tracker: dict,
        swing_pref: dict
    ):
        self.conglomerate_stocks = conglomerate_stocks
        self.conglomerate_brokers = conglomerate_brokers
        self.msci_tracker = msci_tracker
        self.swing_pref = swing_pref

    def categorize_volume(self, lot: float) -> str:
        """Mengkategorikan satu transaksi berdasarkan jumlah lot."""
        if lot < VOLUME_THRESHOLD["kakap"][0]:
            return "semut"
        elif lot < VOLUME_THRESHOLD["hiu"][0]:
            return "kakap"
        elif lot < VOLUME_THRESHOLD["paus"][0]:
            return "hiu"
        else:
            return "paus"

    def detect_s_lots(self, trades: List[TradeTick]) -> List[SLotGroup]:
        """
        Mendeteksi S-Lot (split order) dari bandar berdasarkan group_order_number.
        
        Logika: Transaksi yang berbeda tapi memiliki group_order_number yang sama
        adalah pecahan dari satu order besar yang sengaja dipecah menjadi lot kecil.
        Hanya grup dengan >= 3 transaksi yang dianggap S-Lot signifikan.
        """
        groups = {}
        
        for t in trades:
            gon = t.group_order_number
            if not gon or gon == "0" or gon == "":
                continue
            
            key = f"{gon}_{t.symbol}_{t.action}"
            if key not in groups:
                groups[key] = {
                    "group_order_number": gon,
                    "symbol": t.symbol,
                    "action": t.action,
                    "ticks": [],
                    "broker": t.buyer_broker if t.action == "B" else t.seller_broker
                }
            groups[key]["ticks"].append(t)
        
        s_lot_list = []
        for key, g in groups.items():
            ticks = g["ticks"]
            if len(ticks) < 3:  # Minimal 3 pecahan untuk dianggap S-Lot
                continue
            
            total_lot = sum(t.lot for t in ticks)
            total_value = sum(t.value for t in ticks)
            avg_price = total_value / (total_lot * 100) if total_lot > 0 else 0
            
            s_lot_list.append(SLotGroup(
                group_order_number=g["group_order_number"],
                symbol=g["symbol"],
                action=g["action"],
                total_lot=total_lot,
                total_value=total_value,
                tick_count=len(ticks),
                avg_price=round(avg_price),
                first_time=ticks[0].time_str,
                last_time=ticks[-1].time_str,
                broker=g["broker"]
            ))
        
        # Urutkan berdasarkan total_lot terbesar
        s_lot_list.sort(key=lambda x: x.total_lot, reverse=True)
        return s_lot_list

    def _tally_volume_categories(self, trades: List[TradeTick], result: HAKAHAKIResult) -> None:
        """Menghitung total HAKA/HAKI dan porsi volume per kategori pelaku."""
        vc = VolumeCategory()
        for t in trades:
            category = self.categorize_volume(t.lot)
            is_buy = t.action == "B"
            
            # Akumulasi (HAKA)
            if is_buy:
                result.haka_lot += t.lot
                result.haka_value += t.value
                result.haka_count += 1
            # Distribusi (HAKI)
            else:
                result.haki_lot += t.lot
                result.haki_value += t.value
                result.haki_count += 1
            
            # Volume per kategori
            if category == "semut":
                vc.semut_count += 1
                if is_buy:
                    vc.semut_buy_lot += t.lot
                else:
                    vc.semut_sell_lot += t.lot
            elif category == "kakap":
                vc.kakap_count += 1
                if is_buy:
                    vc.kakap_buy_lot += t.lot
                else:
                    vc.kakap_sell_lot += t.lot
            elif category == "hiu":
                vc.hiu_count += 1
                if is_buy:
                    vc.hiu_buy_lot += t.lot
                else:
                    vc.hiu_sell_lot += t.lot
            else:  # paus
                vc.paus_count += 1
                if is_buy:
                    vc.paus_buy_lot += t.lot
                else:
                    vc.paus_sell_lot += t.lot
        result.volume_category = vc

    def _score_smart_money(self, trades: List[TradeTick]) -> float:
        """Menghitung Smart Money Score berdasarkan retail density broker pengeksekusi."""
        score = 0.0
        for t in trades:
            is_buy = t.action == "B"
            if is_buy:
                if t.buyer_retail_density == "LOW":
                    score += t.lot
                elif t.buyer_retail_density == "HIGH":
                    score -= t.lot * 0.5
            else:
                if t.seller_retail_density == "LOW":
                    score -= t.lot
                elif t.seller_retail_density == "HIGH":
                    score += t.lot * 0.5
        return score

    def _detect_insider_activity(self, conglomerate_name: Optional[str], trades: List[TradeTick]) -> List[str]:
        """Mendeteksi transaksi insider dari broker yang satu konglomerasi dengan emiten."""
        if not conglomerate_name:
            return []
        details = []
        for t in trades:
            is_buy = t.action == "B"
            # Check buyer
            buyer_conglom = self.conglomerate_brokers.get(t.buyer_broker.upper())
            if buyer_conglom == conglomerate_name and is_buy:
                detail = f"Beli {t.lot:.1f} lot @ Rp {t.price:,} via Broker Grup {t.buyer_broker} ({t.time_str})"
                details.append(detail)
            # Check seller
            seller_conglom = self.conglomerate_brokers.get(t.seller_broker.upper())
            if seller_conglom == conglomerate_name and not is_buy:
                detail = f"Jual {t.lot:.1f} lot @ Rp {t.price:,} via Broker Grup {t.seller_broker} ({t.time_str})"
                details.append(detail)
        return sorted(list(set(details)))

    def _detect_msci_flow(self, is_msci_stock: bool, trades: List[TradeTick]) -> List[str]:
        """Mendeteksi transaksi rebalancing MSCI besar di sesi penutupan."""
        if not is_msci_stock:
            return []
        details = []
        for t in trades:
            if t.time_str >= "16:00:00":
                category = self.categorize_volume(t.lot)
                if category in ("hiu", "paus"):
                    is_buy = t.action == "B"
                    act_str = "BELI (HAKA)" if is_buy else "JUAL (HAKI)"
                    detail = f"MSCI Flow {act_str} {t.lot:.1f} lot @ Rp {t.price:,} via {t.buyer_broker if is_buy else t.seller_broker} ({t.time_str})"
                    details.append(detail)
        return sorted(list(set(details)))

    def _compute_swing_plan(self, result: HAKAHAKIResult, multi_day_buyers: Optional[List[dict]]) -> None:
        """Menghitung cheap entry zone, target profit, dan stop loss berdasarkan modal bandar."""
        if not multi_day_buyers:
            return
            
        top_acc = multi_day_buyers[0]
        result.bandar_avg_price = top_acc["avg_price"]
        
        pref = self.swing_pref
        result.cheap_entry_high = result.bandar_avg_price * (1 + pref["max_entry_premium_pct"])
        result.stop_loss = result.bandar_avg_price * (1 - pref["stop_loss_buffer_pct"])
        
        risk = result.last_price - result.stop_loss
        if risk > 0:
            result.take_profit = result.last_price + (risk * pref["risk_reward_ratio"])
        else:
            result.take_profit = result.last_price * (1 + 0.10)
            
        if result.last_price < result.stop_loss:
            result.swing_invalidation_flag = True

    def _generate_signal(self, result: HAKAHAKIResult) -> HAKAHAKIResult:
        """Menghasilkan sinyal trading akhir dengan booster dan filter retail FOMO."""
        if result.analysis_window < MIN_TRADE_COUNT:
            result.signal = "INSUFFICIENT_DATA"
            result.signal_strength = "NONE"
            return result
        
        ratio = result.haka_ratio
        vc = result.volume_category
        
        # Deteksi dominasi Smart Money (Paus & Hiu)
        smart_money_buy = vc.paus_buy_lot + vc.hiu_buy_lot
        smart_money_sell = vc.paus_sell_lot + vc.hiu_sell_lot
        smart_money_total = smart_money_buy + smart_money_sell
        smart_money_buy_ratio = (smart_money_buy / smart_money_total) if smart_money_total > 0 else 0.5
        
        # Sinyal dasar HAKA ratio
        if ratio >= SIGNAL_THRESHOLD["strong_buy"]:
            result.signal = "BUY"
            result.signal_strength = "STRONG"
        elif ratio >= SIGNAL_THRESHOLD["buy"]:
            result.signal = "BUY"
            result.signal_strength = "MODERATE"
        elif ratio <= SIGNAL_THRESHOLD["strong_sell"]:
            result.signal = "SELL"
            result.signal_strength = "STRONG"
        elif ratio <= SIGNAL_THRESHOLD["sell"]:
            result.signal = "SELL"
            result.signal_strength = "MODERATE"
        else:
            result.signal = "NEUTRAL"
            result.signal_strength = "WEAK"
        
        # Booster 1: Dominasi Smart Money berlawanan arah
        if result.signal == "NEUTRAL" and smart_money_buy_ratio >= 0.65:
            result.signal = "BUY"
            result.signal_strength = "WEAK"
        elif result.signal == "NEUTRAL" and smart_money_buy_ratio <= 0.35:
            result.signal = "SELL"
            result.signal_strength = "WEAK"
            
        # Booster 2: Penyelarasan Kualitas Broker (Smart Money Score)
        if result.signal == "BUY" and result.smart_money_score < 0:
            result.signal = "NEUTRAL"
            result.signal_strength = "WEAK (RETAIL FOMO)"
        elif result.signal == "NEUTRAL" and result.smart_money_score > 2000:
            result.signal = "BUY"
            result.signal_strength = "MODERATE (INSTITUTIONAL ACCUMULATION)"
        
        # Booster S-Lot
        if result.s_lot_groups:
            buy_s_lots = [sg for sg in result.s_lot_groups if sg.action == "B"]
            if buy_s_lots and result.signal == "BUY":
                result.signal_strength = "STRONG"
        
        return result

    def compute(self, symbol: str, trades: List[TradeTick], multi_day_buyers: Optional[List[dict]] = None) -> HAKAHAKIResult:
        """Metode orkestrator utama untuk menghitung analisis Tape Reading lengkap."""
        result = HAKAHAKIResult(symbol=symbol, analysis_window=len(trades))
        
        if not trades:
            return result
            
        # 1. Conglomerate & MSCI metadata
        sym_upper = symbol.upper()
        if sym_upper in self.conglomerate_stocks:
            result.conglomerate_name = self.conglomerate_stocks[sym_upper]
        if sym_upper in self.msci_tracker:
            idx_type, status = self.msci_tracker[sym_upper]
            result.is_msci_stock = True
            result.msci_index_type = idx_type
            result.msci_status = status
            
        # 2. Tally Volume and Actions
        self._tally_volume_categories(trades, result)
        
        # 3. Last price and price bounds
        prices = [t.price for t in trades]
        result.last_price = trades[-1].price
        result.price_range_high = max(prices)
        result.price_range_low = min(prices)
        
        # 4. HAKA Ratio
        total_lot = result.haka_lot + result.haki_lot
        if total_lot > 0:
            result.haka_ratio = result.haka_lot / total_lot
            
        # 5. Smart Money Score
        result.smart_money_score = self._score_smart_money(trades)
        
        # 6. Insider activities
        insider = self._detect_insider_activity(result.conglomerate_name, trades)
        if insider:
            result.insider_activity_detected = True
            result.insider_activity_details = insider
            
        # 7. MSCI rebalancing flow
        msci = self._detect_msci_flow(result.is_msci_stock, trades)
        if msci:
            result.msci_flow_detected = True
            result.msci_flow_details = msci
            
        # 8. S-Lots
        result.s_lot_groups = self.detect_s_lots(trades)
        result.total_s_lot = sum(g.total_lot for g in result.s_lot_groups)
        
        # 9. Swing execution plan
        self._compute_swing_plan(result, multi_day_buyers)
        
        # 10. Final signal generation
        result = self._generate_signal(result)
        
        return result
