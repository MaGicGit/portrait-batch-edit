# Codex usage

Open the relevant catalog in Lightroom Classic and the repository root in Codex. For a selection, use this prompt.

> $portrait-batch-edit 处理 Lightroom 当前选中的原片。按光线分组，逐张查看肤色、眼睛、头发和背景，生成方案、代表照预览清单和中文报告。

For an imported folder, replace the selection with its full path, for example “处理 Lightroom 已导入的原片目录 D:\照片\秋日人像，包含子目录”. The skill requests the previews, allocates a numbered job directory and waits for the manifest before scanning. To choose the destination, add “工作目录用 D:\LrAI\session-001”. To resume an existing export, give Codex the directory containing its `lightroom-manifest.csv`.

After review:

> Validate the plan and generate preview-plan.csv, apply-plan.csv, local-adjustment-review.csv and report.html.

After the preview virtual copies are reviewed:

> I approve this style. Generate/verify the final apply plan; I will apply it through Lightroom's plugin.

## Image viewing

Codex should use its built-in `view_image` tool on local contact sheets and individual previews. This is a Codex-session tool, not a Python function. The skill must not claim that a Python script called GPT.
