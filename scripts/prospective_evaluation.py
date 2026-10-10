"""Freeze/verify a prospective review packet, or preserve a supplied human export."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.prospective import freeze, validate_decisions, validate_packet

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "verify", "import"))
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.mode == "freeze":
        result = freeze(root, args.output)
    else:
        if args.packet is None:
            parser.error("--packet is required")
        packet = read_json(args.packet)
        validate_packet(packet, root)
        digest = sha256_file(args.packet)
        frozen = read_json(root / "results/evaluation/prospective_v1/manifest.json")
        if digest != frozen["packet_sha256"]:
            raise ValueError("packet differs from admitted prospective freeze")
        if args.mode == "verify":
            result = {
                "status": "prospective_packet_verified",
                "questions": len(packet["questions"]),
                "packet_sha256": digest,
            }
        else:
            if args.export is None:
                parser.error("--export is required")
            raw = args.export.read_bytes()
            result = validate_decisions(read_json(args.export), packet, digest)
            args.output.mkdir(parents=True, exist_ok=False)
            preserved = args.output / "original-export.json"
            preserved.write_bytes(raw)
            result["export_sha256"] = sha256_file(preserved)
            # Bind parsed decisions to the preserved bytes even if the source changed mid-import.
            result = validate_decisions(read_json(preserved), packet, digest) | {
                "export_sha256": result["export_sha256"]
            }
        result["packet_sha256"] = digest
        write_json(args.output / "validation.json", result)
    print(result)
