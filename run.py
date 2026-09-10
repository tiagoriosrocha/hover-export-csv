#!/usr/bin/env python3
"""Baixa HoVer e o corpus HotpotQA oficial, depois executa o exportador."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CORPUS_DIR = DATA / "corpus" / "enwiki-20171001-pages-meta-current-withlinks-processed"
FILES = {
    "hover_train_release_v1.1.json": "https://raw.githubusercontent.com/hover-nlp/hover/main/data/hover/hover_train_release_v1.1.json",
    "hover_dev_release_v1.1.json": "https://raw.githubusercontent.com/hover-nlp/hover/main/data/hover/hover_dev_release_v1.1.json",
    "hover_test_release_v1.1.json": "https://raw.githubusercontent.com/hover-nlp/hover/main/data/hover/hover_test_release_v1.1.json",
}
CORPUS_URL = "https://nlp.stanford.edu/projects/hotpotqa/enwiki-20171001-pages-meta-current-withlinks-processed.tar.bz2"


def download(url: str, path: Path) -> None:
    part = path.with_suffix(path.suffix + ".part")
    print(f"Baixando {path.name}...")
    try:
        urllib.request.urlretrieve(url, part)
        part.replace(path)
    except Exception:
        part.unlink(missing_ok=True)
        raise


def ensure_data() -> None:
    DATA.mkdir(exist_ok=True)
    for name, url in FILES.items():
        target = DATA / name
        if target.is_file() and target.stat().st_size:
            print(f"Encontrado: {name}")
        else:
            download(url, target)
    if CORPUS_DIR.is_dir():
        print("Encontrado: corpus Wikipedia do HotpotQA")
        return
    archive = DATA / "hotpotqa-wikipedia.tar.bz2"
    if not archive.is_file() or not archive.stat().st_size:
        download(CORPUS_URL, archive)
    required, available = archive.stat().st_size * 2, shutil.disk_usage(DATA).free
    if available < required:
        raise RuntimeError(f"Espaço insuficiente: reserve {required / 1024**3:.1f} GiB; há {available / 1024**3:.1f} GiB livres.")
    print("Extraindo corpus Wikipedia do HotpotQA...")
    (DATA / "corpus").mkdir(exist_ok=True)
    with tarfile.open(archive, "r:bz2") as source:
        source.extractall(DATA / "corpus", filter="data")
    archive.unlink()


if __name__ == "__main__":
    ensure_data()
    subprocess.run([sys.executable, str(ROOT / "export_graph_ready_csv.py")], check=True)
