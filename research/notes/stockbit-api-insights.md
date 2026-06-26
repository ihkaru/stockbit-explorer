# Stockbit API Insights & Integration Guide

Dokumen ini merangkum seluruh hasil investigasi, pemetaan endpoint, parameter query, serta arsitektur integrasi mandiri (*Independent Fetching*) terhadap API internal Stockbit (`exodus.stockbit.com`). Informasi ini ditujukan untuk mempermudah pemahaman developer/agent lain di masa mendatang.

---

## 1. Arsitektur Session Sharing (Token Hijacking)

Stockbit Desktop Client (berbasis framework Tauri) berkomunikasi dengan server backend menggunakan protokol HTTPS (HTTP/2) ke domain `exodus.stockbit.com`.

### Mekanisme Keamanan & Otentikasi:
* **JWT Bearer Token:** Setiap API request diotentikasi menggunakan header `Authorization: Bearer <JWT_TOKEN>`.
* **JWT Expiration:** Token diterbitkan dengan masa aktif tepat **24 jam** (`exp` = `iat` + 86400).
* **Auto-Harvesting Pipeline:** 
  1. Proxy interceptor `interceptor/scripts/addon.py` mencegat lalu lintas keluar dari Stockbit Desktop.
  2. Saat menemukan request ke `exodus.stockbit.com`, interceptor menyalin seluruh request headers aktif ke [data/session_headers.json](file:///c:/projects/stockbit-explorer/data/session_headers.json).
  3. Pustaka klien kita [research/indicators/api_client.py](file:///c:/projects/stockbit-explorer/research/indicators/api_client.py) membaca file JSON tersebut secara dinamis setiap kali memicu request.
  4. **Auto-Refresh:** Jika token kedaluwarsa, pengguna hanya perlu melakukan satu kali interaksi (seperti refresh/klik saham) di Stockbit Desktop. Interceptor akan menangkap token baru dan memperbarui JSON secara otomatis tanpa perlu me-restart skrip pencari data kita.

---

## 2. Header Koneksi & User-Agent WebView2 Desktop

Untuk melakukan penarikan data secara mandiri, HTTP request wajib menyertakan set header lengkap yang meniru persis perilaku Stockbit Desktop Client (Tauri/WebView2 di Windows). Jika tidak, request dapat diblokir oleh Cloudflare WAF dengan status `403 Forbidden` atau `400 Bad Request`.

### Wajib Disertakan di Setiap Request:
- **`User-Agent`**: `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"`
- **`Authorization`**: `"Bearer <JWT_TOKEN>"` (Diambil dinamis dari `session_headers.json`)
- **`x-platform`**: `"desktop"`
- **`x-appversion`**: `"1.65.2"`
- **`origin`**: `"https://tauri.localhost"`
- **`referer`**: `"https://tauri.localhost/"`
- **`sec-ch-ua-platform`**: `'"Windows"'`
- **`sec-ch-ua`**: `'"Not)A;Brand";v="24", "Microsoft Edge WebView2";v="149", "Microsoft Edge";v="149", "Chromium";v="149"'`

---

## 3. Aturan Validasi & Penolakan Server (Accept/Reject Rules)

Berdasarkan hasil investigasi mendalam terhadap lalu lintas API asli, terdapat beberapa aturan tidak tertulis yang harus dipenuhi agar server `exodus.stockbit.com` tidak menolak request kita:

### A. Kapan Data Ditolak Server (HTTP 400 atau Mengembalikan Data Kosong `[]`):
1. **Urutan Kronologis Terbalik pada Chartbit (SANGAT KRUSIAL)**: 
   - Di endpoint `/chartbit/{STOCK}/price/daily` dan `/chartbit/{STOCK}/price/intraday`, parameter `from` dan `to` harus diletakkan dalam urutan kronologis **terbalik** (newer-first).
   - **Tolak/Kosong**: Jika Anda mengirim `from=older_date&to=newer_date` (misal `from=2021-06-01&to=2026-06-26`), API akan merespon sukses `200 OK` tetapi dengan array data kosong: `{"data":{"chartbit": []}}`.
   - **Terima**: Anda wajib mengirim `from=newer_date&to=older_date` (misal `from=2026-06-26&to=2021-06-01`).
2. **Limit Berlebihan pada Historical Summary (Net Foreign Flow)**:
   - Endpoint `/company-price-feed/historical/summary/{STOCK}` akan mengembalikan **HTTP 400 Bad Request** / `{"message":"Invalid parameter"}` jika query parameter `limit` diisi nilai **lebih dari 50** (`limit > 50`). Limit maksimal yang didukung adalah 50.
3. **Format Integer pada Kode Tipe Transaksi Market Detector**:
   - Di endpoint `/marketdetectors/{STOCK}`, query parameter `transaction_type` **wajib** berupa string enum `"TRANSACTION_TYPE_NET"` (untuk Broker Summary Net) atau `"TRANSACTION_TYPE_BUY_SELL"` (untuk Broker Summary kotor/full).
   - **Tolak**: Jika dikirim `"1"` atau `1` (seperti format API versi lama), API akan menolak atau mengembalikan array kosong.

### B. Kapan Data Diterima Server (HTTP 200 dengan Payload Valid):
1. **Token JWT Aktif**: Token divalidasi ke server autentikasi Stockbit dan belum di-expire secara paksa.
2. **Urutan Parameter Chartbit Terbalik**: `from` = tanggal terbaru, `to` = tanggal tertua.
3. **Limit Valid**: `limit` <= 50 untuk data foreign flow, dan `limit` = 0 (untuk un-limited) di chartbit.

---

## 4. Katalog Endpoint API `exodus.stockbit.com`

Berikut adalah rincian API endpoint hasil rekonstruksi, beserta parameter query spesifiknya:

### A. Chartbit Daily Candles (OHLCV Historis)
* **URL**: `https://exodus.stockbit.com/chartbit/{STOCK}/price/daily`
* **Metode**: `GET`
* **Query Parameters**:
  - `from` (Wajib): Tanggal terbaru (Format `YYYY-MM-DD`, misal `"2026-06-26"`)
  - `to` (Wajib): Tanggal tertua (Format `YYYY-MM-DD`, misal `"2016-01-01"`)
  - `limit` (Wajib): `0` (untuk mengembalikan seluruh rentang data)
* **Payload Sukses**: `data.chartbit` (list of daily candles). Berisi data `open`, `high`, `low`, `close`, `volume`, `value`, `frequency`, `foreignbuy`, `foreignsell`, `foreignflow`, `shareoutstanding`, `dividend`, dan `freq_analyzer`.

### B. Chartbit Intraday 1m Candles
* **URL**: `https://exodus.stockbit.com/chartbit/{STOCK}/price/intraday`
* **Metode**: `GET`
* **Query Parameters**:
  - `from` (Wajib): UNIX timestamp detik terbaru (misal `1782381082`)
  - `to` (Wajib): UNIX timestamp detik tertua (misal `1781974799`)
  - `limit` (Wajib): `0`
* **Payload Sukses**: `data.chartbit` (list of 1-minute candles).

### C. Market Detector (Broker Summary EOD / Bandarmologi)
* **URL**: `https://exodus.stockbit.com/marketdetectors/{STOCK}`
* **Metode**: `GET`
* **Query Parameters**:
  - `transaction_type` (Wajib): `"TRANSACTION_TYPE_NET"`
  - `market_board` (Wajib): `"MARKET_BOARD_REGULER"`
  - `investor_type` (Wajib): `"INVESTOR_TYPE_ALL"`
  - `limit` (Wajib): `25`
  - `from` (Wajib): Tanggal target (Format `YYYY-MM-DD`, misal `"2026-06-25"`)
  - `to` (Wajib): Tanggal target (Format `YYYY-MM-DD`, misal `"2026-06-25"`)
* **Payload Sukses**: `data.bandar_detector` (akumulasi verdict) dan `data.broker_summary` (daftar `brokers_buy` dan `brokers_sell` berisi kode broker, harga rata-rata, total lot, total nominal value).

### D. Historical Summary (Foreign Flow Historis)
* **URL**: `https://exodus.stockbit.com/company-price-feed/historical/summary/{STOCK}`
* **Metode**: `GET`
* **Query Parameters**:
  - `period` (Wajib): `"HS_PERIOD_DAILY"`
  - `start_date` (Wajib): Tanggal awal / tertua (Format `YYYY-MM-DD`, misal `"2025-06-17"`)
  - `end_date` (Wajib): Tanggal akhir / terbaru (Format `YYYY-MM-DD`, misal `"2025-07-16"`)
  - `limit` (Wajib): `50` (maksimal 50)
  - `page` (Wajib): `1`
* **Payload Sukses**: `data.result` (list of net foreign records per tanggal).

### E. Price Grid (Fraksi Harga Valid)
* **URL**: `https://exodus.stockbit.com/company-price-feed/prices`
* **Metode**: `GET`
* **Query Parameters**:
  - `stock_code` (Wajib): Ticker saham (misal `"BBCA"`)
* **Payload Sukses**: `data.prices` (list of integers).

### F. Running Trade (Tape Reading Source - Real-time & Historical Ticks)
* **URL**: `https://exodus.stockbit.com/order-trade/running-trade`
* **Metode**: `GET`
* **Query Parameters**:
  - `order_by` (Wajib): `RUNNING_TRADE_ORDER_BY_TIME`
  - `sort` (Wajib): `desc`
  - `limit` (Wajib): `80`
  - `symbols[]` (Opsional): Filter saham (`["BBCA"]`)
  - `action_type` (Wajib): `RUNNING_TRADE_ACTION_TYPE_ALL`
  - `market_board` (Wajib): `BOARD_TYPE_ALL`
  - `date` (Opsional): Menarik data **historical running trade** untuk tanggal spesifik (Format `YYYY-MM-DD`, misal `"2026-06-24"`).
  - `trade_number` & `cursor_direction` (Opsional): Digunakan untuk pagination scroll historis (`cursor_direction=CURSOR_DIRECTION_NEXT`).
* **Payload Sukses**: `data.running_trade` (list transaksi harian/realtime).


---


## 5. Cara Pengujian Cepat API
Gunakan skrip pengujian integrasi yang telah disediakan di repositori:
```bash
# Menjalankan pengujian integrasi mandiri untuk ticker BBCA, TLKM, GOTO, ASII
python research/indicators/test_api_client.py
```
Skrip ini akan menampilkan status konektivitas, verdict bandar, dan contoh struktur data untuk masing-masing endpoint.

---

## 6. Jembatan Gap Data & Rekayasa Data (Bridging Data Gaps)

Meskipun terdapat batasan data real-time (seperti broker masking dan rate limit), sistem dapat memproses data dari API yang ada secara cerdas untuk memenuhinya di sisi backend:

### A. Deteksi Cancel Order & Spoofing (Queue Reconstruction)
Sistem dapat menghitung jumlah lot yang dibatalkan (*canceled*) di setiap harga secara real-time tanpa API historis antrean:
$$\text{Cancel Order} = \text{Antrean Awal (Bid/Offer)} - \text{Total Match (HAKA/HAKI)} - \text{Antrean Akhir}$$
*Jika nilai hasil perhitungan bernilai positif secara signifikan saat harga mendekat, sistem mengonfirmasi adanya aksi *spoofing* (penarikan bid/offer palsu).*

### B. Optimalisasi Rate Limit (Adaptive Polling & Deduplication)
Untuk menghindari batas Cloudflare (`x-rate-limit-limit: 20` request per menit):
* Sistem melakukan polling HTTP ke `/running-trade` setiap **5 - 7 detik** dengan `limit=80`.
* Di sisi backend, transaksi yang didapat dicocokkan dengan database lokal. Transaksi yang memiliki `id` atau `trade_number` yang sudah ada akan dibuang (deduplikasi sekuensial).
* Hasilnya, seluruh data tick berhasil ditangkap tanpa ada yang terlewat, namun frekuensi request tetap sangat rendah.

### C. Dekode Broker Real-time (EOD Broker Matching)
Selama jam bursa, kode broker disamarkan oleh BEI.
* **Solusi EOD:** Sistem merekam transaksi running trade siang hari dengan parameter unik (`trade_number`, `price`, `lot`, `time`, `buy_order_number`, `sell_order_number`).
* Sore hari setelah market tutup, sistem memanggil ulang API `/running-trade` (yang datanya sudah tidak disamarkan lagi) dan melakukan SQL Join/Dictionary Mapping berdasarkan `trade_number` untuk menyuntikkan kode broker asli ke database historis kita.

### D. Rekap Foreign Flow Mandiri
Sistem dapat memetakan pergerakan asing kumulatif (contoh: 5 hari terakhir) beserta harga modalnya (EAP) secara instan:
* Kita membaca data EOD dari `/marketdetectors/{STOCK}`.
* Di sisi backend, kita memfilter semua broker yang memiliki properti `"type": "Asing"`.
* Kita menjumlahkan net lot (`blot`/`slot`) dan net value (`bval`/`sval`) untuk mendapatkan Foreign Net Volume dan Foreign VWAP secara mandiri.

### E. Skrining Moonstock (Sideways + Bandar EAP)
Saham lolos screening sebagai calon *Moonstock* jika:
1. Harga pasar saat ini berada dalam rentang aman:
   $$\text{Price} \le \text{Bandar EAP} + 5\%$$
2. Fluktuasi harga 30 hari terakhir (dari `/running-trade/chart`) menunjukkan volatilitas rendah (standar deviasi kecil / Bollinger Band menyempit) yang mengindikasikan zona sideways/akumulasi diam-bandar.

