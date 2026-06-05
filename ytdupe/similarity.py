import logging
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("ytdupe")

SERIES_PATTERN = re.compile(
    r"(hari\s*ke\s*[-]?\s*\d+|day\s*[-_]?\s*\d+|bagian\s*[-]?\s*\d+|"
    r"part\s*[-_]?\s*\d+|eps\s*\.?\s*\d+|episode\s*[-]?\s*\d+)",
    re.IGNORECASE,
)
SERIES_NUMBER_RE = re.compile(r"(\d+)")


def build_tfidf_matrix(transcripts: dict[str, str]):
    video_ids = list(transcripts.keys())
    texts = [transcripts[vid] for vid in video_ids]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=10000,
        min_df=1,
        max_df=1.0,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    logger.info(
        "TF-IDF matrix: %d video x %d fitur", tfidf_matrix.shape[0], tfidf_matrix.shape[1]
    )
    return tfidf_matrix, vectorizer, video_ids


def compute_similarity_matrix(tfidf_matrix) -> np.ndarray:
    sim_matrix = cosine_similarity(tfidf_matrix)
    np.fill_diagonal(sim_matrix, 0.0)
    return sim_matrix


def _is_series_pair(title_a: str, title_b: str) -> bool:
    match_a = SERIES_PATTERN.search(title_a)
    match_b = SERIES_PATTERN.search(title_b)

    if not match_a or not match_b:
        return False

    num_a_match = SERIES_NUMBER_RE.search(match_a.group(1))
    num_b_match = SERIES_NUMBER_RE.search(match_b.group(1))

    if not num_a_match or not num_b_match:
        return False

    return num_a_match.group(1) != num_b_match.group(1)


def _title_similarity(title_a: str, title_b: str) -> float:
    words_a = set(title_a.lower().split())
    words_b = set(title_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def find_duplicates(
    similarity_matrix: np.ndarray,
    video_ids: list[str],
    threshold: float = 0.75,
    exclude_series: bool = True,
    metadata: pd.DataFrame | None = None,
    mode: str = "duplicate",
) -> list[dict]:
    pairs = []
    n = len(video_ids)

    for i in range(n):
        for j in range(i + 1, n):
            score = float(similarity_matrix[i][j])
            if score >= threshold:
                vid_a = video_ids[i]
                vid_b = video_ids[j]

                if metadata is not None and not metadata.empty:
                    title_a = _get_title(metadata, vid_a)
                    title_b = _get_title(metadata, vid_b)

                    if exclude_series and title_a and title_b and _is_series_pair(title_a, title_b):
                        continue

                    if mode == "repost" and title_a and title_b:
                        if _title_similarity(title_a, title_b) >= 0.5:
                            continue

                pairs.append(
                    {
                        "video_id_a": vid_a,
                        "video_id_b": vid_b,
                        "similarity": score,
                    }
                )

    logger.info("Ditemukan %d pasangan duplikat (threshold=%.2f, mode=%s)", len(pairs), threshold, mode)
    return pairs


def _get_title(metadata: pd.DataFrame, video_id: str) -> str:
    if metadata is None or metadata.empty:
        return ""
    row = metadata[metadata["video_id"] == video_id]
    if row.empty:
        return ""
    return str(row.iloc[0].get("judul", ""))


def cluster_duplicates(
    duplicate_pairs: list[dict],
    video_ids: list[str],
    metadata: pd.DataFrame | None = None,
) -> list[dict]:
    if not duplicate_pairs:
        return []

    parent = {vid: vid for vid in video_ids}
    rank = {vid: 0 for vid in video_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str):
        ra, rb = find(a), find(b)
        if ra != rb:
            if rank[ra] < rank[rb]:
                ra, rb = rb, ra
            parent[rb] = ra
            if rank[ra] == rank[rb]:
                rank[ra] += 1

    pair_similarity: dict[tuple[str, str], float] = {}
    for pair in duplicate_pairs:
        a, b, sim = pair["video_id_a"], pair["video_id_b"], pair["similarity"]
        union(a, b)
        key = (min(a, b), max(a, b))
        pair_similarity[key] = sim

    groups: dict[str, list[str]] = defaultdict(list)
    for vid in video_ids:
        root = find(vid)
        if root in parent:
            groups[root].append(vid)

    clusters = []
    group_id = 1
    for members in sorted(groups.values(), key=lambda g: len(g), reverse=True):
        if len(members) < 2:
            continue

        primary_id = _pick_primary(members, metadata)

        videos = []
        for vid in members:
            status = "PRIMARY" if vid == primary_id else "DUPLIKAT (review)"
            key = (min(primary_id, vid), max(primary_id, vid))
            sim_to_primary = pair_similarity.get(key, 1.0 if vid == primary_id else 0.0)
            videos.append(
                {
                    "video_id": vid,
                    "status": status,
                    "similarity_to_primary": round(sim_to_primary, 4),
                }
            )

        all_pairs_sim = [
            pair_similarity.get((min(a, b), max(a, b)), 0.0)
            for i, a in enumerate(members)
            for b in members[i + 1 :]
        ]
        avg_sim = float(np.mean(all_pairs_sim)) if all_pairs_sim else 0.0

        clusters.append(
            {
                "group_id": group_id,
                "videos": videos,
                "avg_similarity": round(avg_sim, 4),
                "cluster_size": len(members),
            }
        )
        group_id += 1

    logger.info("Ditemukan %d cluster duplikat", len(clusters))
    return clusters


def _pick_primary(members: list[str], metadata: pd.DataFrame | None) -> str:
    if metadata is None or metadata.empty:
        return sorted(members)[0]

    best_vid = members[0]
    best_views = -1

    for vid in members:
        row = metadata[metadata["video_id"] == vid]
        if not row.empty:
            views = _to_int(row.iloc[0].get("penayangan", 0))
            if views > best_views:
                best_views = views
                best_vid = vid

    return best_vid


def _to_int(value) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(str(value).replace(",", "").replace(".", "").strip())
    except (TypeError, ValueError):
        return 0
