# Design — ytdupe: Sistem Deteksi Duplikat Konten YouTube

**Tanggal:** 2026-06-01
**Status:** Disetujui (brainstorming)

## Tujuan

CLI Python bernama `ytdupe` untuk mendeteksi duplikasi konten YouTube di **level transkrip/isi** (bukan judul). Target user: tim digital advertising non-engineer. Bisa dijalankan dengan 1–2 command.

Use case utama: channel donasi/wakaf Islami (~700 video, banyak Shorts, sering re-upload dengan ganti judul). Deteksi pasangan video yang isinya mirip walau judulnya beda.

## Keputusan Konfigurasi (dari brainstorming)

| Parameter | Nilai | Alasan |
|-----------|-------|--------|
| `similarity_threshold` | **0.60** (longgar) | Auto-caption kualitas bervariasi; lebih banyak kandidat untuk review manual |
| `use_stemming` | **true** | Akurasi matching lebih tinggi (varian kata jadi sama); user terima trade-off lambat |
| `languages` | **["id", "en"]** | Prioritas caption Indonesia, fallback English |
| metadata CSV | **belum ada** | Sistem jalan tanpa CSV; bisa tambah via `--metadata` nanti |
| `exclude_series` | **true** | Skip pasangan seri "hari ke-X" yang angkanya beda |

## Lingkungan & Risiko Teknis

- **Python 3.14.5** satu-satunya versi tersedia di sistem (tidak ada 3.10–3.13). pip 26.1.1 via ensurepip OK. Tidak ada uv/pipx.
- **Risiko:** `scikit-learn`/`scipy`/`Sastrawi` butuh wheel untuk 3.14. Kemungkinan besar tersedia, tapi kalau gagal build → fallback.
- **Mitigasi:** Buat venv, install dependencies, verifikasi import di awal (langkah pertama implementasi). Kalau `scikit-learn` gagal total: implementasi TF-IDF + cosine pure-Python (numpy + math) sebagai fallback. Diputuskan saat install nyata.

## Arsitektur

CLI berbasis **Click**, tiga command. yt-dlp dipanggil via **subprocess** (lebih robust untuk bulk, isolasi crash per-video, mudah handle rate-limit).

```
ytdupe/
├── README.md                 # Bahasa Indonesia, step-by-step untuk non-teknis
├── requirements.txt
├── config.yaml               # semua setting
├── pyproject.toml            # agar `ytdupe` jadi command + pytest config
├── ytdupe/
│   ├── __init__.py
│   ├── cli.py                # entry point: download / analyze / all
│   ├── downloader.py         # wrapper yt-dlp (subprocess)
│   ├── parser.py             # VTT/SRT -> teks bersih
│   ├── preprocess.py         # normalisasi + stopword + stemming (id)
│   ├── similarity.py         # TF-IDF + cosine + clustering
│   ├── reporter.py           # Excel multi-sheet
│   └── utils.py              # config loader, logging, helpers
├── data/
│   ├── subtitles/            # hasil download .vtt
│   └── output/               # hasil Excel
└── tests/
    ├── test_similarity.py
    └── test_parser.py
```

## Komponen (per modul)

### `utils.py`
- `load_config(path) -> dict` — baca `config.yaml`, merge dengan default. Error kalau malformed.
- `setup_logging()` — logging ke `ytdupe.log` + console.
- Helper path (pastikan `data/subtitles`, `data/output` ada).

### `downloader.py`
- `download_subtitles(channel_url, lang_priority, output_dir, sleep_interval) -> dict` dengan `{"ok": [ids], "failed": [ids]}`.
- yt-dlp via subprocess. Flags: `--write-auto-sub`, `--write-sub`, `--skip-download`, `--sub-format vtt`, `--sub-langs` dari `lang_priority`, output template `%(id)s.%(ext)s`, `--sleep-interval`.
- Try/except per proses; rate-limit (429) → log + lanjut. Tidak crash seluruh proses.

### `parser.py`
- `parse_vtt(filepath) -> str` — ekstrak teks murni: buang header `WEBVTT`, timestamp, tag `<c>`/`align:`/posisi, dedupe baris berurutan (auto-caption sering ngulang).
- `load_transcripts(subtitle_dir) -> dict[str, str]` — `{video_id: transcript}`. Skip file kosong/parse gagal (log).
- Dukung `.vtt` (utama) dan `.srt`.

