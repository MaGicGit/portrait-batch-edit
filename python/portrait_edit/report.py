from __future__ import annotations

import html
import json
from pathlib import Path


def _escape(value):
    return html.escape(str(value))


def _photo_notes(notes: str) -> str:
    lines = notes.strip().splitlines()
    if not lines:
        return ""
    result = f'<h4>首要判断</h4><p>{_escape(lines[0])}</p>'
    if len(lines) > 1:
        rest = "\n".join(lines[1:])
        result += f'<h4>备注与人工复核</h4><p class="multiline">{_escape(rest)}</p>'
    return result


def _local_proposal(local: dict, target_name: str) -> str:
    sliders = " · ".join(f"{k} {v}" for k, v in local.get("settings", {}).items())
    fields = (("位置", local.get("location")), ("观察依据", local.get("observation")),
              ("操作", local["instruction"]), ("建议滑块", sliders), ("停手条件", local.get("stop_when")))
    details = "".join(f'<dt>{label}</dt><dd class="multiline">{_escape(value)}</dd>'
                      for label, value in fields if value and value.strip())
    return f'<li><b>{_escape(target_name)}</b><dl>{details}</dl></li>'


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
                proposals.append(_local_proposal(local, targets.get(local["target"], local["target"])))
            mark = " · 代表照" if item.get("preview") else ""
            review = f'<ol>{"".join(proposals)}</ol>' if proposals else '<p>无局部调整建议</p>'
            cards.append(f'<article>{thumb}<div><h3>{_escape(Path(source).name)}{mark}</h3>'
                         f'<small>{_escape(source)}</small><p>评分 {_escape(item.get("score", "—"))} · '
                         f'置信度 {_escape(item.get("confidence", "—"))}</p>'
                         f'{_photo_notes(item.get("notes", ""))}<h4>全局显影目标值</h4>'
                         f'<p>{settings or "沿用当前全局设置"}</p><h4>局部精修建议</h4>'
                         f'{review}</div></article>')
        sections.append(f'<section><h2>{_escape(group["style_name"])} · {len(cards)} 张</h2>'
                        f'<p>{_escape(group["rationale"])}</p>{"".join(cards)}</section>')
    warnings = "".join(f"<li>{_escape(w)}</li>" for w in plan.get("warnings", []))
    document = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>人像修图审阅</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;background:#faf9f6;color:#272b29;max-width:1050px;margin:auto;padding:24px}}
article{{display:flex;align-items:flex-start;gap:20px;background:white;border-top:1px solid #c7cfca;padding:18px;overflow-wrap:anywhere}}
img{{width:145px;max-height:210px;object-fit:contain}} h3,h4,p,ul{{margin:0 0 8px}} h4{{margin-top:12px}}
ol{{margin:0;padding-left:1.5em}} dl{{margin:4px 0 10px}} dt{{display:inline;font-weight:600}}
dd{{display:inline;margin-left:0.6em}} dd::after{{content:"";display:block}} .multiline{{white-space:pre-line}}
small{{color:#575e58}} @media(max-width:600px){{article{{display:block}}}}
</style></head><body><h1>人像修图审阅</h1><p>{_escape(plan.get("global_style_summary", ""))}</p>
<p>{len(plan["photos"])} 张照片 · {len(groups)} 个风格组。缩略图显示输入画面，请在 Lightroom 虚拟副本中检查显影效果。局部建议待人工逐项复核。</p>
{("<h2>已限制到允许范围的参数</h2><ul>" + warnings + "</ul>") if warnings else ""}
{"".join(sections)}</body></html>"""
    out = Path(output_path)
    if out.suffix.lower() not in {".htm", ".html"}:
        raise ValueError("Report output must be an HTML file")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    return out
