#!/usr/bin/env python3
"""Read-only lexical retrieval of original reference cases, never held-out evals."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


def terms(text):
    ascii_terms = set(re.findall(r"[a-z0-9-]+", text.lower()))
    han = re.findall(r"[\u4e00-\u9fff]+", text)
    return ascii_terms | {s[i:i+2] for s in han for i in range(len(s)-1)} | set(han)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=4)
    parser.add_argument("--film", help="Optional film ID, e.g. F13")
    parser.add_argument("--topic", help="Optional topic substring")
    args = parser.parse_args()
    ref_root = Path(__file__).resolve().parents[1] / "references"
    query = terms(args.query)
    items = [json.loads(line) for filename in ["dialogue-examples.jsonl", "curated-cases.jsonl"] for line in (ref_root / filename).read_text(encoding="utf-8").splitlines() if line.strip()]
    document_terms = [terms(" ".join([item["id"], item.get("knowledge_card_id", ""), item["topic"], *item["tags"], item["user"], item["assistant"]])) for item in items]
    frequencies = Counter(term for document in document_terms for term in document)
    def weight(term):
        return math.log(1 + len(items) / (1 + frequencies[term]))
    rows = []
    for item in items:
        if args.film and args.film.upper() not in item.get("film_ids", []):
            continue
        if args.topic and args.topic not in item["topic"]:
            continue
        head = " ".join([item["id"], item.get("knowledge_card_id", ""), item["topic"], *item["tags"], item["user"]])
        score = 3 * sum(weight(term) for term in query & terms(head)) + sum(weight(term) for term in query & terms(item["assistant"]))
        if item.get("provenance") == "original_authored_dialogue_example" and score:
            score *= 1.3
        if args.query.strip().upper() == item["id"] or args.query.strip().upper() == item.get("knowledge_card_id"):
            score += 1000
        if score:
            rows.append((score, item))
    rows.sort(key=lambda row: (-row[0], row[1]["id"]))
    for score, item in rows[:max(0, min(args.top, 12))]:
        print(json.dumps({"retrieval_score": round(score, 3), **item}, ensure_ascii=False))
    if not rows:
        print("无关键词匹配；请用主题词检索，或读取 methods.md。")


if __name__ == "__main__":
    main()