### `preprocess.py`
- `normalize(text) -> str` — lowercase, hapus tanda baca, hapus angka berdiri sendiri, collapse spasi.
- `remove_stopwords(text)` — stopword Bahasa Indonesia (Sastrawi kalau ada, fallback list custom).
- `stem(text)` — Sastrawi `StemmerFactory` kalau `use_stemming=true`. Lazy-init (mahal).
- `preprocess(text, use_stemming) -> str` — pipeline gabungan.

### `similarity.py`
- `build_tfidf(transcripts) -> (matrix, ids)` — `TfidfVectorizer(ngram_range=(1,2))`.
- `cosine_matrix(matrix)` — cosine similarity antar semua.
- `find_duplicates(sim_matrix, ids, threshold, titles, exclude_series) -> list[pair]` — pasangan ≥ threshold; kalau `exclude_series` skip pasangan dengan pola `hari ke-X`/`day-X` angka beda.
- `cluster_duplicates(pairs, ids) -> list[cluster]` — connected components (transitif: A≈B, B≈C → grup A-B-C).
- `mark_primary(cluster, metadata, transcripts)` — PRIMARY = penayangan tertinggi kalau ada metadata, else transkrip terpanjang. Sisanya DUPLIKAT.

### `reporter.py`
Excel `.xlsx` via openpyxl. Font Arial, header navy `1F3864` teks putih, border tipis, freeze panes, auto-filter. Angka `#,##0`. Zero formula error.
- **Sheet `Ringkasan`** — total video dianalisis, jumlah cluster, total video duplikat, threshold, tanggal generate, rekomendasi action.
- **Sheet `Duplikat Konten`** — per cluster: Group ID, Status (PRIMARY hijau `C6EFCE` / DUPLIKAT merah `FFC7CE`), Video ID, Judul, Tanggal, Durasi, Penayangan, Similarity Score.
- **Sheet `Matriks Similarity`** (opsional, ≤100 video) — heatmap conditional formatting color scale.
- **Sheet `Transkrip`** — video ID + 200 karakter pertama transkrip.

### `cli.py`
Click group, tiga command:
```bash
ytdupe download --channel <URL>
ytdupe analyze --threshold 0.60 [--metadata <path.csv>]
ytdupe all --channel <URL> --threshold 0.60 [--metadata <path.csv>]
```
Semua param default dari `config.yaml`, override via flag. Progress bar `tqdm` tiap tahap.

### Metadata (CSV YouTube Studio)
Format `Data tabel.csv`: kolom `Konten` = video ID. Param `--metadata`. Multi-CSV → gabung & dedupe by video ID, ambil baris penayangan tertinggi. Tanpa CSV: kolom judul = video ID, PRIMARY by transkrip terpanjang.

## Data Flow

```
channel URL
  └─(download)→ data/subtitles/<id>.vtt
       └─(parse)→ {id: transcript}
            └─(preprocess)→ {id: clean_text}
                 └─(tfidf+cosine)→ sim_matrix
                      └─(threshold+cluster)→ clusters [PRIMARY/DUPLIKAT]
                           └─(+metadata CSV opsional)→ reporter
                                └→ data/output/laporan_duplikat_konten.xlsx
```

## Error Handling

- Semua I/O try/except: file gak ada, subtitle kosong, CSV malformed.
- Download: per-video isolasi, 429 → log + lanjut.
- Video tanpa caption → auto-skip (log).
- Logging modul `logging` → `ytdupe.log` + console.

## Testing

- `test_similarity.py` — transkrip sintetis dengan duplikat yang diketahui → assert cluster benar; test threshold; test exclude_series.
- `test_parser.py` — sample VTT string → assert teks bersih (no timestamp/tag, no baris dobel).
- pytest. Tidak perlu network (mock/sample data).

## config.yaml

```yaml
channel_url: "https://www.youtube.com/@Gerakanwakafsumur/videos"
languages: ["id", "en"]
sleep_interval: 2
similarity_threshold: 0.60
use_stemming: true
exclude_series: true
output_file: "data/output/laporan_duplikat_konten.xlsx"
subtitle_dir: "data/subtitles"
```

## Limitations (untuk README)

- Akurasi tergantung kualitas auto-caption YouTube.
- Video tanpa caption sama sekali → di-skip (tidak terdeteksi).
- Deteksi berbasis teks: re-upload dengan footage beda tapi narasi sama → ke-detect. Footage sama tanpa caption → butuh perceptual hashing (di luar scope).
- Stemming `true` = lebih lambat di 700 video.

## Non-Goals (YAGNI)

- Analisis visual/frame hashing.
- Database/persistensi selain file.
- Web UI / API server.
- Multi-channel sekaligus dalam satu run.
