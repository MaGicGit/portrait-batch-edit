from __future__ import annotations

import html
import json
from pathlib import Path


def _escape(value):
    return html.escape(str(value))


def write_report(plan_path: str | Path, output_path: str | Path) -> Path:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    groups = {g["id"]: g for g in plan["style_groups"]}
    targets = {"facial_skin": "面部皮肤", "iris_pupil": "虹膜和瞳孔",
               "hair": "头发", "background": "背景", "subject": "主体"}
    sections = []
    for group_id, group in groups.items():
        cards = []
        for item in plan["photos"]:
            if item["style_group"] != group_id:
                continue
            source = item["source_path"]
            preview = item.get("preview_path")
            thumb = ""
            if preview and Path(preview).is_file():
                url = _escape(Path(preview).resolve().as_uri())
                thumb = f'<a href="{url}"><img src="{url}" loading="lazy" alt="输入预览"></a>'
            settings = " · ".join(f"{_escape(k)} {_escape(v)}" for k, v in item["global_settings"].items())
            proposals = []
            for local in item.get("local_adjustments", []):
                sliders = ", ".join(f"{_escape(k)} {_escape(v)}" for k, v in local.get("settings", {}).items())
                values = f"（{sliders}）" if sliders else ""
                proposals.append(f'<li><b>{_escape(targets.get(local["target"], local["target"]))}</b> '
                                 f'{_escape(local["instruction"])} {values}</li>')
            mark = " · 代表照" if item.get("preview") else ""
            cards.append(f'<article>{thumb}<div><h3>{_escape(Path(source).name)}{mark}</h3>'
                         f'<small>{_escape(source)}</small><p>评分 {_escape(item.get("score", "—"))} · '
                         f'置信度 {_escape(item.get("confidence", "—"))}</p>'
                         f'<p>{_escape(item.get("notes", ""))}</p><h4>全局显影目标值</h4>'
                         f'<p>{settings or "沿用当前全局设置"}</p><h4>局部精修建议</h4>'
                         f'<ul>{"".join(proposals) or "<li>无局部调整建议</li>"}</ul></div></article>')
        sections.append(f'<section><h2>{_escape(group["style_name"])} · {len(cards)} 张</h2>'
                        f'<p>{_escape(group["rationale"])}</p>{"".join(cards)}</section>')
    warnings = "".join(f"<li>{_escape(w)}</li>" for w in plan.get("warnings", []))
    document = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>人像修图审阅</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;background:#faf9f6;color:#272b29;max-width:1050px;margin:auto;padding:24px}}
article{{display:flex;align-items:flex-start;gap:20px;background:white;border-top:1px solid #c7cfca;padding:18px;overflow-wrap:anywhere}}
img{{width:145px;max-height:210px;object-fit:contain}} h3,h4,p,ul{{margin:0 0 8px}} h4{{margin-top:12px}}
small{{color:#575e58}} @media(max-width:600px){{article{{display:block}}}}
</style></head><body><h1>人像修图审阅</h1><p>{_escape(plan.get("global_style_summary", ""))}</p>
<p>{len(plan["photos"])} 张照片 · {len(groups)} 个风格组。缩略图显示输入画面，请在 Lightroom 虚拟副本中检查显影效果。局部建议供蒙版面板逐项使用。</p>
{("<h2>已限制到允许范围的参数</h2><ul>" + warnings + "</ul>") if warnings else ""}
{"".join(sections)}</body></html>"""
    out = Path(output_path)
    if out.suffix.lower() not in {".htm", ".html"}:
        raise ValueError("Report output must be an HTML file")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    return out
