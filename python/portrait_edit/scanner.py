from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

RASTER_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
RAW_EXTS = {".arw", ".cr2", ".cr3", ".nef", ".nrw", ".raf", ".orf", ".rw2", ".dng", ".pef", ".srw"}


def _image_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "width": None, "height": None, "format": path.suffix.lower().lstrip("."),
        "captured_at": None
    }
    try:
        from PIL import Image, ExifTags
        with Image.open(path) as im:
            info["width"], info["height"] = im.size
            info["format"] = (im.format or path.suffix.lstrip(".")).lower()
            exif = im.getexif()
            if exif:
                tag_names = {v: k for k, v in ExifTags.TAGS.items()}
                dt = exif.get(tag_names.get("DateTimeOriginal", -1))
                if dt:
                    info["captured_at"] = str(dt)
    except Exception:
        pass
    return info


def scan_folder(input_dir: str | Path, workdir: str | Path) -> Path:
    root = Path(input_dir).expanduser().resolve()
    out_dir = Path(workdir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Input folder does not exist: {root}")
    out_dir.mkdir(parents=True, exist_ok=True)

    items = []
    nested_workdir = out_dir != root and out_dir.is_relative_to(root)
    for p in sorted(root.rglob("*")):
        if not p.is_file() or (nested_workdir and p.is_relative_to(out_dir)):
            continue
        ext = p.suffix.lower()
        if ext not in RASTER_EXTS and ext not in RAW_EXTS:
            continue
        info = _image_info(p) if ext in RASTER_EXTS else {
            "width": None, "height": None, "format": ext.lstrip("."), "captured_at": None
        }
        items.append({
            "id": str(len(items) + 1).zfill(5),
            "file_name": p.name,
            "source_path": str(p),
            "preview_path": str(p) if ext in RASTER_EXTS else None,
            "extension": ext,
            "file_format": ext[1:].upper(),
            "size_bytes": p.stat().st_size,
            **info,
            "preview_status": "ready" if ext in RASTER_EXTS else "needs_lightroom_preview"
        })

    manifest = {
        "schema_version": "1.0",
        "input_root": str(root),
        "photo_count": len(items),
        "photos": items
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def scan_lightroom_manifest(lr_manifest: str | Path, workdir: str | Path) -> Path:
    src = Path(lr_manifest).expanduser().resolve()
    out_dir = Path(workdir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(src)

    items = []
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"source_path", "preview_path"} <= set(reader.fieldnames or ()):
            raise ValueError(f"Invalid Lightroom manifest header: {src}")
        seen = set()
        for row in reader:
            source_path = row["source_path"]
            if not source_path or source_path.casefold() in seen:
                raise ValueError(f"Empty or duplicate Lightroom source: {source_path!r}")
            seen.add(source_path.casefold())
            preview = Path(row.get("preview_path", "")).expanduser()
            if not preview.is_absolute():
                preview = src.parent / preview
            exists = bool(row.get("preview_path")) and preview.is_file()
            items.append({
                "id": row.get("uuid") or row.get("local_identifier") or str(len(items) + 1).zfill(5),
                "local_identifier": row.get("local_identifier"),
                "uuid": row.get("uuid"),
                "catalog_id": row.get("catalog_id"),
                "develop_stamp": row.get("develop_stamp"),
                "file_format": row.get("file_format") or Path(source_path).suffix[1:].upper(),
                "file_name": row.get("file_name") or Path(row.get("source_path", "")).name,
                "source_path": row.get("source_path", ""),
                "preview_path": str(preview.resolve()) if exists else None,
                "extension": Path(row.get("source_path", "")).suffix.lower(),
                "width": _safe_int(row.get("width")),
                "height": _safe_int(row.get("height")),
                "captured_at": row.get("captured_at"),
                "preview_status": "ready" if exists else "missing_preview"
            })
            if "develop_stamp" in row:
                items[-1]["current_settings"] = {
                    key[5:]: float(value) for key, value in row.items()
                    if key.startswith("base_") and value
                }

    manifest = {
        "schema_version": "1.0",
        "source_manifest": str(src),
        "photo_count": len(items),
        "photos": items
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _safe_int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
