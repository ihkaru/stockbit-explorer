# Stockbit Explorer & Transaction Analysis Automation

Repository ini bertujuan untuk membangun **alat bantu analisis transaksi (Tape Reading / Order Flow Analysis Helper)** dan **penghasil sinyal trading (Signal Generator)** berbasis metodologi Hengky Adinata dengan memanfaatkan data dari Stockbit (baik data live saat market buka maupun data simulasi/replay menggunakan `mitmdump` saat bursa tutup).

---

## Metodologi Trading (Hengky Adinata)
1. **Analisis Transaksi (Tape Reading/Order Flow):** Memantau Running Trade & Orderbook untuk mendeteksi transaksi jumbo (HAKI) dan akumulasi oleh pelaku besar (*Smart Money*).
2. **Filtering & Konfirmasi:** Memvalidasi letak akumulasi (apakah di area harga murah/sideways) dan respons pasar (bid menebal, offer dimakan agresif).
3. **Eksekusi Trading:** Entry searah dengan kekuatan *Smart Money* menggunakan gaya scalping/momentum trading.
4. **Take Profit / Decision Making:** Keluar posisi saat target tercapai atau terdeteksi aksi distribusi balik oleh pelaku besar.
5. **Risk Management:** Mengamankan keuntungan secara berkala dengan memisahkan modal dasar untuk putaran berikutnya.
6. **Alokasi Swing/Invest:** Memindahkan profit ke aset *undervalued* (Blue Chip/Mid-cap) untuk pertumbuhan jangka panjang.

---

## Regulasi Terkini BEI (Per Juni 2026)
Sistem ini disesuaikan dengan batasan regulasi BEI terkini untuk menghindari sinyal palsu:
1. **Kode Broker Masking (Penutupan Kode Broker Real-time):** Kode broker ditutup selama jam perdagangan. Deteksi broker akumulasi secara real-time tidak dilakukan saat jam bursa; analisis real-time murni berfokus pada volume, kecepatan running trade, dan orderbook. Data Broker Summary penuh baru dianalisis setelah market tutup (*End-of-Day*).
2. **Full Periodic Call Auction (FCA):** Saham di Papan Pemantauan Khusus (PPK) diperdagangkan secara buta (*blind order book*) tanpa running trade kontinu. Saham FCA otomatis disaring dan dikecualikan oleh sistem.
3. **Auto Rejection Simetris:** Aturan ARA & ARB simetris berimbas pada perhitungan rasio risk-to-reward harian yang dinamis.
4. **Harga Saham Minimum Rp1:** Saham tidak lagi aman tidur di Rp50, melainkan dapat turun hingga Rp1.


---

## Analisis Gap Data: Keterbatasan Offline vs. Solusi Live Streaming

Untuk menerapkan Tape Reading secara efektif, terdapat kesenjangan (*gap*) data yang kritis antara metode pengumpulan data offline (pasca-market) dengan data yang sebenarnya dibutuhkan oleh strategi:

| Kebutuhan Strategi | Keterbatasan Data Offline (Pasca-Market / EOD) | Solusi Sistem: Live Streaming & Sync Backend |
| :--- | :--- | :--- |
| **Kecepatan Transaksi (HAKA Speed)** | Data EOD hanya menampilkan total volume harian tanpa rincian waktu terjadinya. | **Live capture** mendeteksi kecepatan eksekusi (milidetik) untuk mengidentifikasi urgensi pembeli. |
| **Deteksi Fake Bid/Offer (Spoofing)** | Riwayat antrean yang dicabut (*cancel order*) tidak tercatat di akhir hari. | **Live monitoring** mendeteksi *cancellation rate* bid/offer sebelum sempat match. |
| **Deteksi Pecahan Lot (Split Order)** | Hanya terlihat total lot akumulasi per broker di summary akhir hari. | **Backend parser** menyaring susunan transaksi berurutan (*split order*) per detik. |
| **Ketepatan Sinyal & Entry Point** | Analisis malam hari membuat entri esok pagi rawan terkena *open gap up*. | **Real-time Engine** memicu notifikasi instan langsung saat bursa berjalan untuk entry presisi di area murah. |

