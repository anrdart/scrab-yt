import sys

import click

from ytdupe.utils import ensure_dirs, load_config, load_metadata, setup_logging


@click.group()
def cli():
    pass


@cli.command()
@click.option("--channel", required=True, help="URL channel YouTube")
@click.option("--config", "config_path", default="config.yaml", help="Path file konfigurasi")
def download(channel, config_path):
    channel = channel.strip()
    if not channel:
        raise click.BadParameter("URL channel wajib diisi", param_hint="--channel")

    config = load_config(config_path)
    config["channel_url"] = channel
    logger = setup_logging()
    ensure_dirs(config)

    from ytdupe.downloader import download_subtitles

    logger.info("Memulai download subtitle dari: %s", channel)
    result = download_subtitles(
        channel_url=config["channel_url"],
        lang_priority=config["languages"],
        output_dir=config["subtitle_dir"],
        sleep_interval=config["sleep_interval"],
    )

    click.echo(f"\nSelesai!")
    click.echo(f"  Berhasil: {len(result['success'])} video")
    click.echo(f"  Gagal: {len(result['failed'])} video")

    if result["failed"]:
        click.echo("\nVideo gagal:")
        for vid, err in result["failed"][:10]:
            click.echo(f"  {vid}: {err}")
        if len(result["failed"]) > 10:
            click.echo(f"  ... dan {len(result['failed']) - 10} lainnya")


@cli.command()
@click.option("--threshold", default=None, type=click.FloatRange(0, 1), help="Similarity threshold (0-1)")
@click.option("--metadata", default=None, help="Path file CSV metadata YouTube Studio")
@click.option("--config", "config_path", default="config.yaml", help="Path file konfigurasi")
def analyze(threshold, metadata, config_path):
    config = load_config(config_path)
    logger = setup_logging()
    ensure_dirs(config)

    if threshold is not None:
        config["similarity_threshold"] = threshold

    from ytdupe.parser import parse_all_subtitles
    from ytdupe.preprocess import normalize_transcripts
    from ytdupe.similarity import (
        build_tfidf_matrix,
        cluster_duplicates,
        compute_similarity_matrix,
        find_duplicates,
    )
    from ytdupe.reporter import generate_report

    logger.info("Memulai analisis duplikat...")

    transcripts = parse_all_subtitles(config["subtitle_dir"])
    if not transcripts:
        click.echo("Error: Tidak ada subtitle ditemukan di %s" % config["subtitle_dir"])
        click.echo("Jalankan 'ytdupe download --channel <URL>' terlebih dahulu.")
        sys.exit(1)

    click.echo(f"Ditemukan {len(transcripts)} transkrip")

    normalized = normalize_transcripts(transcripts, use_stemming=config["use_stemming"])
    if not normalized:
        click.echo("Error: Semua transkrip kosong setelah preprocessing")
        sys.exit(1)

    click.echo("Membangun TF-IDF matrix...")
    tfidf_matrix, vectorizer, video_ids = build_tfidf_matrix(normalized)

    click.echo("Menghitung similarity matrix...")
    sim_matrix = compute_similarity_matrix(tfidf_matrix)

    metadata_df = load_metadata(metadata) if metadata else load_metadata("")

    click.echo(f"Mencari duplikat (threshold={config['similarity_threshold']})...")
    pairs = find_duplicates(
        sim_matrix,
        video_ids,
        threshold=config["similarity_threshold"],
        exclude_series=config["exclude_series"],
        metadata=metadata_df,
    )

    click.echo("Mengelompokkan cluster duplikat...")
    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata_df)

    output_path = generate_report(
        output_path=config["output_file"],
        transcripts=transcripts,
        clusters=clusters,
        metadata=metadata_df,
        similarity_matrix=sim_matrix,
        video_ids=video_ids,
        config=config,
    )

    total_dupes = sum(c["cluster_size"] - 1 for c in clusters)
    click.echo(f"\nHasil Analisis:")
    click.echo(f"  Total video dianalisis: {len(transcripts)}")
    click.echo(f"  Cluster duplikat: {len(clusters)}")
    click.echo(f"  Video duplikat: {total_dupes}")
    click.echo(f"  Laporan: {output_path}")


@cli.command(name="all")
@click.option("--channel", required=True, help="URL channel YouTube")
@click.option("--threshold", default=None, type=click.FloatRange(0, 1), help="Similarity threshold (0-1)")
@click.option("--metadata", default=None, help="Path file CSV metadata YouTube Studio")
@click.option("--config", "config_path", default="config.yaml", help="Path file konfigurasi")
def run_all(channel, threshold, metadata, config_path):
    channel = channel.strip()
    if not channel:
        raise click.BadParameter("URL channel wajib diisi", param_hint="--channel")

    config = load_config(config_path)
    config["channel_url"] = channel
    logger = setup_logging()
    ensure_dirs(config)

    if threshold is not None:
        config["similarity_threshold"] = threshold

    from ytdupe.downloader import download_subtitles
    from ytdupe.parser import parse_all_subtitles
    from ytdupe.preprocess import normalize_transcripts
    from ytdupe.similarity import (
        build_tfidf_matrix,
        cluster_duplicates,
        compute_similarity_matrix,
        find_duplicates,
    )
    from ytdupe.reporter import generate_report

    logger.info("=== MEMULAI DOWNLOAD + ANALISIS ===")

    click.echo("Tahap 1: Download subtitle...")
    result = download_subtitles(
        channel_url=config["channel_url"],
        lang_priority=config["languages"],
        output_dir=config["subtitle_dir"],
        sleep_interval=config["sleep_interval"],
    )
    click.echo(f"  Berhasil: {len(result['success'])}, Gagal: {len(result['failed'])}")

    click.echo("\nTahap 2: Analisis duplikat...")
    transcripts = parse_all_subtitles(config["subtitle_dir"])
    if not transcripts:
        click.echo("Error: Tidak ada transkrip ditemukan")
        sys.exit(1)

    click.echo(f"  Ditemukan {len(transcripts)} transkrip")

    normalized = normalize_transcripts(transcripts, use_stemming=config["use_stemming"])
    if not normalized:
        click.echo("Error: Semua transkrip kosong setelah preprocessing")
        sys.exit(1)

    click.echo("  Membangun TF-IDF matrix...")
    tfidf_matrix, vectorizer, video_ids = build_tfidf_matrix(normalized)

    click.echo("  Menghitung similarity...")
    sim_matrix = compute_similarity_matrix(tfidf_matrix)

    metadata_df = load_metadata(metadata) if metadata else load_metadata("")

    click.echo(f"  Mencari duplikat (threshold={config['similarity_threshold']})...")
    pairs = find_duplicates(
        sim_matrix,
        video_ids,
        threshold=config["similarity_threshold"],
        exclude_series=config["exclude_series"],
        metadata=metadata_df,
    )

    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata_df)

    output_path = generate_report(
        output_path=config["output_file"],
        transcripts=transcripts,
        clusters=clusters,
        metadata=metadata_df,
        similarity_matrix=sim_matrix,
        video_ids=video_ids,
        config=config,
    )

    total_dupes = sum(c["cluster_size"] - 1 for c in clusters)
    click.echo(f"\n=== SELESAI ===")
    click.echo(f"  Total video dianalisis: {len(transcripts)}")
    click.echo(f"  Cluster duplikat: {len(clusters)}")
    click.echo(f"  Video duplikat: {total_dupes}")
    click.echo(f"  Laporan disimpan: {output_path}")


# Entry point for setup.py/pyproject.toml: console_scripts = ["ytdupe=ytdupe.cli:cli"]
