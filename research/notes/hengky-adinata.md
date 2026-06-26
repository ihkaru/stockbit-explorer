# Metodologi Hengky Adinata — Dokumentasi Detail
> Dokumen ini melengkapi README proyek Stockbit Explorer dengan aspek-aspek metodologi
> yang belum tercakup, berdasarkan riset publik dari podcast, kursus, dan komunitas Remora Trader.

---

## Daftar Isi
1. [Filosofi Remora](#1-filosofi-remora)
2. [Mental Trading Framework](#2-mental-trading-framework)
3. [Konsep Moonstock & Screening](#3-konsep-moonstock--screening)
4. [Fake Wall vs Real Accumulation Detection](#4-fake-wall-vs-real-accumulation-detection)
5. [Broker Summary Post-Market (Detail)](#5-broker-summary-post-market-detail)
6. [Dinamika Market Maker](#6-dinamika-market-maker)
7. [Distribusi Detection (Konkret)](#7-distribusi-detection-konkret)

---

## 1. Filosofi Remora

### Konsep Dasar

Remora Trader mengambil nama dari **ikan remora** (*Remora remora*) — ikan kecil yang menempel
pada tubuh hiu untuk ikut makan dari sisa mangsanya. Filosofi ini bukan sekadar nama komunitas;
ia adalah **prinsip operasional** yang menentukan bagaimana trader memilih saham, kapan masuk,
dan kapan keluar.

```
IKAN HIU  =  Smart Money / Market Maker / Pelaku Besar
IKAN REMORA  =  Trader Retail yang mengikuti
```

### Implikasi Praktis

| Prinsip | Artinya dalam Eksekusi |
|---|---|
| **Tidak menjadi market mover** | Jangan masuk saham sepi yang "akan digerakkan sendiri" |
| **Ikuti yang sudah punya pemain** | Cari tanda kehadiran pelaku besar terlebih dahulu |
| **Makan dari sisa mangsa** | Entry setelah akumulasi terdeteksi, bukan spekulasi sebelumnya |
| **Lepas sebelum hiu berbalik** | Exit sebelum/saat distribusi dimulai, bukan menunggu puncak |

### Konsekuensi terhadap Seleksi Saham

Filosofi remora secara langsung **mengeliminasi kategori saham berikut** dari watchlist:

- Saham tanpa tanda aktivitas pelaku besar (volume flat, spread tipis, running trade sepi)
- Saham yang sedang tidak ada "pemain aktif" meski fundamentalnya bagus
- Saham yang pemainnya sudah terlalu obvious dan harga sudah naik jauh

Ini berbeda secara fundamental dari pendekatan value investing maupun TA murni — **kehadiran
pelaku besar adalah syarat pertama**, bukan syarat terakhir.

---

## 2. Mental Trading Framework

### Mengapa Mental Didahulukan

Hengky secara konsisten menempatkan aspek psikologi **di atas** teknik analisis. Alasannya logis:
teknik analisis bisa dipelajari dalam hitungan minggu, tapi kegagalan eksekusi hampir selalu
bersumber dari kondisi mental yang buruk.

### Framework Rules: "Kapan Masuk, Kapan Salah, Kapan Keluar"

Hengky menegaskan bahwa **all-in hanya masuk akal jika 3 rules ini sudah terdefinisi**
sebelum posisi dibuka:

```
┌─────────────────────────────────────────────────────────┐
│  RULES WAJIB SEBELUM EKSEKUSI                           │
├─────────────────────────────────────────────────────────┤
│  1. Entry Rule    : Kondisi apa yang membuat kita masuk │
│  2. Invalidation  : Kondisi apa yang berarti thesis     │
│                     kita salah → cut loss WAJIB         │
│  3. Exit Rule     : Target profit dan/atau kondisi      │
│                     keluar dari posisi menang           │
└─────────────────────────────────────────────────────────┘

Jika belum ada 3 rules ini → itu SPEKULASI, bukan STRATEGI.
```

### Anti-Pattern: Revenge Trading

**Revenge trading** adalah kondisi di mana trader yang baru rugi langsung masuk posisi baru
dengan motivasi "balik modal". Ini adalah pola yang paling sering menghancurkan akun.

```
Siklus Revenge Trading:
  Rugi → Emosi naik → Entry impulsif → Rugi lebih besar
       ↑______________________________________________↓
```

**Solusi Hengky:** Buat aturan eksplisit: setelah cut loss, ada *cooling period* wajib
(misal 30 menit, atau sampai ada setup baru yang valid), bukan langsung masuk lagi.

### "Playing Survival Mode": Kapan TIDAK Trading

Ini adalah konsep yang sering dilewatkan. Hengky secara eksplisit mengajarkan bahwa
**menghindari pasar adalah keputusan strategis yang valid**, bukan kelemahan.

Kondisi yang memerlukan survival mode:

```
KONDISI PASAR                        REKOMENDASI
─────────────────────────────────    ──────────────────────────────
Market sangat fluktuatif/irasional   Step aside — tidak ada trade
IHSG dalam tren turun kuat           Defensif, kurangi ukuran posisi
Capital outflow deras (asing keluar) Tunggu stabilisasi
Uncertainty geopolitik tinggi        Modal kecil-menengah: jangan agresif
```

> "Lebih baik tidak trading daripada maksa trading dan sumbang donasi ke market."
> — Hengky Adinata

### Objektivitas saat Posisi Merugi

Kunci objektivitas menurut Hengky:

- **Fokus pada kondisi saat ini**, bukan harga rata-rata (average) posisi kita
- Jika smart money berhenti akumulasi dan mulai distribusi → cut loss **tanpa negosiasi**,
  terlepas dari berapa kerugian yang sudah ada
- Mental sudah jatuh = kehilangan keberanian untuk masuk ulang ketika pasar membaik
  → kerugian ganda (nominal + missed opportunity)

---

## 3. Konsep Moonstock & Screening

### Definisi Moonstock

**Moonstock** adalah label untuk saham-saham dalam watchlist Remora yang memenuhi kriteria
"berpotensi naik signifikan karena ada pelaku besar yang sedang atau akan menggerakkan harga."

Moonstock bukan prediksi harga — ia adalah **daftar kandidat** yang sudah lolos filter awal
sebelum dilakukan tape reading lebih dalam.

### Alur Screening Menuju Moonstock

```
UNIVERSE SAHAM (semua emiten BEI)
          │
          ▼
┌─────────────────────────┐
│  FILTER 1: LIKUIDITAS   │
│  - Volume harian cukup  │
│  - Spread tidak terlalu │
│    lebar                │
│  - Bukan FCA/PPK        │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  FILTER 2: AKTIVITAS    │
│  PELAKU BESAR           │
│  - Ada broker dominan   │
│    di summary           │
│  - Akumulasi terdeteksi │
│    di area harga murah  │
│  - Frekuensi transaksi  │
│    jumbo meningkat      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  FILTER 3: POSISI HARGA │
│  - Harga di area        │
│    accumulation zone    │
│    (bukan sudah naik    │
│    jauh / overbought)   │
│  - Risk/reward masuk    │
│    akal secara teknikal │
└────────────┬────────────┘
             │
             ▼
         MOONSTOCK
    (masuk watchlist aktif)
```

### "The Math of Stock Market"

Dari kurikulum Remora, ada konsep matematis yang mendasari pemilihan Moonstock:

- **Asymmetric risk/reward:** Entry di area akumulasi → potensi gain jauh lebih besar
  dari potensi loss ke titik invalidasi
- **Probability weighting:** Kehadiran pelaku besar secara statistik meningkatkan
  probabilitas harga naik (bukan jaminan, tapi edge yang terukur)
- **Position sizing:** Ukuran posisi disesuaikan dengan keyakinan setup, bukan flat

### Implikasi untuk Sistem Otomatis

Dalam konteks project ini, Moonstock screening bisa diautomasi dengan:

```
Input harian (EOD):
  - Broker summary per saham
  - Volume anomaly detection
  - Price zone analysis (apakah di area base/sideways?)

Output:
  - Daftar kandidat moonstock dengan skor confidence
  - Flag: "accumulation detected at low price zone"
```

---

## 4. Fake Wall vs Real Accumulation Detection

### Problem: Bid Tebal Bisa Menipu

Ini adalah salah satu jebakan paling umum dalam tape reading. Bid order besar di orderbook
**tidak otomatis berarti ada pembeli kuat** — bisa jadi itu adalah *fake wall* yang sengaja
dipasang untuk menarik retail masuk, lalu dicabut.

```
SKENARIO FAKE WALL:

Orderbook terlihat:
  Bid 3180: 50.000 lot  ←── terlihat "kuat" → retail ikut beli

Apa yang terjadi:
  Retail masuk → 50.000 lot bid langsung dicabut →
  harga tidak ada penopangnya → turun
  Retail: ketinggalan / cut loss
  Pelaku: dapat sell di harga tinggi
```

### Cara Membedakan Fake Wall vs Real Accumulation

#### Indikator Real Accumulation

```
1. BID TERISI, BUKAN CUMA DIPAJANG
   - Cek running trade: apakah lot besar benar-benar di-HAKI?
   - Real: offer dimakan agresif, bid pindah naik setelah terisi
   - Fake: bid tebal tapi tidak ada transaksi terjadi di sana

2. POLA "SEKALI HAJAR — BID NAIK"
   Ciri naik:
     offer dimakan → lot besar → sekali hajar
     → offer habis → pindah ke harga lebih tinggi
     → bid baru muncul di harga sebelumnya (support baru)

3. LOT BESAR DI ATAS ANTRIAN BID
   Dari pengajaran Hengky:
   "Cek antrian bid — kalau lot besar ada di atas (harga tinggi)
    dan sudah sebagian besar match → itu pertanda kuat."
   Ini karena pelaku besar tidak mau terlalu obvious pasang
   di lot terbawah.

4. KONFIRMASI DARI DONE SUMMARY
   - S-Lot besar di harga tertentu = banyak yang beli di offer
     (agresif, tidak mau nunggu)
   - Pola konsisten lintas beberapa candlestick = bukan fluke
```

#### Indikator Fake Wall / Distribusi Terselubung

```
1. OFFER DIISI ULANG TERUS (NETTING)
   - Offer kecil dimakan → langsung diisi ulang oleh offer baru
   - Pelaku sedang jualan secara bertahap
   - Harga naik tapi volume offer tidak berkurang

2. BID BESAR MUNCUL LALU HILANG SEBELUM TERISI
   - Waktu pasang ke waktu cabut sangat singkat
   - Tidak ada transaksi di harga bid tersebut
   - Ini adalah "fake support"

3. SPREAD MELEBAR MENDADAK
   - Pelaku sedang mengurangi exposure
   - Bid-offer gap membesar = likuiditas ditarik

4. VOLUME NAIK TAPI HARGA STAGNAN
   - Distribusi halus: pelaku jual ke retail yang beli
   - Harga ditahan agar tidak jatuh sebelum semua barang terdistribusi
```

### Tabel Cepat: Identifikasi Pola

| Sinyal | Real Accumulation | Fake Wall / Distribusi |
|---|---|---|
| Bid tebal | Terisi (ada transaksi) | Dicabut sebelum terisi |
| Cara makan offer | Lot besar, sekali hajar | Lot kecil, bertahap, diisi ulang |
| Setelah offer habis | Bid naik (support baru terbentuk) | Offer muncul lagi di harga sama |
| S-Lot di done summary | Besar, konsisten | Kecil atau tidak beraturan |
| Pergerakan harga | Naik berkelanjutan | Naik lalu koreksi tajam |

---

## 5. Broker Summary Post-Market (Detail)

### Mengapa EOD Broker Summary Penting

Sejak regulasi **Kode Broker Masking** berlaku, data broker real-time tidak tersedia saat jam
bursa. Namun setelah market tutup, **Broker Summary harian tersedia penuh** — ini adalah
sumber informasi terpenting untuk konfirmasi siapa yang benar-benar akumulasi atau distribusi.

### Komponen Broker Summary yang Dianalisis

```
┌──────────────────────────────────────────────────────────────┐
│  BROKER SUMMARY  (per saham, per hari)                       │
├──────────────┬───────────┬───────────┬──────────────────────┤
│  Kode Broker │  Net Buy  │  Net Sell │  Keterangan          │
├──────────────┼───────────┼───────────┼──────────────────────┤
│  YP (Indo)   │ +50.000   │           │  Net Buyer           │
│  CC (Mandiri)│           │ -30.000   │  Net Seller          │
│  BK (JP Mor) │ +80.000   │           │  Net Buyer Dominan   │
│  GR (Trimega)│ +10.000   │           │  Ikut akumulasi?     │
└──────────────┴───────────┴───────────┴──────────────────────┘
```

### Konsep AK (Akumulator) dan BK (Broker Kunci)

```
AK = Broker Akumulator
     → Net buyer signifikan selama beberapa hari berturut-turut
     → Posisi average-nya bisa diestimasi dari harga rata-rata
       transaksi mereka selama periode akumulasi

BK = Broker Kunci (yang paling dominan menggerakkan saham)
     → Biasanya 1-2 broker dengan volume terbesar
     → Ketika BK mulai switch ke net sell → sinyal distribusi

SIGNAL KUAT AKUMULASI:
  AK/BK konsisten net buy selama 3-5+ hari
  → Average price mereka bisa jadi support kuat
  → Entry di atas average price mereka = risk terkelola

SIGNAL DISTRIBUSI:
  AK/BK yang sebelumnya net buy mulai buang barang ke ritel
  → Khususnya saat harga sideways (tidak obvious ke ritel)
  → "Jangan cuma senang lihat harga naik, lihat siapa yang
     sedang jualan di balik layar"
```

### Menghitung Estimated Average Price Pelaku Besar

```python
# Pseudocode: estimasi harga rata-rata broker akumulator
# dari data broker summary harian

def estimate_broker_avg_price(broker_daily_data):
    """
    broker_daily_data: list of {date, net_lot, vwap_harian}
    Hanya ambil hari-hari di mana broker adalah net buyer
    """
    total_lot = 0
    total_value = 0

    for day in broker_daily_data:
        if day['net_lot'] > 0:  # hari net buy
            total_lot   += day['net_lot']
            total_value += day['net_lot'] * day['vwap_harian']

    if total_lot == 0:
        return None

    return total_value / total_lot  # estimated average entry price
```

Harga rata-rata estimasi ini dipakai sebagai:
- **Support kuat:** pelaku besar cenderung defend posisinya di area ini
- **Stop loss referensi:** break signifikan di bawah area ini = thesis batal

### Framework Analisis EOD untuk Sistem

```
SETIAP HARI SETELAH MARKET TUTUP:

1. Download broker summary semua saham di watchlist
2. Update tabel akumulasi kumulatif per broker per saham
3. Hitung:
   - Net change hari ini vs kemarin (apakah akselerasi?)
   - Estimated average entry price akumulator
   - Jumlah hari akumulasi berturut-turut
4. Flag:
   - "Akumulasi kuat (X hari berturut)"
   - "AK mulai distribusi" (net sell setelah periode net buy panjang)
   - "Broker baru masuk besar-besaran"
5. Update skor Moonstock kandidat
```

---

## 6. Dinamika Market Maker

### Siapa Market Maker dalam Konteks Ini

Market maker (MM) dalam konteks saham Indonesia merujuk pada dua entitas berbeda:

1. **Official Market Maker:** Broker yang ditunjuk emiten untuk menjaga likuiditas saham
   (terutama saham mid-small cap yang kurang likuid)
2. **Informal "Bandar":** Pelaku dengan modal besar yang mengakumulasi lalu mendistribusikan
   saham secara terencana untuk profit

Hengky membahas keduanya, tapi yang paling relevan secara taktis adalah tipe kedua.

### Siklus Operasi Market Maker

```
FASE 1: AKUMULASI (harga rendah / sideways)
  ┌─────────────────────────────────────────────────┐
  │ MM beli secara bertahap                         │
  │ - Harga dijaga agar tidak naik terlalu cepat    │
  │   (agar bisa beli lebih banyak di harga murah)  │
  │ - Volume mulai meningkat tapi tidak dramatis    │
  │ - Retail belum banyak yang tertarik             │
  └─────────────────────────────────────────────────┘
            ↓ (akumulasi cukup)
FASE 2: MARKUP (harga naik)
  ┌─────────────────────────────────────────────────┐
  │ MM mulai dorong harga naik                      │
  │ - Volume meledak, attention dari retail         │
  │ - FOMO (fear of missing out) terjadi            │
  │ - Target MM: 150% - 200% dari harga akumulasi   │
  │   ("Dia tarik 200% karena dia butuh ruang       │
  │    untuk jual turun")                           │
  └─────────────────────────────────────────────────┘
            ↓ (target tercapai)
FASE 3: DISTRIBUSI (harga tinggi)
  ┌─────────────────────────────────────────────────┐
  │ MM jual ke retail yang baru FOMO masuk          │
  │ - Harga mungkin masih naik sedikit atau sideways│
  │ - Volume tetap tinggi (tapi sekarang MM jual)   │
  │ - "Retail jadi exit liquidity"                  │
  └─────────────────────────────────────────────────┘
            ↓ (barang habis terdistribusi)
FASE 4: MARKDOWN
  ┌─────────────────────────────────────────────────┐
  │ Tidak ada lagi yang menopang harga              │
  │ - Harga turun, retail panik                     │
  │ - MM mungkin mulai akumulasi lagi di bawah      │
  └─────────────────────────────────────────────────┘
```

### Mengapa Market Maker Bisa Gagal

Hengky secara terbuka membahas ini — dan penting karena menjelaskan ketidakpastian yang
inherent dalam strategi mengikuti MM:

```
KEGAGALAN MM TERJADI KETIKA:

1. KESERAKAHAN: harga dinaikkan terlalu tinggi (misal 50 → 500)
   tanpa memberi retail ruang untuk untung terlebih dahulu
   → Retail tidak mau masuk karena sudah terlalu mahal
   → MM tidak bisa distribusi → terjebak dengan posisinya sendiri

2. TIDAK ADA PARTISIPASI RETAIL:
   → MM sering pakai influencer/buzzer untuk menarik retail
   → Jika tetap tidak ada yang mau beli → MM terpaksa jual rugi

3. MARKET CONDITION BERUBAH:
   → Sentimen makro berubah mendadak (news, kebijakan)
   → Capital outflow masif (asing keluar)
   → MM tidak bisa counter tekanan jual sebesar itu
```

### Implikasi Strategis untuk Trader Remora

```
KAPAN REMORA IKUT:
  ✓ Fase akumulasi terdeteksi (harga masih rendah/sideways)
  ✓ Ada tanda-tanda markup akan dimulai (volume naik, bid agresif)
  ✓ Risk/reward masih favorable

KAPAN REMORA KELUAR:
  ✓ Tanda distribusi pertama muncul — tidak perlu tunggu puncak
  ✓ MM berhenti defend harga di area support mereka
  ✓ "Jika smart money berbalik arah, langsung cut loss"
  ✗ JANGAN tunggu "satu candlestick lagi" setelah sinyal distribusi
```

---

## 7. Distribusi Detection (Konkret)

### Prinsip Dasar

Distribusi adalah proses pelaku besar **menjual posisinya kepada retail** secara bertahap.
Tujuan mereka: jual sebanyak mungkin di harga setinggi mungkin **tanpa membuat harga langsung
jatuh** (karena kalau jatuh duluan, tidak ada yang mau beli).

Oleh karena itu, distribusi sering terjadi **saat harga masih terlihat bagus** — inilah yang
membuatnya berbahaya bagi retail yang tidak tahu cara membacanya.

### Sinyal Distribusi dari Running Trade

```
SINYAL 1: VOLUME NAIK TAPI HARGA STAGNAN / LEMAH
  Logika: banyak transaksi terjadi, tapi harga tidak naik
  → ada penjual besar yang menyerap setiap kenaikan
  → mereka jual ke setiap buyer yang datang

SINYAL 2: OFFER TIDAK MAU HABIS
  - Setiap kali offer dimakan, langsung ada offer baru di harga sama
  - Berbeda dengan akumulasi di mana offer habis dan pindah ke atas
  - Ini adalah "tembok penjual" yang terus diisi ulang

SINYAL 3: BID MULAI MENIPIS SETELAH SEBELUMNYA TEBAL
  - Pelaku besar yang sebelumnya pasang bid (untuk akumulasi)
    mulai menarik bid mereka
  - Support yang sebelumnya kuat mulai tidak bisa dipegang

SINYAL 4: RUNNING TRADE ANOMALI
  - Muncul transaksi lot besar tapi di sisi HAKI (jual ke bid)
    setelah sebelumnya dominan HAKA (beli offer)
  - Pergeseran dari "beli agresif" ke "jual agresif"
```

### Sinyal Distribusi dari Broker Summary (EOD)

```
SINYAL UTAMA:
  AK (Akumulator) yang sebelumnya konsisten net buy
  mulai muncul sebagai net sell di EOD broker summary

POLA YANG HARUS DIWASPADAI:
  Hari 1-10: BK net buy konsisten   → akumulasi
  Hari 11:   BK net buy melambat    → perhatian
  Hari 12:   BK net sell kecil      → WARNING
  Hari 13:   BK net sell membesar   → DISTRIBUSI TERKONFIRMASI → EXIT

POLA HALUS (lebih berbahaya):
  BK pecah ordernya ke banyak broker lain (broker pengeksekusi berubah)
  → tujuan: tidak terlalu obvious di summary
  → deteksi: lihat apakah ada cluster broker kecil yang tiba-tiba
    net sell bersamaan, sementara BK utama "menghilang"
```

### Framework Keputusan: Hold vs Exit

```
                    MASIH HOLD?
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
  AK/BK masih net buy?        AK/BK mulai net sell?
           │                         │
           ▼                         ▼
  Running trade masih        Cek running trade:
  akumulatif?                ada HAKI besar?
           │                         │
     ┌─────┴─────┐             ┌─────┴──────┐
     ▼           ▼             ▼            ▼
   YA           TIDAK        YA            TIDAK
   │             │           │             │
   ▼             ▼           ▼             ▼
  HOLD       Evaluasi    EXIT SEGERA   Monitor ketat,
             ulang thesis (distribusi    siapkan exit
                          terkonfirmasi) plan
```

### "Jangan Jadi Exit Liquidity"

Ini adalah konsep kunci dalam distribusi detection:

```
EXIT LIQUIDITY = kondisi di mana retail (kita) adalah target jual
                 dari pelaku besar

Tanda-tanda kita hampir menjadi exit liquidity:
  - Baru masuk setelah harga sudah naik signifikan (FOMO)
  - Masuk karena hype / rekomendasi buzzer / viral di media sosial
  - Volume tiba-tiba meledak disertai berita positif
    (berita positif sering keluar tepat saat distribusi)
  - Spread melebar, tapi kita tetap masuk karena "momentum"
```

---

## Ringkasan: Integrasi ke dalam Sistem

Ketujuh elemen di atas bukan berdiri sendiri — mereka membentuk satu alur kerja terpadu:

```
SCREENING (Moonstock Candidates)
    ↓ [Filter: likuiditas, aktivitas broker, price zone]
    
REAL-TIME MONITORING (Jam Bursa)
    ↓ [Running trade analysis: real accumulation vs fake wall]
    ↓ [Bid-offer reading: cara makan offer, pola S-Lot]
    ↓ [HAKI detection: lot jumbo, kecepatan, arah]
    
MENTAL FRAMEWORK (Sepanjang Waktu)
    ↓ [3 rules terdefinisi: entry / invalidasi / exit]
    ↓ [Survival mode check: apakah kondisi layak trading?]
    
EOD ANALYSIS (Setelah Market Tutup)
    ↓ [Broker summary: update AK/BK status]
    ↓ [Estimasi average price pelaku besar]
    ↓ [Distribusi detection: apakah AK mulai switch?]
    
DECISION
    → Entry / Hold / Exit
    → Update Moonstock watchlist untuk hari berikutnya
```

---

*Dokumen ini bersifat living document — perbarui seiring materi Remora Trader terbaru
(Hengky secara rutin merilis sesi baru dengan nama bertema laut: Tidal Wave, Vortex,
Deep Blue, dll.).*