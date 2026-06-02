# SUPERPROMPT — Sistem Deteksi Duplikat Konten YouTube (Content-Level)

> **Cara pakai:** Copy seluruh isi file ini, paste ke AI coding agent (Claude Code, Cursor, Windsurf, dll). Agent akan generate full project siap jalan. Bagian `[ISI SENDIRI]` ganti sesuai kebutuhan lu sebelum di-submit.

---

## ROLE & GOAL

Lu adalah senior Python engineer. Bikinin gue aplikasi CLI (command-line) bernama **`ytdupe`** untuk mendeteksi **duplikasi konten YouTube di level isi/transkrip**, bukan cuma judul. Sistem harus:

1. Bulk-download subtitle/caption dari satu channel YouTube via `yt-dlp`.
2. Parse file subtitle (VTT/SRT) jadi teks bersih per video.
3. Hitung kemiripan antar-transkrip pakai TF-IDF + cosine similarity.
4. Deteksi pasangan video yang **isinya mirip walau judulnya beda** (kasus re-upload).
5. Export hasil ke Excel multi-sheet yang rapi & berwarna.

Target user: tim digital advertising (non-engineer friendly). Output harus bisa dijalankan orang awam dengan 1–2 command.

---

## KONTEKS DOMAIN

- Channel target: kanal donasi/wakaf Islami (contoh: `@Gerakanwakafsumur`).
- Karakteristik konten: banyak Shorts pendek (≤60 detik), tema berulang (air bersih, santri, sumur bor), sering re-upload dengan ganti judul/thumbnail.
- Bahasa caption: **Bahasa Indonesia** (`id`), fallback ke `en` kalau tidak ada.
- Skala: ~700 video per channel. Sistem harus tetap efisien di jumlah segini.

---

## STACK & DEPENDENCIES

- Python 3.10+
- `yt-dlp` — download subtitle
- `webvtt-py` atau parser manual — parse VTT
- `scikit-learn` — TF-IDF + cosine similarity
- `pandas` — manipulasi data
- `openpyxl` — generate Excel berformat
- `Sastrawi` — stemming + stopword removal Bahasa Indonesia (opsional tapi recommended)
- `tqdm` — progress bar
- `click` atau `argparse` — CLI interface

Buatkan `requirements.txt` dan `README.md` instalasi.

---

## STRUKTUR PROJECT YANG DIINGINKAN

```
ytdupe/
├── README.md                 # cara install & pakai, bahasa Indonesia, step-by-step
├── requirements.txt
├── config.yaml               # semua setting bisa diubah tanpa edit code
├── ytdupe/
│   ├── __init__.py
│   ├── cli.py                # entry point: command download / analyze / all
│   ├── downloader.py         # wrapper yt-dlp
│   ├── parser.py             # VTT/SRT -> teks bersih
│   ├── preprocess.py         # normalisasi teks Bahasa Indonesia
│   ├── similarity.py         # TF-IDF + cosine + clustering duplikat
│   ├── reporter.py           # generate Excel multi-sheet
│   └── utils.py
├── data/
│   ├── subtitles/            # hasil download .vtt
│   └── output/               # hasil Excel
└── tests/
    └── test_similarity.py
```

---

## SPESIFIKASI DETAIL PER MODUL

### 1. `downloader.py`
- Fungsi `download_subtitles(channel_url, lang_priority, output_dir, sleep_interval)`.
- Pakai `yt-dlp` via subprocess ATAU python API (`yt_dlp.YoutubeDL`).
- Flags wajib: `--write-auto-sub`, `--skip-download`, `--sub-format vtt`, output template `%(id)s.%(ext)s`.
- `lang_priority` default `["id", "en"]` — coba `id` dulu, fallback `en`.
- Tambah `--sleep-interval` (default 2 detik) untuk hindari rate-limit error 429.
- Handle error per video tanpa nge-crash seluruh proses (try/except + log skip).
- Return list video ID yang berhasil + yang gagal.

### 2. `parser.py`
- Fungsi `parse_vtt(filepath) -> str`: ekstrak teks murni dari VTT.
- Buang timestamp, tag posisi (`<c>`, `align:`, dll), dan baris duplikat berurutan (auto-caption sering ngulang baris).
- Return satu string transkrip bersih per video.
- Mapping `{video_id: transcript}`.

### 3. `preprocess.py`
- Fungsi `normalize(text) -> str`: lowercase, hapus tanda baca, hapus angka berdiri sendiri, collapse spasi.
- Stopword removal Bahasa Indonesia (pakai Sastrawi atau list custom).
- Stemming opsional (toggle di config — stemming bikin akurat tapi lambat).

