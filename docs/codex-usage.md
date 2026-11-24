# Codex usage

Open the repository root in Codex. Invoke:

`$portrait-batch-edit`

Example request:

> Process `D:\LrAI\session-001`. Inspect the contact sheets, infer a distinct style for each lighting group, inspect full previews of representative photos, and write `ai-edit-plan.json`. Do not apply anything to Lightroom yet.

After review:

> Validate the plan and generate preview-plan.csv, apply-plan.csv, local-adjustment-review.csv and report.html.

After the preview virtual copies are reviewed:

> I approve this style. Generate/verify the final apply plan; I will apply it through Lightroom's plugin.

## Image viewing

Codex should use its built-in `view_image` tool on local contact sheets and individual previews. This is a Codex-session tool, not a Python function. The skill must not claim that a Python script called GPT.