---

## Rencana Besar Proyek (Phased Roadmap)

```plaintext
   +---------------------------------------------------------+
   |              FASE 1: INTERCEPT STOCKBIT                 |
   |  Mencegat lalu lintas WebSocket Stockbit via mitmproxy  |
   +---------------------------------------------------------+
                                |
                                v
   +---------------------------------------------------------+
   |                FASE 2: DUMPING DATA                     |
   |  Menyimpan log data intraday tick-by-tick ke file lokal |
   +---------------------------------------------------------+
                                |
                                v
   +---------------------------------------------------------+
   |            FASE 3 & 4: RESEARCH & DATA ANALYSIS         |
   |  Riset transaksi Smart Money & hitung rasio HAKA/HAKI   |
   +---------------------------------------------------------+
                                |
                                v
   +---------------------------------------------------------+
   |               FASE 5: WORKFLOW DESIGN                   |
   |  Mendesain arsitektur integrasi sistem dari hulu-hilir  |
   +---------------------------------------------------------+
                                |
                                v
   +---------------------------------------------------------+
   |         FASE 6 & 7: BACKTESTING & FORWARD TESTING       |
   |  Simulator replay & pengujian sinyal real-time (dry run)|
   +---------------------------------------------------------+
                                |
                                v
   +---------------------------------------------------------+
   |            FASE 8 & 9: UI DESIGN & DEPLOYMENT           |
   |  Dashboard visualisasi & peluncuran sistem stabil       |
   +---------------------------------------------------------+
```

### Penjelasan Detail Fase:
1. **Intercept Stockbit:** Menganalisis traffic WebSocket Stockbit di browser dan membangun skrip interceptor menggunakan Python.
2. **Dumping Data:** Merekam dan menyimpan data intraday ke format `.mitm` untuk simulasi offline.
3. **Research:** Memetakan skema pesan WebSocket dan mencari pola akumulasi *Smart Money*.
4. **Data Analysis:** Merumuskan filter FCA dan batas transaksi lot jumbo.
5. **Workflow Design:** Merancang integrasi data pipeline.
6. **Backtesting:** Simulator pemutar ulang data `.mitm` untuk evaluasi akurasi sinyal.
7. **Forward Testing:** Uji coba sinyal real-time di tengah jam bursa secara dry run.
8. **UI Design:** Dashboard visualisasi PWA.
9. **Deployment:** Setup server lokal/cloud stabil.

---

### Struktur Folder Proyek (Folder Structure)

Struktur direktori dirancang bertahap untuk memisahkan antara modul interceptor, repositori data hasil capture, ruang riset dan analisis, mesin backtesting terdistribusi, serta kontainerisasi database PostgreSQL:

