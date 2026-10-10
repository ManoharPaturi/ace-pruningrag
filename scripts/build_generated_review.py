"""Readable local review packet for genuine generated answers; decisions start pending."""

import argparse
import hashlib
import html
import json
from pathlib import Path


def build(run: Path, output: Path):
    rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
    grouped = {}
    for row in rows:
        grouped.setdefault(row["interaction_id"], []).append(row)
    cards = []
    for index, (identity, variants) in enumerate(grouped.items()):
        question = variants[0]["query"]
        blocks = []
        for variant in sorted(variants, key=lambda r: r["policy"]):
            evidence = "".join(
                "<details><summary>Source excerpt "
                + str(i + 1)
                + "</summary><p>"
                + html.escape(e.get("source_url", e.get("source_ref", "")))
                + "</p><pre>"
                + html.escape(e["content"])
                + "</pre></details>"
                for i, e in enumerate(variant["selected"])
            )
            blocks.append(f'''<section class="variant" data-policy="{variant["policy"]}">
<h3>{html.escape(variant["policy"].replace("_", " "))}</h3>
<div class="answer">{html.escape(variant["prediction"])}</div>
<p class="muted">Input {variant["input_tokens"]} tokens ·
Output {variant["output_tokens"]} tokens ·
{variant["generation_seconds"]:.2f}s ·
Generation round {variant.get("regeneration_round", 1)} ·
Source policy: {html.escape(variant.get("retry_policy", variant["policy"]).replace("_", " "))} ·
Automatic status: {html.escape(variant["evaluation"]["outcome"].replace("_", " "))}</p>{evidence}
<label>Your correctness decision<select class="decision">
<option value="pending">Pending</option>
<option value="correct">Correct</option>
<option value="incorrect">Incorrect</option>
<option value="abstained">Abstained</option>
<option value="uncertain">Uncertain / ambiguous reference</option></select></label>
<label>Evidence support<select class="support">
<option value="pending">Pending</option>
<option value="supported">Supported</option>
<option value="unsupported">Contains unsupported claim</option>
<option value="uncertain">Uncertain</option>
<option value="not_applicable">Not applicable: abstention</option></select></label>
<label>Notes<textarea class="notes" rows="3"></textarea></label>
<label><input class="attest" type="checkbox">
I inspected this answer and its evidence.</label></section>''')
        cards.append(
            f'<article data-id="{identity}"><div class="muted">'
            f"Question {index + 1} of {len(grouped)} · "
            f"{html.escape(variants[0]['query_time'])}</div><h2>{html.escape(question)}</h2>"
            + "".join(blocks)
            + "</article>"
        )
    payload = json.dumps(rows, ensure_ascii=True).replace("<", "\\u003c")
    page = (Path(__file__).parent / "templates/generated_review.html").read_text()
    page = page.replace("__CARDS__", "".join(cards)).replace("__DATA__", payload)
    page = page.replace("50 questions", f"{len(grouped)} questions")
    page = page.replace(
        "__RUN_HASH__", hashlib.sha256((run / "predictions.jsonl").read_bytes()).hexdigest()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(page)
    return {
        "questions": len(grouped),
        "generated_answers": len(rows),
        "initial_decisions": "pending",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.output), indent=2))
