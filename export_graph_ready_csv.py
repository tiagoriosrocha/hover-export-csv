#!/usr/bin/env python3
"""Exporta HoVer para CSV, resolvendo corretamente os supporting_facts no corpus HotpotQA.

Os sentence_ids do HoVer são aplicados ao parágrafo introdutório do artigo,
seguindo a segmentação do dump processado do HotpotQA. A página inteira não
é achatada em uma única lista de sentenças.
"""
from __future__ import annotations

import bz2
import csv
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DATA, CORPUS, OUTPUT = ROOT / "data", ROOT / "data/corpus/enwiki-20171001-pages-meta-current-withlinks-processed", ROOT / "processed-data"
FIELDS = ["id", "label", "split", "claim", "evidence_text", "evidence", "evidence_annotation_id", "evidence_id", "evidence_wiki_url", "evidence_sentence_id"]
TAG = re.compile(r"<[^>]+>")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def clean_sentence(text):
    """Remove hyperlinks HTML, preservando o texto visível."""
    return unescape(TAG.sub("", text)).strip()


def hotpot_intro_paragraph(page):
    """Retorna o parágrafo introdutório usado no HotpotQA.

    O dump completo armazena ``text`` como uma lista de parágrafos, e cada
    parágrafo como uma lista de sentenças. O primeiro bloco costuma conter
    apenas o título da página e NÃO corresponde à sentença 0 das anotações.

    O HotpotQA define seu parágrafo introdutório como o primeiro parágrafo
    com mais de 50 caracteres após a remoção dos hyperlinks. Os índices em
    ``supporting_facts`` são 0-based dentro desse parágrafo.
    """
    for paragraph_index, paragraph in enumerate(page.get("text", [])):
        sentences = [clean_sentence(sentence) for sentence in paragraph]
        sentences = [sentence for sentence in sentences if sentence]
        plain_paragraph = "".join(sentences).strip()
        if len(plain_paragraph) > 50:
            return {
                "paragraph_index": paragraph_index,
                "sentences": sentences,
            }
    return None


def pages_for(items):
    titles = {title for item in items for title, _ in item.get("supporting_facts", [])}
    pages = {}
    shards = list(CORPUS.rglob("*.bz2"))
    print(
        f"Procurando {len(titles):,} páginas de evidência em "
        f"{len(shards):,} arquivos do corpus...",
        flush=True,
    )

    for shard_number, shard in enumerate(shards, start=1):
        with bz2.open(shard, "rt", encoding="utf-8") as source:
            for line in source:
                page = json.loads(line)
                title = page.get("title")
                if title not in titles or title in pages:
                    continue

                intro = hotpot_intro_paragraph(page)
                if intro is not None:
                    pages[title] = intro

        if len(pages) == len(titles):
            print(
                f"Páginas de evidência localizadas ({len(pages):,}/{len(titles):,}).",
                flush=True,
            )
            return pages

        if shard_number % 250 == 0 or shard_number == len(shards):
            print(
                f"  Corpus: {shard_number:,}/{len(shards):,} arquivos; "
                f"{len(pages):,}/{len(titles):,} páginas localizadas.",
                flush=True,
            )

    missing = sorted(titles - pages.keys())
    preview = ", ".join(missing[:10])
    suffix = " ..." if len(missing) > 10 else ""
    print(
        f"Aviso: faltam {len(missing)} páginas de evidência no corpus: "
        f"{preview}{suffix}. Os exemplos afetados serão registrados em "
        f"{OUTPUT / 'unresolved_evidence.csv'}.",
        flush=True,
    )
    return pages


def make_row(item, split, pages):
    facts = item.get("supporting_facts", [])
    ids = [f"{title}::sentence::{sentence}" for title, sentence in facts]

    # O sentence_id do HoVer/HotpotQA é 0-based dentro do parágrafo
    # introdutório selecionado, e não na página inteira.
    invalid = []
    for title, sentence in facts:
        page = pages.get(title)
        sentence_count = len(page["sentences"]) if page else 0
        if (
            page is None
            or not isinstance(sentence, int)
            or isinstance(sentence, bool)
            or sentence < 0
            or sentence >= sentence_count
        ):
            invalid.append((title, sentence, sentence_count))

    if invalid:
        return None, invalid

    texts = [
        pages[title]["sentences"][sentence]
        for title, sentence in facts
    ]
    titles = list(dict.fromkeys(title for title, _ in facts))

    return {
        "id": item["uid"],
        "label": item.get("label", ""),
        "split": split,
        "claim": item["claim"],
        "evidence_text": json.dumps(
            [{"set_id": 0, "text": texts}],
            ensure_ascii=False,
        ),
        "evidence": json.dumps(
            {
                "supporting_facts": facts,
                "num_hops": item.get("num_hops"),
            },
            ensure_ascii=False,
        ),
        "evidence_annotation_id": "[0]",
        "evidence_id": json.dumps(ids, ensure_ascii=False),
        "evidence_wiki_url": json.dumps(
            [
                "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))
                for title in titles
            ],
            ensure_ascii=False,
        ),
        "evidence_sentence_id": json.dumps(ids, ensure_ascii=False),
    }, []


def write(name, rows):
    with (OUTPUT / name).open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def make_rows(items, split, pages):
    rows, unresolved = [], []
    for item in items:
        row, invalid = make_row(item, split, pages)
        if row is None:
            unresolved.append({
                "id": item["uid"],
                "split": split,
                "claim": item["claim"],
                "invalid_supporting_facts": json.dumps(invalid, ensure_ascii=False),
            })
        else:
            rows.append(row)
    return rows, unresolved


def main():
    train, dev = load("hover_train_release_v1.1.json"), load("hover_dev_release_v1.1.json")
    pages = pages_for(train + dev)
    OUTPUT.mkdir(exist_ok=True)
    train_rows, train_unresolved = make_rows(train, "train", pages)
    dev_rows, dev_unresolved = make_rows(dev, "dev", pages)
    write("train.csv", train_rows)
    write("dev.csv", dev_rows)
    write("hover_dataset_full.csv", train_rows + dev_rows)
    unresolved = train_unresolved + dev_unresolved
    if unresolved:
        report = OUTPUT / "unresolved_evidence.csv"
        with report.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=unresolved[0].keys())
            writer.writeheader()
            writer.writerows(unresolved)
        print(f"{len(unresolved)} exemplos com evidência incompatível foram excluídos; detalhes em {report}")
    print(f"Exportados {len(train_rows)} exemplos de treino e {len(dev_rows)} de desenvolvimento em {OUTPUT}")


if __name__ == "__main__":
    main()
