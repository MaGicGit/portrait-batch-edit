from __future__ import annotations

import argparse

from .scanner import scan_folder, scan_lightroom_manifest
from .contact_sheets import make_contact_sheets
from .plan import validate_and_export
from .report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="portrait-edit", description="Codex + Lightroom Classic portrait editing utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan a folder of rendered images and RAW filenames")
    p_scan.add_argument("--input", required=True)
    p_scan.add_argument("--workdir", required=True)

    p_lr = sub.add_parser("scan-lightroom", help="Convert Lightroom plugin export manifest to project manifest")
    p_lr.add_argument("--manifest", required=True)
    p_lr.add_argument("--workdir", required=True)

    p_sheets = sub.add_parser("sheets", help="Create contact sheets from a manifest")
    p_sheets.add_argument("--manifest", required=True)
    p_sheets.add_argument("--out", required=True)
    p_sheets.add_argument("--batch-size", type=int, default=20)
    p_sheets.add_argument("--columns", type=int, default=4)

    p_validate = sub.add_parser("validate", help="Validate AI edit plan and export Lightroom CSVs")
    p_validate.add_argument("--manifest", required=True)
    p_validate.add_argument("--plan", required=True)
    p_validate.add_argument("--out", required=True)

    p_report = sub.add_parser("report", help="Generate HTML report from an AI edit plan")
    p_report.add_argument("--plan", required=True)
    p_report.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.command == "scan":
        print(scan_folder(args.input, args.workdir))
    elif args.command == "scan-lightroom":
        print(scan_lightroom_manifest(args.manifest, args.workdir))
    elif args.command == "sheets":
        for path in make_contact_sheets(args.manifest, args.out, args.batch_size, args.columns):
            print(path)
    elif args.command == "validate":
        outputs = validate_and_export(args.manifest, args.plan, args.out)
        for name, path in outputs.items():
            print(f"{name}: {path}")
    elif args.command == "report":
        print(write_report(args.plan, args.out))


if __name__ == "__main__":
    main()
