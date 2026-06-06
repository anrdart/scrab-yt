import logging
import os
from io import BytesIO
from typing import Callable

import numpy as np

logger = logging.getLogger("ytdupe.worker")

THUMB_URL = "https://img.youtube.com/vi/{video_id}/mqdefault.jpg"


def download_thumbnails(
    video_ids: list[str],
    output_dir: str,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, str]:
    import httpx

    os.makedirs(output_dir, exist_ok=True)
    results: dict[str, str] = {}
    total = len(video_ids)

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for idx, video_id in enumerate(video_ids, 1):
            if on_progress:
                on_progress(idx, total, video_id)

            path = os.path.join(output_dir, f"{video_id}.jpg")
            if os.path.exists(path):
                results[video_id] = path
                continue

            try:
                resp = client.get(THUMB_URL.format(video_id=video_id))
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(resp.content)
                results[video_id] = path
            except Exception as e:
                logger.warning("Thumbnail download failed for %s: %s", video_id, e)

    logger.info("Downloaded %d/%d thumbnails", len(results), total)
    return results


def compute_thumbnail_hashes(thumbnail_paths: dict[str, str]) -> dict[str, object]:
    import imagehash
    from PIL import Image

    hashes: dict[str, object] = {}
    for video_id, path in thumbnail_paths.items():
        try:
            img = Image.open(path)
            hashes[video_id] = imagehash.phash(img)
        except Exception as e:
            logger.warning("Hash failed for %s: %s", video_id, e)

    logger.info("Computed %d thumbnail hashes", len(hashes))
    return hashes


def compute_thumbnail_similarity_matrix(
    hashes: dict[str, object],
    video_ids: list[str],
    threshold: float = 0.85,
) -> tuple[np.ndarray, list[dict]]:
    n = len(video_ids)
    sim_matrix = np.zeros((n, n), dtype=np.float64)
    pairs: list[dict] = []

    hash_list = [hashes.get(vid) for vid in video_ids]

    for i in range(n):
        for j in range(i + 1, n):
            h_a, h_b = hash_list[i], hash_list[j]
            if h_a is None or h_b is None:
                continue
            distance = h_a - h_b
            similarity = 1.0 - (distance / 64.0)
            sim_matrix[i][j] = similarity
            sim_matrix[j][i] = similarity

            if similarity >= threshold:
                pairs.append({
                    "video_id_a": video_ids[i],
                    "video_id_b": video_ids[j],
                    "similarity": round(similarity, 4),
                })

    logger.info("Thumbnail similarity: %d pairs >= %.2f threshold", len(pairs), threshold)
    return sim_matrix, pairs