### 4. `similarity.py`
- Build TF-IDF matrix dari semua transkrip (`TfidfVectorizer`, `ngram_range=(1,2)`).
- Hitung cosine similarity matrix antar semua video.
- Fungsi `find_duplicates(threshold)`: ambil pasangan dengan similarity ≥ threshold (default `0.75`).
- **Penting:** kasih flag untuk exclude pasangan yang merupakan **seri episode** (judul mengandung pola `hari ke-X` / `day-X` dengan angka beda) — ini bukan duplikat.
- Kelompokkan duplikat transitif jadi cluster (kalau A≈B dan B≈C, jadikan satu grup A-B-C) pakai connected components.
- Untuk tiap cluster, tandai video dengan **penayangan tertinggi sebagai PRIMARY**, sisanya **DUPLIKAT (review)**.

### 5. `reporter.py`
Generate Excel `.xlsx` dengan sheet berikut (font Arial, header navy `1F3864` teks putih, border tipis, freeze panes, auto-filter):

- **Sheet `Ringkasan`**: metrik kunci (total video dianalisis, jumlah cluster duplikat, total video duplikat), threshold yang dipakai, tanggal generate, rekomendasi action.
- **Sheet `Duplikat Konten`**: per cluster — Group ID, Status (PRIMARY hijau `C6EFCE` / DUPLIKAT merah `FFC7CE`), Video ID, Judul, Tanggal, Durasi, Penayangan, Similarity Score.
- **Sheet `Matriks Similarity`** (opsional, kalau ≤100 video): heatmap similarity antar video pakai conditional formatting color scale.
- **Sheet `Transkrip`**: video ID + 200 karakter pertama transkrip (buat verifikasi manual).

Angka format `#,##0`. Zero formula error wajib.

### 6. `cli.py`
Tiga command:
```bash
ytdupe download --channel <URL>           # cuma download subtitle
ytdupe analyze --threshold 0.75           # analisis dari subtitle yg udah ada
ytdupe all --channel <URL> --threshold 0.75   # download + analyze sekaligus
```
Semua param punya default dari `config.yaml`. Tampilkan progress bar (`tqdm`) di tiap tahap.

---

## `config.yaml` YANG DIINGINKAN

```yaml
channel_url: "https://www.youtube.com/@Gerakanwakafsumur/videos"
languages: ["id", "en"]
sleep_interval: 2
similarity_threshold: 0.75
use_stemming: false
exclude_series: true          # skip pasangan seri "hari ke-X"
output_file: "data/output/laporan_duplikat_konten.xlsx"
subtitle_dir: "data/subtitles"
```

---

## INTEGRASI DATA METADATA (PENTING)

Sistem harus bisa **gabung** transkrip dengan metadata video (judul, tanggal, durasi, penayangan) dari file CSV export YouTube Studio. Format CSV (`Data tabel.csv`):

```
Konten,Judul video,Waktu publikasi video,Durasi,Penayangan,Waktu tonton (jam),Subscriber,Tayangan,Rasio klik-tayang dari tayangan (%)
```

- Kolom `Konten` = video ID (matching ke nama file subtitle).
- Tambah param `--metadata <path.csv>` di command analyze.
- Kalau ada beberapa CSV (per periode), gabung & dedupe by video ID, ambil baris dengan penayangan tertinggi.

---

## REQUIREMENT KUALITAS

- Code bersih, modular, ada docstring tiap fungsi.
- Error handling di semua I/O (file gak ada, subtitle kosong, CSV malformed).
- Logging pakai modul `logging`, simpan ke `ytdupe.log`.
- `README.md` ditulis dalam **Bahasa Indonesia**, step-by-step buat orang non-teknis (install Python → install dependencies → jalanin command → buka hasil Excel).
- Sertakan minimal 1 unit test untuk fungsi similarity.
- Jangan over-engineer. Prioritas: jalan, akurat, gampang dipahami.

---

## OUTPUT YANG GUE HARAPKAN DARI LU (AI AGENT)

1. Semua file project lengkap dengan isinya.
2. Penjelasan singkat cara jalanin dari nol.
3. Catatan limitation (misal: akurasi tergantung kualitas auto-caption, video tanpa caption otomatis di-skip).

---

## [ISI SENDIRI — sesuaikan sebelum submit]

- URL channel: `[GANTI dengan channel lu]`
- Threshold similarity: `[0.75 = ketat | 0.60 = longgar, lebih banyak kandidat]`
- Mau pakai stemming? `[true = akurat tapi lambat | false = cepat]`
- Bahasa caption: `[id / en / id,en]`

---

*Catatan teknis: ini deteksi berbasis transkrip teks. Dua video bisa beda footage tapi narasinya sama persis (re-upload audio sama) → ke-detect. Tapi kalau footage sama tapi tanpa caption sama sekali, butuh analisis visual (perceptual hashing frame) yang di luar scope sistem ini — bisa jadi fase lanjutan.*
