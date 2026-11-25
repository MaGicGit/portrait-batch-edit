from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .report import write_report

RESOURCES = Path(__file__).parent
BOUNDS = json.loads((RESOURCES / "develop-settings.json").read_text("utf-8"))["settings"]
SCHEMA = Draft202012Validator(json.loads((RESOURCES / "edit-plan.schema.json").read_text("utf-8")))
CSV_FIELDS = ["revision", "source_path", "uuid", "catalog_id", "develop_stamp",
              "style_group", "representative", *BOUNDS]
REVIEW_DETAILS = ("location", "observation", "stop_when")


def load_json(path: str | Path) -> dict[str, Any]:
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError(f"Invalid JSON number: {value}")

    data = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=no_duplicates, parse_constant=invalid_number)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def _norm_path(value: str) -> str:
    return os.path.normpath(value.replace("/", "\\")).casefold()


def _normalize(manifest, plan):
    error = next(SCHEMA.iter_errors(plan), None)
    if error:
        raise ValueError(f"{error.json_path}: {error.message}")
    groups = [g["id"] for g in plan["style_groups"]]
    if len(groups) != len(set(groups)):
        raise ValueError("Duplicate style group ID")
    known = {}
    for photo in manifest["photos"]:
        key = _norm_path(photo["source_path"])
        if key in known:
            raise ValueError(f"Ambiguous source in manifest: {photo['source_path']}")
        known[key] = photo

    normalized, warnings = [], []
    for item in plan["photos"]:
        path = item["source_path"]
        source = known.pop(_norm_path(path), None)
        if not source:
            raise ValueError(f"Unknown or repeated photo: {path}")
        if not source.get("preview_path") or not Path(source["preview_path"]).is_file():
            raise ValueError(f"Missing preview for {path}. Export a Lightroom preview first.")
        if item["style_group"] not in groups:
            raise ValueError(f"Unknown group for {path}: {item['style_group']}")
        safe = {}
        for name, value in item["global_settings"].items():
            if name not in BOUNDS:
                raise ValueError(f"{path}: unsupported Develop setting {name}")
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"{path}: {name} must be a finite number")
            if name in {"Temperature", "Tint"} and source.get("file_format", "").upper() in {
                "JPG", "JPEG", "TIFF", "PNG", "PSD"
            }:
                raise ValueError(f"{path}: use IncrementalTemperature / IncrementalTint for rendered files")
            baseline = source.get("current_settings")
            if baseline is not None and name not in baseline:
                raise ValueError(f"{path}: {name} is unavailable for this photo")
            limits = BOUNDS[name]
            safe[name] = max(limits["min"], min(limits["max"], value))
            if safe[name] != value:
                warnings.append(f"{path} · {name}: {value} → {safe[name]}")
        normalized.append({**item, "source_path": source["source_path"],
                           "preview_path": source["preview_path"], "global_settings": safe,
                           **{k: source.get(k) or "" for k in ("uuid", "catalog_id", "develop_stamp")}})
    if known:
        raise ValueError("Plan is missing photos: " + ", ".join(p["source_path"] for p in known.values()))

    reps = {}
    for item in normalized:
        group = item["style_group"]
        rank = (item.get("preview", False), item.get("score", 0))
        if group not in reps or rank > reps[group][0]:
            reps[group] = rank, item
    if set(reps) != set(groups):
        raise ValueError("Every declared group needs at least one photo")
    for item in normalized:
        item["preview"] = item is reps[item["style_group"]][1]
    return {**plan, "photos": normalized, "warnings": warnings}


def validate_and_export(manifest_path: str | Path, plan_path: str | Path,
                        out_dir: str | Path) -> dict[str, Path]:
    plan = _normalize(load_json(manifest_path), load_json(plan_path))
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    revision = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    names = {"normalized_plan": "normalized-plan.json", "local_adjustments": "local-adjustment-review.csv",
             "report": "report.html", "preview_csv": "preview-plan.csv", "apply_csv": "apply-plan.csv"}
    with tempfile.TemporaryDirectory(dir=out) as staging:
        stage = Path(staging)
        (stage / names["normalized_plan"]).write_text(payload, encoding="utf-8")
        write_report(stage / names["normalized_plan"], stage / names["report"])
        with (stage / names["local_adjustments"]).open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["source_path", "style_group", "target", "status", "instruction", "settings_json",
                             *REVIEW_DETAILS])
            for item in plan["photos"]:
                for local in item.get("local_adjustments", []):
                    writer.writerow([item["source_path"], item["style_group"], local["target"], local["status"],
                                     local["instruction"], json.dumps(local.get("settings", {}), ensure_ascii=False),
                                     *(local.get(key, "") for key in REVIEW_DETAILS)])
        for kind in ("preview_csv", "apply_csv"):
            with (stage / names[kind]).open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for item in plan["photos"]:
                    if kind == "preview_csv" and not item["preview"]:
                        continue
                    row = {key: item[key] for key in ("source_path", "uuid", "catalog_id", "develop_stamp", "style_group")}
                    writer.writerow({**row, "revision": revision, "representative": int(item["preview"]),
                                     **item["global_settings"]})
        for name in names.values():
            os.replace(stage / name, out / name)
    return {key: out / name for key, name in names.items()}
