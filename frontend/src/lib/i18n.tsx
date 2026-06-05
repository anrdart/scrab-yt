import { createContext, useContext, useState, type ReactNode } from "react";

export type Lang = "en" | "id";

const translations = {
  // Sidebar
  "nav.dashboard": { en: "Dashboard", id: "Dasbor" },
  "nav.newScan": { en: "New Scan", id: "Scan Baru" },

  // Dashboard
  "dashboard.title": { en: "Dashboard", id: "Dasbor" },
  "dashboard.subtitle": { en: "YouTube duplicate content detection summary", id: "Ringkasan deteksi duplikat konten YouTube" },
  "dashboard.kicker": { en: "scan archive", id: "arsip scan" },
  "dashboard.totalVideos": { en: "Total Videos", id: "Total Video" },
  "dashboard.clusters": { en: "Duplicate Clusters", id: "Cluster Duplikat" },
  "dashboard.duplicates": { en: "Duplicate Videos", id: "Video Duplikat" },
  "dashboard.history": { en: "History", id: "Riwayat" },
  "dashboard.noData": { en: "No analyses yet", id: "Belum ada analisis" },
  "dashboard.firstScan": { en: "Start your first scan", id: "Mulai scan pertama" },
  "dashboard.view": { en: "View", id: "Lihat" },
  "dashboard.delete": { en: "Delete", id: "Hapus" },
  "dashboard.cancel": { en: "Cancel", id: "Batal" },
  "dashboard.confirmDelete": { en: "Delete this analysis?", id: "Hapus analisis ini?" },
  "dashboard.confirmCancel": { en: "Cancel this analysis?", id: "Batalkan analisis ini?" },
  "dashboard.deleteFailed": { en: "Failed to delete", id: "Gagal menghapus" },
  "dashboard.cancelFailed": { en: "Failed to cancel", id: "Gagal membatalkan" },

  // Table headers
  "table.channel": { en: "Channel", id: "Channel" },
  "table.status": { en: "Status", id: "Status" },
  "table.videos": { en: "Videos", id: "Video" },
  "table.clusters": { en: "Clusters", id: "Cluster" },
  "table.duplicates": { en: "Duplicates", id: "Duplikat" },
  "table.date": { en: "Date", id: "Tanggal" },
  "table.video": { en: "Video", id: "Video" },
  "table.views": { en: "Views", id: "Tayangan" },
  "table.similarity": { en: "Similarity", id: "Kemiripan" },
  "table.mode": { en: "Mode", id: "Mode" },

  // Status
  "status.done": { en: "Done", id: "Selesai" },
  "status.running": { en: "Running", id: "Berjalan" },
  "status.failed": { en: "Failed", id: "Gagal" },
  "status.cancelled": { en: "Cancelled", id: "Dibatalkan" },
  "status.pending": { en: "Queued", id: "Antrian" },
  "status.primary": { en: "Primary", id: "Utama" },
  "status.duplicate": { en: "Duplicate", id: "Duplikat" },

  // New Analysis
  "new.kicker": { en: "analysis setup", id: "pengaturan analisis" },
  "new.title": { en: "New Scan", id: "Scan Baru" },
  "new.subtitle": { en: "Enter YouTube channel URL to detect duplicate content", id: "Masukkan URL channel YouTube untuk deteksi duplikat konten" },
  "new.channelUrl": { en: "Channel URL", id: "URL Channel" },
  "new.channelPlaceholder": { en: "https://www.youtube.com/@ChannelName/videos", id: "https://www.youtube.com/@NamaChannel/videos" },
  "new.mode": { en: "Detection Mode", id: "Mode Deteksi" },
  "new.modeDuplicate": { en: "Duplicate Content", id: "Konten Duplikat" },
  "new.modeRepost": { en: "Repost Detection", id: "Deteksi Repost" },
  "new.modeDuplicateDesc": { en: "Find videos with similar transcripts (same content)", id: "Cari video dengan transkrip serupa (konten sama)" },
  "new.modeRepostDesc": { en: "Find videos with similar content but different titles (reposts)", id: "Cari video dengan konten sama tapi judul berbeda (repost)" },
  "new.threshold": { en: "Similarity Threshold", id: "Ambang Kemiripan" },
  "new.thresholdLoose": { en: "Loose", id: "Longgar" },
  "new.thresholdNormal": { en: "Normal", id: "Normal" },
  "new.thresholdStrict": { en: "Strict", id: "Ketat" },
  "new.thresholdVeryStrict": { en: "Very Strict", id: "Sangat Ketat" },
  "new.thresholdMore": { en: "more candidates", id: "lebih banyak kandidat" },
  "new.thresholdIdentical": { en: "near-identical", id: "hampir identik" },
  "new.excludeSeries": { en: "Exclude video series", id: "Kecualikan seri video" },
  "new.excludeSeriesDesc": { en: "Skip episode series (Day-1, Day-2, etc)", id: "Lewati seri episode (Hari ke-1, Hari ke-2, dll)" },
  "new.stemming": { en: "Indonesian stemming", id: "Stemming Indonesia" },
  "new.stemmingDesc": { en: "More accurate, slower processing", id: "Lebih akurat, proses lebih lambat" },
  "new.submit": { en: "Start Scan", id: "Mulai Scan" },
  "new.submitting": { en: "Starting...", id: "Memulai..." },
  "new.submitFailed": { en: "Failed to start analysis", id: "Gagal memulai analisis" },

  // Analysis Detail
  "detail.kicker": { en: "analysis detail", id: "detail analisis" },
  "detail.back": { en: "Back", id: "Kembali" },
  "detail.notFound": { en: "Analysis not found", id: "Analisis tidak ditemukan" },
  "detail.failed": { en: "Analysis failed", id: "Analisis gagal" },
  "detail.retry": { en: "Retry", id: "Coba Lagi" },
  "detail.cancelBtn": { en: "Cancel Analysis", id: "Batalkan Analisis" },
  "detail.cancelling": { en: "Cancelling...", id: "Membatalkan..." },
  "detail.confirmCancel": { en: "Cancel running analysis?", id: "Batalkan analisis yang sedang berjalan?" },
  "detail.uploadCsv": { en: "Upload CSV", id: "Upload CSV" },
  "detail.uploadFailed": { en: "Upload failed", id: "Upload gagal" },
  "detail.cancelFailed": { en: "Cancel failed", id: "Gagal membatalkan" },
  "detail.threshold": { en: "Threshold", id: "Ambang" },
  "detail.tabClusters": { en: "Clusters", id: "Cluster" },
  "detail.tabTranscripts": { en: "Transcripts", id: "Transkrip" },
  "detail.noDuplicates": { en: "No duplicates found", id: "Tidak ada duplikat" },
  "detail.allUnique": { en: "All {n} videos are unique (threshold {t})", id: "Semua {n} video unik (ambang {t})" },
  "detail.group": { en: "Group", id: "Grup" },
  "detail.videoCount": { en: "videos", id: "video" },

  // Progress stages
  "stage.downloadSubtitle": { en: "Download Subtitle", id: "Download Subtitle" },
  "stage.audioTranscription": { en: "Audio Transcription", id: "Transkripsi Audio" },
  "stage.parsePreprocess": { en: "Parse & Preprocess", id: "Parse & Preprocessing" },
  "stage.similarity": { en: "Similarity Analysis", id: "Analisis Kemiripan" },
  "stage.report": { en: "Generate Report", id: "Buat Laporan" },

  // Transcript table
  "transcript.videoId": { en: "Video ID", id: "ID Video" },
  "transcript.preview": { en: "Preview", id: "Pratinjau" },
} as const;

type TranslationKey = keyof typeof translations;

const I18nContext = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (key: TranslationKey, vars?: Record<string, string>) => string }>({
  lang: "id",
  setLang: () => {},
  t: (key) => key,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("ytdupe-lang") as Lang) || "id");

  const changeLang = (l: Lang) => {
    setLang(l);
    localStorage.setItem("ytdupe-lang", l);
  };

  const t = (key: TranslationKey, vars?: Record<string, string>) => {
    let text = translations[key]?.[lang] ?? key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        text = text.replace(`{${k}}`, v);
      }
    }
    return text;
  };

  return <I18nContext.Provider value={{ lang, setLang: changeLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
