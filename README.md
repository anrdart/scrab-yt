# ytdupe — Deteksi Duplikat Konten YouTube

**ytdupe** adalah alat CLI untuk mendeteksi duplikasi konten YouTube di level **isi/transkrip**, bukan cuma judul. Cocok untuk tim digital advertising yang perlu mengidentifikasi video re-upload di channel YouTube.

## Fitur

- **Bulk download subtitle** dari seluruh channel YouTube via `yt-dlp`
- **Deteksi duplikat** menggunakan TF-IDF + cosine similarity
- **Clustering otomatis** — video yang mirip dikelompokkan (jika A≈B dan B≈C, otomatis jadi satu grup)
- **Series exclusion** — video seri ("Hari ke-1", "Hari ke-2") otomatis di-skip agar tidak dianggap duplikat
- **Laporan Excel** multi-sheet dengan warna (PRIMARY hijau, DUPLIKAT merah)
- **Dukungan Bahasa Indonesia** — stemming & stopword removal via Sastrawi
- **Integrasi metadata** — gabung data penayangan dari CSV YouTube Studio

## Persyaratan

- **Python 3.10** atau lebih baru
- **pip** (package manager Python)
- Koneksi internet (untuk download subtitle)

## Instalasi

### 1. Install Python

Download dan install Python dari [python.org](https://www.python.org/downloads/). Pastikan centang **"Add Python to PATH"** saat install di Windows.

Cek instalasi:
```bash
python --version
```

### 2. Install dependencies

Buka terminal/command prompt, masuk ke folder project, lalu jalankan:
```bash
cd /path/ke/ytdupe
pip install -r requirements.txt
```

### 3. Install yt-dlp (jika belum ada)

```bash
pip install yt-dlp
```

## Konfigurasi

Edit file `config.yaml` sesuai kebutuhan:

```yaml
channel_url: "https://www.youtube.com/@Gerakanwakafsumur/videos"
languages: ["id", "en"]           # Bahasa caption: coba Indonesia dulu, fallback English
sleep_interval: 2                  # Jeda antar download (detik) — naikkan jika error 429
similarity_threshold: 0.75         # 0.75 = ketat | 0.60 = longgar (lebih banyak kandidat)
use_stemming: false                # true = akurat tapi lambat | false = cepat
exclude_series: true               # Skip video seri (hari ke-1, hari ke-2, dst)
output_file: "data/output/laporan_duplikat_konten.xlsx"
subtitle_dir: "data/subtitles"
```

## Penggunaan

### Command 1: Download subtitle saja

```bash
ytdupe download --channel "https://www.youtube.com/@NamaChannel/videos"
```

### Command 2: Analisis duplikat dari subtitle yang sudah ada

```bash
ytdupe analyze
```

Dengan opsi:
```bash
ytdupe analyze --threshold 0.70 --metadata "Data tabel.csv"
```

### Command 3: Download + Analisis sekaligus

```bash
ytdupe all --channel "https://www.youtube.com/@NamaChannel/videos"
```

Dengan opsi lengkap:
```bash
ytdupe all --channel "https://www.youtube.com/@NamaChannel/videos" --threshold 0.75 --metadata "Data tabel.csv"
```

## Cara Dapatkan CSV YouTube Studio

1. Buka **YouTube Studio** (studio.youtube.com)
2. Pilih channel yang ingin dianalisis
3. Masuk ke menu **Konten** atau **Analytics**
4. Klik **Lihat lainnya** di bagian kanan atas tabel
5. Klik ikon download / **Export** → pilih format CSV
6. Simpan file CSV di folder project (misal: `Data tabel.csv`)

File CSV harus memiliki kolom: `Konten`, `Judul video`, `Waktu publikasi video`, `Durasi`, `Penayangan`, dll.

Jika ada beberapa file CSV (per periode), gabungkan manual atau letakkan di satu folder — sistem otomatis dedupe berdasarkan video ID dan ambil penayangan tertinggi.

## Cara Baca Hasil Excel

File output berisi beberapa sheet:

### Sheet "Ringkasan"
Metrik kunci: total video, jumlah cluster duplikat, threshold yang dipakai, tanggal generate.

### Sheet "Duplikat Konten"
Daftar video duplikat per cluster:
- **Hijau** = PRIMARY (video dengan penayangan tertinggi, pertahankan)
- **Merah** = DUPLIKAT (review — kemungkinan re-upload, bisa dihapus/privat)
- Kolom: Group ID, Status, Video ID, Judul, Tanggal, Durasi, Penayangan, Similarity Score

### Sheet "Transkrip"
Preview 200 karakter pertama transkrip tiap video untuk verifikasi manual.

### Sheet "Matriks Similarity" (jika ≤100 video)
Heatmap similarity antar semua video (merah = rendah, hijau = tinggi).

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Error 429 (rate limit) dari YouTube | Naikkan `sleep_interval` di config.yaml ke 5-10 detik |
| Tidak ada subtitle ditemukan | Channel mungkin tidak punya auto-caption. Coba ganti `languages` ke `["en"]` |
| Proses stemming sangat lambat | Set `use_stemming: false` di config.yaml |
| Hasil duplikat terlalu banyak | Naikkan `similarity_threshold` ke 0.80 atau 0.85 |
| Hasil duplikat terlalu sedikit | Turunkan `similarity_threshold` ke 0.60 atau 0.65 |
| Video seri terdeteksi sebagai duplikat | Pastikan `exclude_series: true` di config.yaml |

## Keterbatasan

1. **Hanya bekerja dengan video yang memiliki auto-caption.** Video tanpa subtitle otomatis akan di-skip.
2. **Tidak bisa mendeteksi duplikat visual.** Dua video dengan footage sama tapi narasi berbeda tidak terdeteksi. Untuk itu diperlukan perceptual hashing (di luar scope).
3. **Akurasi tergantung kualitas auto-caption.** Caption yang buruk → transkrip tidak akurat → deteksi kurang tepat.
4. **Video pendek (Shorts)** mungkin memiliki transkrip sangat singkat sehingga similarity score bisa tidak stabil.
5. **Proses download ~700 video** membutuhkan waktu ~25-35 menit tergantung koneksi dan sleep interval.

## Menjalankan tanpa install

Jika tidak ingin install sebagai package:
```bash
python -m ytdupe.cli all --channel "https://www.youtube.com/@NamaChannel/videos"
```

## Deploy Backend dengan Docker

Backend FastAPI bisa dijalankan sebagai container dari root project:

```bash
docker compose up --build
```

Endpoint lokal:

```bash
curl http://127.0.0.1:8001/api/health
```

Environment penting:

| Variable | Fungsi | Contoh |
|----------|--------|--------|
| `PORT` | Port uvicorn di container | `8001` |
| `YTDUPE_DATA_DIR` | Lokasi data job/subtitle/output | `/app/data` |
| `YTDUPE_DB` | Lokasi SQLite database | `/app/data/ytdupe.db` |
| `YTDUPE_CORS_ORIGINS` | Domain frontend yang boleh akses API | `https://ytdupe.pages.dev` |

Untuk production, pasang persistent volume ke `/app/data` supaya database SQLite, subtitle, dan laporan Excel tidak hilang saat container restart.

## Deploy Frontend ke Cloudflare Pages

Frontend adalah static Vite app di folder `frontend`.

Cloudflare Pages settings:

| Setting | Nilai |
|---------|-------|
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `frontend` |

Set environment variable di Cloudflare Pages:

```bash
VITE_API_BASE_URL=https://backend-domain-kamu.com
```

Lalu set backend:

```bash
YTDUPE_CORS_ORIGINS=https://domain-cloudflare-pages-kamu.pages.dev
```

File `frontend/public/_redirects` sudah disiapkan supaya route React seperti `/analyses/<id>` tetap bisa dibuka langsung atau direfresh.