```plaintext
stockbit-explorer/
│
├── interceptor/              # FASE 1: Interception
│   ├── scripts/              # Skrip custom mitmproxy (addon.py) untuk menyadap WebSocket
│   ├── config/               # Sertifikat SSL & konfigurasi mitmproxy
│   └── README.md             # Petunjuk cara setup proxy & penyadapan
│
├── data/                     # FASE 2: Dumping & Datasets
│   ├── raw/                  # Data mentah (.mitm, .log, .jsonl) hasil rekaman WebSocket
│   ├── processed/            # Data hasil parsing yang siap pakai
│   └── README.md             # Penjelasan format data dan cara eksploitasinya
│
├── research/                 # FASE 3 & 4: Research & Data Analysis
│   ├── notebooks/            # Jupyter Notebooks (.ipynb) untuk riset analisis
│   ├── indicators/           # Modul & pustaka analisis Tape Reading (Python)
│   │   ├── db/               # Paket database repository (PG/Timescale DDL & CRUD)
│   │   ├── parser/           # Paket parser log WebSocket/HTTP menjadi data terstruktur
│   │   ├── tape_reading/     # Paket kalkulator sinyal HAKA/HAKI Remora Trader
│   │   ├── api_client.py     # Reusable client API Stockbit mandiri (exodus client)
│   │   ├── test_api_client.py # Skrip pengujian integrasi live API klien
│   │   ├── backloader.py     # CLI Backloader historis multi-threaded rate-limited
│   │   ├── backload_config.py # Konfigurasi default backloading & target groups
│   │   ├── db_maintenance.py # CLI Pemeliharaan, kompresi, & vakum database
│   │   ├── fetch_ticker_data.py # Utilitas penarik data emiten harian (Frontloader)
│   │   └── worker.py         # Daemon Background Worker untuk realtime log tailing
│   └── notes/                # Catatan riset, metodologi, & insight API
│       ├── hengky-adinata.md # Rangkuman detail metodologi trading Remora Trader
│       └── stockbit-api-insights.md # Rangkuman skema, parameter, & jembatan gap API
│
├── backtester/               # FASE 5, 6 & 7: Simulator & Backtest (Akan diperluas)
│   ├── simulator/            # Replay engine untuk memutar ulang log biner WebSocket
│   └── main.py               # Entry point untuk simulasi
│
├── infra/                    # FASE 10: Infrastruktur & Database Setup
│   ├── init.sql              # PostgreSQL DDL + TimescaleDB Hypertables & triggers
│   └── migrate_sqlite_to_pg.py # Skrip migrasi batch SQLite -> PostgreSQL Docker
│
├── Dockerfile                # Containerization untuk worker daemon
├── docker-compose.yml        # Docker stack: TimescaleDB (5433), PgBouncer (6432), Worker
├── requirements.txt          # Dependensi pustaka Python
├── gemini.md                 # Log progress harian (antigravity log)
└── README.md                 # Dokumentasi utama proyek
```

---

## Independent Fetching & Session Sharing (Metode Akses Mandiri)

Untuk menghindari ketergantungan penuh pada aplikasi Stockbit Desktop yang harus terus aktif melakukan polling, repositori ini mengimplementasikan **Session Sharing & Hijacking**:

