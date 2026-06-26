# Setup Interceptor Stockbit

Modul ini bertanggung jawab untuk mencegat (*intercept*) lalu lintas WebSocket dari Stockbit secara real-time menggunakan `mitmproxy` / `mitmdump`.

---

## Prasyarat (Prerequisites)
1. Python 3.10+
2. Paket `mitmproxy` telah terinstal di python environment Anda (`pip install mitmproxy`).

---

## Langkah Setup & Penggunaan

### 1. Jalankan mitmdump Pertama Kali
Jalankan command ini di terminal untuk menginisialisasi sertifikat SSL `mitmproxy` di folder user Anda:
```bash
mitmdump
```
Hentikan program setelah berjalan (`Ctrl+C`). Sertifikat CA akan otomatis terbuat di folder `~/.mitmproxy/` (atau `C:\Users\Username\.mitmproxy\`).

### 2. Instal Sertifikat SSL mitmproxy di PC/Browser
Agar dapat membaca lalu lintas HTTPS/WSS (aman), PC Anda harus mempercayai sertifikat dari mitmproxy:
* **Windows:**
  1. Buka folder `C:\Users\Username\.mitmproxy\`.
  2. Klik dua kali berkas `mitmproxy-ca-cert.p12`.
  3. Pilih **Store Location: Current User** -> Next.
  4. Pilih **Place all certificates in the following store** -> **Trusted Root Certification Authorities** -> Next -> Finish.
* **Browser (Firefox/Chrome):** Jika menggunakan Firefox, masuk ke Settings -> Certificates -> View Certificates -> Import -> pilih `mitmproxy-ca-cert.pem` -> Centang "Trust this CA to identify websites".

### 3. Aktifkan System/Browser Proxy
Atur proxy koneksi internet Anda atau gunakan extension proxy manager (seperti Proxy SwitchyOmega di Chrome/Firefox):
* **Host:** `127.0.0.1`
* **Port:** `8080`

### 4. Jalankan Skrip Interseptor
Jalankan `mitmdump` dengan menyertakan skrip `addon.py`:
```bash
mitmdump -s scripts/addon.py
```
Atau jika ingin berjalan tanpa mencetak log request HTTP biasa (hanya menampilkan log dari skrip WebSocket kita):
```bash
mitmdump -q -s scripts/addon.py
```

### 5. Buka Stockbit & Pantau Data
1. Buka browser dan masuk ke [Stockbit](https://stockbit.com/).
2. Login dan buka fitur **Running Trade** atau **Orderbook**.
3. Periksa file `interceptor.log` yang dibuat di direktori utama, atau amati terminal Anda. Frame WebSocket yang ditangkap akan tercetak secara real-time.
