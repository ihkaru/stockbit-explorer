import os
import logging
from db_manager import StockbitDbManager

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def seed_data(db_path=None):
    db = StockbitDbManager(db_path)
    
    # 1. Seed Broker Profiles
    logging.info("Seeding broker profiles...")
    broker_profiles = [
        # Tier 1 Brokers (Major Players)
        {"code": "BK", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "AK", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "RX", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "KZ", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "MS", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "YU", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "ZP", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "DB", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "CS", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "CG", "retail_density": "LOW", "typical_style": "SWING", "tier": 1},
        {"code": "CC", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 1},
        {"code": "OD", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 1},
        {"code": "YP", "retail_density": "HIGH", "typical_style": "SCALPING", "tier": 1},
        {"code": "PD", "retail_density": "HIGH", "typical_style": "SWING", "tier": 1},
        
        # Tier 2 Brokers (Mid-sized / Regional)
        {"code": "AZ", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "GR", "retail_density": "LOW", "typical_style": "SWING", "tier": 2},
        {"code": "DH", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "CD", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "RB", "retail_density": "LOW", "typical_style": "SWING", "tier": 2},
        {"code": "KI", "retail_density": "LOW", "typical_style": "SWING", "tier": 2},
        {"code": "LG", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "BQ", "retail_density": "LOW", "typical_style": "SWING", "tier": 2},
        {"code": "BS", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "AR", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "IF", "retail_density": "MEDIUM", "typical_style": "SWING", "tier": 2},
        {"code": "SQ", "retail_density": "LOW", "typical_style": "SWING", "tier": 2},
        
        # Retail & Scalping Specialists (MG is prime market maker)
        {"code": "MG", "retail_density": "MEDIUM", "typical_style": "SCALPING", "tier": 2},
        {"code": "CP", "retail_density": "MEDIUM", "typical_style": "SCALPING", "tier": 2},
        {"code": "XC", "retail_density": "HIGH", "typical_style": "SCALPING", "tier": 2},
        {"code": "KK", "retail_density": "HIGH", "typical_style": "SWING", "tier": 2},
        {"code": "NI", "retail_density": "HIGH", "typical_style": "SWING", "tier": 2},
        {"code": "EP", "retail_density": "HIGH", "typical_style": "SWING", "tier": 2},
        {"code": "YZ", "retail_density": "HIGH", "typical_style": "SCALPING", "tier": 2},
        {"code": "AT", "retail_density": "HIGH", "typical_style": "SWING", "tier": 2}
    ]
    
    # First, make sure the brokers are in the table (upsert defaults if they aren't there)
    # The database parser might not have fetched all of them yet
    default_brokers = []
    for p in broker_profiles:
        default_brokers.append({
            "code": p["code"],
            "name": f"Broker {p['code']}",
            "group_type": "Lokal" if p["retail_density"] in ("HIGH", "MEDIUM") else "Asing",
            "color": "#7924c3",
            "membership_type": "MEMBERSHIP_TYPE_EXCHANGE_MEMBER"
        })
    db.insert_brokers(default_brokers)
    
    # Update broker profiles
    updated_brokers = db.update_broker_profiles(broker_profiles)
    logging.info(f"Berhasil mengupdate {updated_brokers} profil broker.")

    # 2. Seed Conglomerates
    logging.info("Seeding conglomerates...")
    congloms = [
        {
            "name": "Djarum Group",
            "owner_name": "Hartono Family",
            "description": "Konglomerasi terbesar di Indonesia, pemilik Bank Central Asia (BBCA), Sarana Menara (TOWR), Blibli (BELI)."
        },
        {
            "name": "Salim Group",
            "owner_name": "Anthony Salim",
            "description": "Konglomerasi pangan terbesar (Indofood), perkebunan (London Sumatra), ritel, otomotif, dan tambang (Amman Mineral)."
        },
        {
            "name": "Sinar Mas Group",
            "owner_name": "Widjaja Family",
            "description": "Konglomerasi pulp & paper (Indah Kiat), properti (Bumi Serpong Damai), telekomunikasi, dan energi/jasa keuangan."
        },
        {
            "name": "MNC Group",
            "owner_name": "Hary Tanoesoedibjo",
            "description": "Konglomerasi media terbesar (MNC Group), jasa keuangan, properti, dan pertambangan."
        },
        {
            "name": "CT Corp",
            "owner_name": "Chairul Tanjung",
            "description": "Konglomerasi ritel modern, media (Trans TV/Detik), perbankan (Bank Mega, Allo Bank), dan properti/wisata."
        },
        {
            "name": "Lippo Group",
            "owner_name": "Riady Family",
            "description": "Konglomerasi properti (Lippo Karawaci), layanan kesehatan (Siloam Hospitals), ritel modern (Matahari), dan teknologi keuangan."
        },
        {
            "name": "Barito Pacific Group",
            "owner_name": "Prajogo Pangestu",
            "description": "Konglomerasi petrokimia (Chandra Asri), energi terbarukan (Barito Renewables), infrastruktur, tambang, dan kontraktor tambang."
        },
        {
            "name": "Bakrie Group",
            "owner_name": "Bakrie Family",
            "description": "Konglomerasi pertambangan batu bara/mineral (Bumi Resources), infrastruktur, media, perkebunan, dan energi."
        },
        {
            "name": "Adaro / Boy Thohir",
            "owner_name": "Garibaldi Thohir & Partners",
            "description": "Konglomerasi energi batu bara, logam mineral, dan jasa investasi keuangan (Trimegah Sekuritas)."
        },
        {
            "name": "Panin Group",
            "owner_name": "Mu'min Ali Gunawan",
            "description": "Konglomerasi perbankan, asuransi, leasing, dan sekuritas terkemuka di Indonesia."
        }
    ]
    db.insert_conglomerates(congloms)

    # 3. Seed Conglomerate Stocks Mappings
    logging.info("Seeding conglomerate stock mappings...")
    conglom_stocks = [
        # Djarum Group
        {"conglomerate_name": "Djarum Group", "symbol": "BBCA"},
        {"conglomerate_name": "Djarum Group", "symbol": "TOWR"},
        {"conglomerate_name": "Djarum Group", "symbol": "BELI"},
        {"conglomerate_name": "Djarum Group", "symbol": "RANC"},
        
        # Salim Group
        {"conglomerate_name": "Salim Group", "symbol": "INDF"},
        {"conglomerate_name": "Salim Group", "symbol": "ICBP"},
        {"conglomerate_name": "Salim Group", "symbol": "LSIP"},
        {"conglomerate_name": "Salim Group", "symbol": "SIMP"},
        {"conglomerate_name": "Salim Group", "symbol": "DNET"},
        {"conglomerate_name": "Salim Group", "symbol": "BINA"},
        {"conglomerate_name": "Salim Group", "symbol": "IMAS"},
        {"conglomerate_name": "Salim Group", "symbol": "DCII"},
        {"conglomerate_name": "Salim Group", "symbol": "AMMN"},
        {"conglomerate_name": "Salim Group", "symbol": "PANI"},
        
        # Sinar Mas Group
        {"conglomerate_name": "Sinar Mas Group", "symbol": "BSDE"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "INKP"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "TKIM"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "DSSA"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "GEMS"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "SMMA"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "SMAR"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "DMAS"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "BSIM"},
        {"conglomerate_name": "Sinar Mas Group", "symbol": "FREN"},
        
        # MNC Group
        {"conglomerate_name": "MNC Group", "symbol": "BHIT"},
        {"conglomerate_name": "MNC Group", "symbol": "BMTR"},
        {"conglomerate_name": "MNC Group", "symbol": "MNCN"},
        {"conglomerate_name": "MNC Group", "symbol": "MSIN"},
        {"conglomerate_name": "MNC Group", "symbol": "IPTV"},
        {"conglomerate_name": "MNC Group", "symbol": "MSKY"},
        {"conglomerate_name": "MNC Group", "symbol": "BCAP"},
        {"conglomerate_name": "MNC Group", "symbol": "BABP"},
        {"conglomerate_name": "MNC Group", "symbol": "KPIG"},
        {"conglomerate_name": "MNC Group", "symbol": "IATA"},
        
        # CT Corp
        {"conglomerate_name": "CT Corp", "symbol": "MEGA"},
        {"conglomerate_name": "CT Corp", "symbol": "BBHI"},
        
        # Lippo Group
        {"conglomerate_name": "Lippo Group", "symbol": "LPKR"},
        {"conglomerate_name": "Lippo Group", "symbol": "SILO"},
        {"conglomerate_name": "Lippo Group", "symbol": "LPPF"},
        {"conglomerate_name": "Lippo Group", "symbol": "MLPL"},
        {"conglomerate_name": "Lippo Group", "symbol": "NOBU"},
        {"conglomerate_name": "Lippo Group", "symbol": "LPCK"},
        {"conglomerate_name": "Lippo Group", "symbol": "LPGI"},
        {"conglomerate_name": "Lippo Group", "symbol": "MPPA"},
        
        # Barito Pacific Group
        {"conglomerate_name": "Barito Pacific Group", "symbol": "BRPT"},
        {"conglomerate_name": "Barito Pacific Group", "symbol": "TPIA"},
        {"conglomerate_name": "Barito Pacific Group", "symbol": "CUAN"},
        {"conglomerate_name": "Barito Pacific Group", "symbol": "BREN"},
        {"conglomerate_name": "Barito Pacific Group", "symbol": "PTRO"},
        {"conglomerate_name": "Barito Pacific Group", "symbol": "GZCO"},
        
        # Bakrie Group
        {"conglomerate_name": "Bakrie Group", "symbol": "BNBR"},
        {"conglomerate_name": "Bakrie Group", "symbol": "BUMI"},
        {"conglomerate_name": "Bakrie Group", "symbol": "BRMS"},
        {"conglomerate_name": "Bakrie Group", "symbol": "UNSP"},
        {"conglomerate_name": "Bakrie Group", "symbol": "ELTY"},
        {"conglomerate_name": "Bakrie Group", "symbol": "ENRG"},
        {"conglomerate_name": "Bakrie Group", "symbol": "DEWA"},
        {"conglomerate_name": "Bakrie Group", "symbol": "VIVA"},
        {"conglomerate_name": "Bakrie Group", "symbol": "MDIA"},
        
        # Adaro / Boy Thohir
        {"conglomerate_name": "Adaro / Boy Thohir", "symbol": "ADRO"},
        {"conglomerate_name": "Adaro / Boy Thohir", "symbol": "ADMR"},
        {"conglomerate_name": "Adaro / Boy Thohir", "symbol": "MBMA"},
        {"conglomerate_name": "Adaro / Boy Thohir", "symbol": "ESSA"},
        
        # Panin Group
        {"conglomerate_name": "Panin Group", "symbol": "PADI"},
        {"conglomerate_name": "Panin Group", "symbol": "PNLF"},
        {"conglomerate_name": "Panin Group", "symbol": "PNIN"},
        {"conglomerate_name": "Panin Group", "symbol": "PANS"},
        {"conglomerate_name": "Panin Group", "symbol": "PNBN"}
    ]
    db.insert_conglomerate_stocks(conglom_stocks)

    # 4. Seed Conglomerate Brokers Mappings
    logging.info("Seeding conglomerate broker mappings...")
    conglom_brokers = [
        {"conglomerate_name": "Djarum Group", "broker_code": "SQ"}, # BCA Sekuritas
        {"conglomerate_name": "Salim Group", "broker_code": "RB"},  # Ina Sekuritas
        {"conglomerate_name": "Sinar Mas Group", "broker_code": "DH"}, # Sinarmas Sekuritas
        {"conglomerate_name": "MNC Group", "broker_code": "EP"},    # MNC Sekuritas
        {"conglomerate_name": "CT Corp", "broker_code": "CD"},      # Mega Capital
        {"conglomerate_name": "Lippo Group", "broker_code": "KI"},   # Ciptadana Sekuritas
        {"conglomerate_name": "Adaro / Boy Thohir", "broker_code": "LG"}, # Trimegah Sekuritas
        {"conglomerate_name": "Panin Group", "broker_code": "GR"}   # Panin Sekuritas
    ]
    db.insert_conglomerate_brokers(conglom_brokers)

    # 5. Seed MSCI Index Tracker
    logging.info("Seeding MSCI tracker constituents (May/June 2026 update)...")
    msci_stocks = [
        # Active Constituents (MSCI Global Standard)
        {"symbol": "BBCA", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "BBRI", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "BMRI", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "BBNI", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "BRIS", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "TLKM", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "GOTO", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "ICBP", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "INDF", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "UNVR", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "ADRO", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "UNTR", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "PTBA", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "MDKA", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "ASII", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "SMGR", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "KLBF", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "CPIN", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        {"symbol": "CTRA", "index_type": "GLOBAL_STANDARD", "status": "ACTIVE", "effective_date": "2026-06-25"},
        
        # Active Constituents (MSCI Small Cap)
        {"symbol": "AMRT", "index_type": "SMALL_CAP", "status": "ACTIVE", "effective_date": "2026-05-31"},
        
        # Deleted Constituents (May 2026 Rebalancing)
        {"symbol": "AMMN", "index_type": "GLOBAL_STANDARD", "status": "DELETED", "effective_date": "2026-05-31"},
        {"symbol": "BREN", "index_type": "GLOBAL_STANDARD", "status": "DELETED", "effective_date": "2026-05-31"},
        {"symbol": "TPIA", "index_type": "GLOBAL_STANDARD", "status": "DELETED", "effective_date": "2026-05-31"},
        {"symbol": "DSSA", "index_type": "GLOBAL_STANDARD", "status": "DELETED", "effective_date": "2026-05-31"},
        {"symbol": "CUAN", "index_type": "GLOBAL_STANDARD", "status": "DELETED", "effective_date": "2026-05-31"}
    ]
    db.insert_msci_stocks(msci_stocks)
    
    # 6. Seed Trading Preferences (Swing Trader Focus)
    logging.info("Seeding trading preferences...")
    preferences = [
        {
            "strategy_name": "REMORA_SWING",
            "max_entry_premium_pct": 0.05,       # Maksimal 5% di atas modal bandar
            "stop_loss_buffer_pct": 0.04,        # Batas stop loss 4% di bawah modal bandar
            "risk_reward_ratio": 2.5,            # Target profit multiplier 2.5x dari risk
            "min_haka_ratio": 0.60,              # Minimal rasio HAKA 60%
            "min_smart_money_score": 1000.0,     # Minimal skor lot institusi
            "max_portfolio_allocation": 0.20     # Maksimal alokasi modal 20%
        }
    ]
    db.insert_trading_preferences(preferences)
    
    logging.info("Seeding data berhasil diselesaikan!")

if __name__ == "__main__":
    seed_data()