1. **Auto-Harvesting Token:** Ketika proxy interceptor (`addon.py`) berjalan dan menangkap request dari Stockbit Desktop ke `exodus.stockbit.com`, skrip akan otomatis menyalin request headers terbaru (termasuk JWT Token `Authorization` Bearer dan `Cookie`) ke dalam berkas lokal [data/session_headers.json](file:///c:/projects/stockbit-explorer/data/session_headers.json).
2. **Independent Fetching:** Pustaka klien [api_client.py](file:///c:/projects/stockbit-explorer/research/indicators/api_client.py) membaca berkas [data/session_headers.json](file:///c:/projects/stockbit-explorer/data/session_headers.json) untuk melakukan request HTTP sendiri ke server secara berkala. Token JWT valid selama **24 jam** sejak diterbitkan.
3. **Peta API Stockbit Yang Didukung:**
   * **Running Trade:** `https://exodus.stockbit.com/order-trade/running-trade` (Params: `limit`, `symbols[]`, `action_type`, `market_board`, `sort`, `order_by`).
   * **Trade Book:** `https://exodus.stockbit.com/order-trade/trade-book` (Params: `symbol`, `group_by`).
   * **Market Detector (EOD Broker Summary):** `https://exodus.stockbit.com/marketdetectors/{STOCK}` (Params: `transaction_type=TRANSACTION_TYPE_NET`, `from=YYYY-MM-DD`, `to=YYYY-MM-DD`). Mengembalikan data net lot, average price, dan tipe broker (`Asing`/`Lokal`).
   * **Price Candles (Daily & Intraday 1m):** `https://exodus.stockbit.com/chartbit/{STOCK}/price/{intraday|daily}` (Params: `from` & `to` yang memiliki urutan terbalik).

---

## Infrastruktur Database & Container (PostgreSQL + TimescaleDB + PgBouncer)

Untuk menangani skala data miliaran baris time-series, proyek ini bermigrasi dari SQLite ke arsitektur container terintegrasi:
*   **TimescaleDB (Port 5433)**: Mengelompokkan tabel deret waktu besar (`running_trades`, `ohlcv_data`, `broker_daily_activity`) menjadi hypertable, mengaktifkan kompresi chunk otomatis (>30 hari, rasio ~5x), dan mengoptimalkan performa kueri. Port internal `5432` dipetakan ke host port `5433` untuk mencegah konflik dengan Postgres lokal lainnya.
*   **PgBouncer (Port 6432)**: Pooler koneksi database berjalan dalam mode `transaction` pooling untuk menangani beban konkruensi penarikan data dari puluhan thread sekaligus tanpa menghabiskan slot koneksi fisik di Postgres.
*   **Worker Ingestion Daemon**: Daemon Python berjalan di dalam Docker yang terus memantau direktori log `data/raw/` secara real-time. Ketika terdeteksi data baru dari running trade WebSocket, worker langsung mem-parsing dan melakukan *UPSERT* ke database PostgreSQL melewati PgBouncer.

---

## Panduan Menjalankan Layanan (Docker & Python Host)

### 1. Menjalankan Docker Stack
Nyalakan database TimescaleDB, PgBouncer, dan Worker daemon terisolasi di latar belakang:
```bash
docker compose up -d
```
Verifikasi bahwa seluruh container berjalan sehat:
```bash
docker compose ps
```

### 2. Melakukan Migrasi Data Awal (SQLite -> Postgres Docker)
Pastikan data dari SQLite lokal dipindahkan ke database Docker baru melalui PgBouncer (Port 6432):
```bash
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python infra/migrate_sqlite_to_pg.py
```

### 3. Menjalankan Historical Backloader (Massal & Cepat)
Gunakan backloader berkinerja tinggi untuk menarik data historis emiten secara konkuren (default 8 worker, 50ms spacing):
```bash
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/backloader.py --symbols PANI,BUMI,PTRO,VKTR,SINI --start-date 2026-06-19 --end-date 2026-06-26
```

### 4. Pengecekan Kelengkapan Data (Audit)
Untuk mengaudit apakah data historis/live dari ticker tertentu sudah lengkap pada rentang tanggal tertentu, jalankan skrip audit kelengkapan data:
```bash
# Menjalankan audit kelengkapan penuh (Wajib Running Trades + Intraday 1-min untuk Tape Reading)
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/check_db_completeness.py --start-date 2026-06-19 --end-date 2026-06-26

# Menjalankan audit dalam mode EOD-Only (hanya memeriksa Lilin EOD, Broker Summary, & Foreign Flow)
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/check_db_completeness.py --start-date 2026-06-19 --end-date 2026-06-26 --eod-only
```

### 5. Pemeliharaan & Integritas Database (Maintenance)
Jalankan skrip pemeliharaan berkala untuk merapikan indeks, menghapus duplikasi yatim, dan pemampatan penyimpanan database:
```bash
# Melakukan pengecekan integritas relasional & TimescaleDB hypertables
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/db_maintenance.py --check

# Melakukan pembersihan data duplikat & data yatim (orphan) secara otomatis
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/db_maintenance.py --clean

# Membangun ulang indeks & merampingkan penyimpanan database (VACUUM & ANALYZE)
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/db_maintenance.py --optimize

# Menjalankan semua tugas pemeliharaan sekaligus (Check + Clean + Optimize)
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:6432/stockbit_explorer"; python research/indicators/db_maintenance.py --all
```

---

## Pengecekan Integritas & Kelengkapan Data

Sistem ini dilengkapi dengan dua skrip utilitas utama untuk memastikan kesehatan database dan kelayakan data untuk analisis Tape Reading:

### 1. Skrip Kelengkapan Data (`check_db_completeness.py`)
Skrip ini mengaudit ketersediaan data untuk seluruh ticker yang ada di database pada rentang tanggal bursa (weekdays).

*   **Dua Mode Pengecekan**:
    *   **Mode Default (Full Audit)**: Mewajibkan semua tabel terisi lengkap, termasuk **Intraday 1-minute candles** dan **Running Trades (tick-by-tick)**. Mode ini penting sebelum melakukan Tape Reading backtest atau live analysis, karena kalkulasi volume HAKA/HAKI dan deteksi S-Lot didasarkan pada data mikro ini.
    *   **Mode EOD-Only (`--eod-only`)**: Menurunkan kriteria audit hanya pada data harian ringkasan (Daily OHLCV EOD, Broker Summary EOD, dan Net Foreign Flow).
*   **Pengecualian Khusus Index (`IHSG`)**: Indeks IHSG tidak memiliki data Broker Summary maupun Running Trades di feed bursa standar. Skrip ini secara otomatis mengecualikan kriteria tersebut untuk `IHSG` agar status auditnya tidak terhambat.
*   **Status Kelengkapan Saat Ini (19 - 26 Juni 2026)**:
    *   **EOD-Only Mode**: **100% Lengkap** untuk 36 ticker (`Complete: 216 | Incomplete: 0`). Semua data lilin harian, aktivitas broker EOD, dan foreign flow telah diserap dengan sempurna.
    *   **Full Mode (Tape Reading)**: **Parsial**. Hanya lengkap pada ticker dan tanggal di mana logs raw WebSocket telah direkam atau diunduh secara spesifik (misalnya BBCA, GOTO, TLKM, SKRN pada hari bursa aktif tertentu). Ticker lainnya hanya memiliki data EOD karena API tick-by-tick historis memiliki limitasi penarikan volume besar secara paralel.

### 2. Skrip Pemeliharaan & Integritas (`db_maintenance.py`)
Skrip ini memfasilitasi pembersihan data sampah dan perampingan penyimpanan database PostgreSQL/TimescaleDB secara berkala.

*   **Pemeriksaan Integritas (`--check`)**: Memverifikasi konektivitas driver PostgreSQL, relasi foreign key, dan eksistensi hypertable TimescaleDB (`running_trades`, `ohlcv_data`, `broker_daily_activity`).
*   **Pembersihan Data (`--clean`)**: Menghapus data duplikat pada tabel `trade_book` dan membersihkan rekaman yatim (*orphaned*) pada `orderbook_ticks` yang tidak memiliki parent di `orderbook_snapshots`.
*   **Optimasi Penyimpanan (`--optimize`)**: Memicu perintah `VACUUM` dan `ANALYZE` pada PostgreSQL untuk mengklaim kembali ruang disk yang terbuang pasca-penghapusan data besar-besaran serta memperbarui statistik indeks untuk query planner yang efisien.

---

## Panduan Eksplorasi Repositori (Exploration Guide)

### 1. Pelajari Dasar Strategi & Metodologi
*   **Ke mana harus pergi:** Buka berkas [research/notes/hengky-adinata.md](file:///c:/projects/stockbit-explorer/research/notes/hengky-adinata.md).
*   **Mengapa:** File ini menjelaskan aturan main trading (Tape Reading, indikator HAKA/HAKI, filter FCA) yang menjadi logika dasar seluruh algoritma deteksi sinyal di repo ini.

### 2. Pahami Rencana Kerja & Progress Terbaru
*   **Ke mana harus pergi:** Buka berkas [gemini.md](file:///c:/projects/stockbit-explorer/gemini.md) dan bagian **Rencana Besar Proyek** di atas.

### 3. Masuk ke Tahap Pengumpulan Data (Fase 1 & 2)
*   **Ke mana harus pergi:** Folder `interceptor/` dan `data/`.

### 4. Pelajari Analisis Formula & Pengujian (Fase 3, 4 & 5)
*   **Ke mana harus pergi:** Folder `research/` dan `backtester/strategy/`.

### 5. Pembangunan Dashboard & API Sinyal (Fase 8 & 9)
*   **Ke mana harus pergi:** Folder `backend-api/` dan `frontend-pwa/` (akan dibangun pada fase akhir).
*   **Mengapa:** Ini adalah antarmuka visual (Dashboard PWA berbasis Vue) dan penyedia data (Laravel API) tempat trader memantau sinyal HAKA/HAKI yang dikirimkan secara real-time dari engine.
