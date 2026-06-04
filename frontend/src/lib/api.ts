export interface AnalysisSummary {
  id: string;
  channel_url: string;
  channel_name: string;
  status: string;
  total_videos: number;
  total_clusters: number;
  total_duplicates: number;
  created_at: string | null;
  finished_at: string | null;
}

export interface AnalysisDetail extends AnalysisSummary {
  progress: number;
  progress_message: string;
  threshold: number;
}

export interface ClusterVideo {
  video_id: string;
  status: string;
  similarity_to_primary: number;
  judul: string;
  tanggal_publikasi: string;
  durasi: string;
  penayangan: number;
}

export interface ClusterDetail {
  group_id: number;
  videos: ClusterVideo[];
  avg_similarity: number;
  cluster_size: number;
}

export interface TranscriptPreview {
  video_id: string;
  preview: string;
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function apiUrl(path: string): string {
  return `${API_BASE_URL}/api${path}`;
}

export async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail ?? err);
    throw new Error(detail || "Request failed");
  }
  return res.json();
}

export const createAnalysis = (data: {
  channel_url: string;
  threshold?: number;
  use_stemming?: boolean;
  exclude_series?: boolean;
}) => api<AnalysisDetail>("/analyses", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const listAnalyses = () => api<AnalysisSummary[]>("/analyses");

export const getAnalysis = (id: string) => api<AnalysisDetail>(`/analyses/${id}`);

export const getClusters = (id: string) => api<ClusterDetail[]>(`/analyses/${id}/clusters`);

export const getTranscripts = (id: string) => api<TranscriptPreview[]>(`/analyses/${id}/transcripts`);

export const uploadMetadata = (id: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return api<{ message: string }>(`/analyses/${id}/metadata`, { method: "POST", body: fd });
};

export const cancelAnalysis = (id: string) =>
  api<{ message: string }>(`/analyses/${id}/cancel`, { method: "POST" });

export const deleteAnalysis = (id: string) =>
  api<{ message: string }>(`/analyses/${id}`, { method: "DELETE" });
