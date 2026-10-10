"""Escaped source excerpts and alternative support-set review; no generated labels."""

import argparse
import html
import json
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file


def build(packet_path, output):
    packet = read_json(packet_path)
    cards = []
    for q in packet["questions"]:
        chunks = "".join(
            f"<details><summary>Candidate {i + 1} · {html.escape(e['source_title'])}</summary>"
            f"<p>{html.escape(e['source_url'])}</p><p>Page {e['page_index'] + 1} · "
            f"{html.escape(e['field'])} · characters {e['char_start']}–{e['char_end']}</p>"
            f"<pre>{html.escape(e['content'])}</pre></details>"
            for i, e in enumerate(q["candidates"])
        )
        pages = "".join(
            f"<details><summary>Full source page {i + 1}: {html.escape(p['page_name'])}</summary>"
            f"<p>{html.escape(p['page_url'])}</p><pre>{html.escape(p['page_result'])}</pre>"
            f"<pre>{html.escape(p['page_snippet'])}</pre></details>"
            for i, p in enumerate(q["pages"])
        )
        cards.append(f'''<article data-id="{html.escape(q["interaction_id"])}">
<h2>{html.escape(q["query"])}</h2><p>{html.escape(q["query_time"])}</p>
{chunks}<details><summary>Inspect full source pages</summary>{pages}</details>
<label>What facts must the evidence establish to answer the entire question?
<textarea class="requirements" rows="3"></textarea></label>
<label>Answerability<select class="answerability"><option value="pending">Pending</option>
<option value="supported_by_candidates">Candidate evidence supports the full answer</option>
<option value="missing_evidence">Candidate evidence is insufficient</option>
<option value="uncertain">Uncertain / ambiguous question or source</option></select></label>
<label>Acceptable complete support sets — candidate numbers, e.g. 1,3; 2,5
<input class="sets" placeholder="Each semicolon separates an alternative complete set"></label>
<label>Notes / missing facts / temporal or conflicting claims
<textarea class="notes" rows="3"></textarea></label>
<label>Decision<select class="status"><option value="pending">Pending</option>
<option value="reviewed">Reviewed and resolved</option>
<option value="needs_changes">Needs changes / unresolved</option></select></label>
<label><input class="attested" type="checkbox">
I inspected the relevant evidence. Each listed set satisfies all written requirements.
A missing-evidence decision applies to this candidate pool.</label></article>''')
    meta = {
        q["interaction_id"]: [e["evidence_id"] for e in q["candidates"]]
        for q in packet["questions"]
    }
    template = (Path(__file__).parent / "templates/evidence_review.html").read_text()
    page = template.replace("__CARDS__", "".join(cards)).replace("__COUNT__", str(len(cards)))
    page = page.replace("__META__", json.dumps(meta).replace("<", "\\u003c"))
    page = page.replace("__PACKET_SHA__", sha256_file(packet_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(page)
    return {"questions": len(cards), "initial_decisions": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.packet, args.output))
