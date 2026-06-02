import numpy as np
import pandas as pd
import pytest

from ytdupe.parser import parse_all_subtitles
from ytdupe.similarity import (
    build_tfidf_matrix,
    cluster_duplicates,
    compute_similarity_matrix,
    find_duplicates,
)
from ytdupe.utils import load_metadata


def test_build_tfidf_matrix():
    transcripts = {
        "vid1": "sumur bor untuk desa terpencil air bersih",
        "vid2": "sumur bor bagi warga desa air bersih bersih",
        "vid3": "wakaf untuk pembangunan masjid baru",
    }
    matrix, vectorizer, video_ids = build_tfidf_matrix(transcripts)

    assert matrix.shape[0] == 3
    assert matrix.shape[1] > 0
    assert len(video_ids) == 3
    assert set(video_ids) == {"vid1", "vid2", "vid3"}


def test_build_tfidf_matrix_keeps_terms_shared_by_all_documents():
    transcripts = {
        "vid1": "sumur bor desa air bersih",
        "vid2": "sumur bor desa air bersih",
    }

    matrix, _, video_ids = build_tfidf_matrix(transcripts)

    assert matrix.shape[0] == 2
    assert matrix.shape[1] > 0
    assert video_ids == ["vid1", "vid2"]


def test_compute_similarity_matrix():
    transcripts = {
        "a": "kata satu dua tiga",
        "b": "kata satu dua empat",
        "c": "halo dunia baru",
    }
    matrix, _, video_ids = build_tfidf_matrix(transcripts)
    sim = compute_similarity_matrix(matrix)

    assert sim.shape == (3, 3)
    assert sim[0][0] == 0.0
    assert sim[0][1] > sim[0][2]


def test_find_duplicates_basic():
    video_ids = ["v0", "v1", "v2", "v3"]
    sim_matrix = np.array([
        [0.0, 0.9, 0.3, 0.2],
        [0.9, 0.0, 0.2, 0.1],
        [0.3, 0.2, 0.0, 0.85],
        [0.2, 0.1, 0.85, 0.0],
    ])

    pairs = find_duplicates(sim_matrix, video_ids, threshold=0.75)

    assert len(pairs) == 2
    pair_ids = {(p["video_id_a"], p["video_id_b"]) for p in pairs}
    assert ("v0", "v1") in pair_ids
    assert ("v2", "v3") in pair_ids


def test_find_duplicates_excludes_series():
    video_ids = ["v0", "v1"]
    sim_matrix = np.array([
        [0.0, 0.9],
        [0.9, 0.0],
    ])
    metadata = pd.DataFrame({
        "video_id": ["v0", "v1"],
        "judul": ["Wakaf hari ke-1", "Wakaf hari ke-2"],
    })

    pairs = find_duplicates(
        sim_matrix, video_ids, threshold=0.75,
        exclude_series=True, metadata=metadata,
    )

    assert len(pairs) == 0


def test_find_duplicates_same_series_number_not_excluded():
    video_ids = ["v0", "v1"]
    sim_matrix = np.array([
        [0.0, 0.9],
        [0.9, 0.0],
    ])
    metadata = pd.DataFrame({
        "video_id": ["v0", "v1"],
        "judul": ["Wakaf hari ke-1", "Wakaf hari ke-1 ulang"],
    })

    pairs = find_duplicates(
        sim_matrix, video_ids, threshold=0.75,
        exclude_series=True, metadata=metadata,
    )

    assert len(pairs) == 1


def test_cluster_duplicates_transitive():
    pairs = [
        {"video_id_a": "a", "video_id_b": "b", "similarity": 0.9},
        {"video_id_a": "b", "video_id_b": "c", "similarity": 0.85},
    ]
    video_ids = ["a", "b", "c", "d"]

    clusters = cluster_duplicates(pairs, video_ids)

    assert len(clusters) == 1
    assert clusters[0]["cluster_size"] == 3
    member_ids = {v["video_id"] for v in clusters[0]["videos"]}
    assert member_ids == {"a", "b", "c"}


def test_cluster_duplicates_picks_highest_views_as_primary():
    pairs = [
        {"video_id_a": "a", "video_id_b": "b", "similarity": 0.9},
    ]
    video_ids = ["a", "b"]
    metadata = pd.DataFrame({
        "video_id": ["a", "b"],
        "penayangan": [100, 500],
    })

    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata)

    assert len(clusters) == 1
    primary = [v for v in clusters[0]["videos"] if v["status"] == "PRIMARY"]
    assert len(primary) == 1
    assert primary[0]["video_id"] == "b"


def test_cluster_duplicates_handles_string_views_as_primary():
    pairs = [
        {"video_id_a": "a", "video_id_b": "b", "similarity": 0.9},
    ]
    video_ids = ["a", "b"]
    metadata = pd.DataFrame({
        "video_id": ["a", "b"],
        "penayangan": ["1.000", "500"],
    })

    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata)

    primary = [v for v in clusters[0]["videos"] if v["status"] == "PRIMARY"]
    assert primary[0]["video_id"] == "a"


def test_cluster_duplicates_empty():
    clusters = cluster_duplicates([], ["a", "b"])
    assert clusters == []


def test_load_metadata_accepts_csv_without_views(tmp_path):
    csv_path = tmp_path / "metadata.csv"
    csv_path.write_text("Konten,Judul video\nabc123,Video A\n", encoding="utf-8")

    df = load_metadata(str(csv_path))

    assert list(df["video_id"]) == ["abc123"]
    assert int(df.iloc[0]["penayangan"]) == 0


def test_load_metadata_parses_indonesian_thousands(tmp_path):
    csv_path = tmp_path / "metadata.csv"
    csv_path.write_text("Konten,Penayangan\nabc123,1.234\n", encoding="utf-8")

    df = load_metadata(str(csv_path))

    assert int(df.iloc[0]["penayangan"]) == 1234


def test_parse_all_subtitles_strips_language_suffix(tmp_path):
    subtitle_path = tmp_path / "abc123.id-orig.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHalo dunia\n",
        encoding="utf-8",
    )

    transcripts = parse_all_subtitles(str(tmp_path))

    assert transcripts == {"abc123": "Halo dunia"}
