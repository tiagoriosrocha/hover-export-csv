#!/usr/bin/env python3
"""Exporta HoVer para CSV, resolvendo sentenças no corpus HotpotQA."""
from __future__ import annotations

import bz2
import csv
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DATA, CORPUS, OUTPUT = ROOT / "data", ROOT / "data/corpus/enwiki-20171001-pages-meta-current-withlinks-processed", ROOT / "processed-data"
FIELDS = ["id", "label", "split", "claim", "evidence_text", "evidence", "evidence_annotation_id", "evidence_id", "evidence_wiki_url", "evidence_sentence_id"]
TAG = re.compile(r"<[^>]+>")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def pages_for(items):
    titles = {title for item in items for title, _ in item.get("supporting_facts", [])}
    pages = {}
    for shard in CORPUS.rglob("*.bz2"):
        with bz2.open(shard, "rt", encoding="utf-8") as source:
            for line in source:
                page = json.loads(line)
                if page.get("title") in titles:
                    pages[page["title"]] = [TAG.sub("", s).strip() for paragraph in page["text"] for s in paragraph]
        if len(pages) == len(titles):
            return pages
    raise RuntimeError(f"Faltam {len(titles) - len(pages)} páginas de evidência no corpus.")


def make_row(item, split, pages):
    facts = item.get("supporting_facts", [])
    ids = [f"{title}::sentence::{sentence}" for title, sentence in facts]
    texts = [pages[title][sentence] for title, sentence in facts]
    titles = list(dict.fromkeys(title for title, _ in facts))
    return {
        "id": item["uid"], "label": item.get("label", ""), "split": split, "claim": item["claim"],
        "evidence_text": json.dumps([{"set_id": 0, "text": texts}], ensure_ascii=False),
        "evidence": json.dumps({"supporting_facts": facts, "num_hops": item.get("num_hops")}, ensure_ascii=False),
        "evidence_annotation_id": "[0]", "evidence_id": json.dumps(ids, ensure_ascii=False),
        "evidence_wiki_url": json.dumps(["https://en.wikipedia.org/wiki/" + quote(t.replace(" ", "_")) for t in titles]),
        "evidence_sentence_id": json.dumps(ids, ensure_ascii=False),
    }


def write(name, rows):
    with (OUTPUT / name).open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    train, dev = load("hover_train_release_v1.1.json"), load("hover_dev_release_v1.1.json")
    pages = pages_for(train + dev)
    OUTPUT.mkdir(exist_ok=True)
    train_rows = [make_row(item, "train", pages) for item in train]
    dev_rows = [make_row(item, "dev", pages) for item in dev]
    write("train.csv", train_rows)
    write("dev.csv", dev_rows)
    write("hover_dataset_full.csv", train_rows + dev_rows)
    print(f"Exportados {len(train_rows)} exemplos de treino e {len(dev_rows)} de desenvolvimento em {OUTPUT}")


if __name__ == "__main__":
    main()
