from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


def make_contact_sheets(manifest_path: str | Path, out_dir: str | Path,
                        batch_size: int = 20, columns: int = 4,
                        cell_width: int = 360, cell_height: int = 470) -> list[Path]:
    if batch_size < 1 or columns < 1:
        raise ValueError("batch-size and columns must be positive")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    photos = [p for p in manifest.get("photos", []) if p.get("preview_path") and Path(p["preview_path"]).exists()]
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    created: list[Path] = []
    inputs = {Path(p[key]).resolve() for p in manifest["photos"]
              for key in ("source_path", "preview_path") if p.get(key)}
    tiles = []

    for batch_no, start in enumerate(range(0, len(photos), batch_size), 1):
        batch = photos[start:start + batch_size]
        rows = (len(batch) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "white")
        draw = ImageDraw.Draw(sheet)

        for offset, item in enumerate(batch):
            idx = start + offset + 1
            x = (offset % columns) * cell_width
            y = (offset // columns) * cell_height
            img_path = Path(item["preview_path"])
            try:
                with Image.open(img_path) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((cell_width - 20, cell_height - 70), Image.Resampling.LANCZOS)
                    px = x + (cell_width - im.width) // 2
                    py = y + 8 + (cell_height - 70 - im.height) // 2
                    sheet.paste(im, (px, py))
                label = f"{idx:04d} | {item.get('file_name', img_path.name)}"
                draw.text((x + 8, y + cell_height - 52), label[:52], fill="black", font=font)
                draw.text((x + 8, y + cell_height - 32),
                          f"{item.get('width') or '?'}x{item.get('height') or '?'} | {item.get('captured_at') or ''}",
                          fill="#444444", font=font)
            except OSError as exc:
                raise ValueError(f"Cannot read preview: {img_path}") from exc
            tiles.append({"number": idx, "sheet": batch_no, "source_path": item["source_path"],
                          "preview_path": str(img_path)})

        path = output / f"contact-sheet-{batch_no:03d}.jpg"
        if path.resolve() in inputs:
            raise ValueError(f"Contact sheet would overwrite an input photo: {path}")
        sheet.save(path, quality=90, optimize=True)
        created.append(path)

    index_path = output / "index.json"
    index_path.write_text(json.dumps({
        "contact_sheets": [str(p) for p in created],
        "photo_count": len(photos),
        "tiles": tiles,
        "missing_previews": [p["source_path"] for p in manifest["photos"] if not p.get("preview_path") or not Path(p["preview_path"]).is_file()],
        "batch_size": batch_size,
        "columns": columns
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return created
