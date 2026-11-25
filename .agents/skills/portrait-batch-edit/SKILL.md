---
name: portrait-batch-edit
description: 从提示词自动导出 Lightroom Classic 当前选区或已导入文件夹的人像预览，在当前 Codex 对话逐张看图，生成显影、局部精修和代表照方案，供确认后用于虚拟副本。
---

# Lightroom Classic 人像批量修图

使用当前对话的图像查看能力（例如 `view_image`）进行视觉判断。Python 负责清单、联系表、校验和报告；Lua 插件负责 Lightroom 显影。视觉输入不可用时请用户附上预览图。本工作流无需 OpenAI API 或密钥。

## 找到输入与工具

项目内的 Skill 位于 `.agents/skills/portrait-batch-edit`，项目根目录含 `python/portrait_edit`。若通过用户级安装脚本调用，从本 Skill 目录的 `project-path.txt` 读取项目位置。将 `$projectRoot` 设为项目根目录，`$pythonBin` 设为项目的 `.venv/Scripts/python.exe` 完整路径，`$job` 表示本次独立工作目录。

- 用户给出已有的 Lightroom 导出目录或清单时，以 `lightroom-manifest.csv` 所在目录作为 `$job`。只有 `previews` 或 `lightroom-manifest.tmp` 的批次属于未完成导出，重试时使用新的工作目录。
- 用户要求处理 Lightroom 当前选区、已导入的原片目录，或给出一个新的批次工作目录时，在当前对话自动发起导出。先运行 `& "$projectRoot\scripts\install-lightroom-plugin.ps1"` 安装或更新插件。把 `$exportArgs` 初始化为 `@()`。使用选区时直接执行下方命令。指定 Lightroom 原片目录时追加 `$exportArgs += @('--source-folder', $sourceFolder)`，包含子目录中的已导入原片。用户指定输出位置时追加 `$exportArgs += @('--workdir', $job)`。旧示例中新的或空的 `D:\LrAI\session-001` 属于输出位置。省略输出位置会自动分配新目录。

  ```powershell
  [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
  $lrManifest = & $pythonBin -X utf8 -m portrait_edit.cli export-lightroom @exportArgs
  if ($LASTEXITCODE -ne 0) { throw 'Lightroom 预览导出未完成，请查看命令返回的原因。' }
  $job = Split-Path -LiteralPath $lrManifest
  ```

  等待命令返回本批次完整清单，再继续扫描和看图。若选区为空或原片目录未收录，按返回的原因请用户选片或打开对应的 Lightroom 目录。若插件首次安装或更新后未响应，提示在增效工具管理器启用或重新载入，或重启 Lightroom 一次。用户也可使用手动菜单 `Export Selected Previews` 导出到新目录。
- 对已取得的 Lightroom 清单运行 `& $pythonBin -m portrait_edit.cli scan-lightroom --manifest "$job\lightroom-manifest.csv" --workdir $job`。
- 本地成片目录使用 `& $pythonBin -m portrait_edit.cli scan --input <照片目录> --workdir $job`。若 RAW 需要 Lightroom 渲染预览，按其已导入的原片目录请求导出。图像打不开时记录对应照片，请求可读预览。
- 运行 `& $pythonBin -m portrait_edit.cli sheets --manifest "$job\manifest.json" --out "$job\contact-sheets"`。按 `index.json` 中的格子编号定位完整路径，尤其注意不同子目录中的同名文件。

## 看图与写方案

打开索引中的每张联系表，按主光方向、光质、环境色和背景分组。读[修图手册的场景与部位索引](references/editing-policy.md)，依画面进入 Varis 或 Kelby 的对应案例。再打开每张照片的预览，比较受光侧与背光侧、脸与颈、人物与背景，决定哪一处最影响这张人像，或哪些特征值得保留。插件向 Lightroom 请求 2048 × 2048 的 JPEG 预览。若放大后仍看不清毛孔、微血丝或单根发丝，在备注中指出需要用原片 1:1 核对的位置。

在 `$job\ai-edit-plan.json` 写入 v1.0 方案。项目内 `examples/ai-edit-plan.example.json` 有完整样例，`python/portrait_edit/edit-plan.schema.json` 定义结构，`python/portrait_edit/develop-settings.json` 给出支持的滑块及范围。

- 每组给出 `id`、`style_name`、`rationale`，说明选择该风格的画面依据。逐张使用清单中的完整 `source_path` 和 `preview_path`，覆盖全部照片。每组标记一张 `preview: true`。
- `global_settings` 填 Lightroom 滑块的**最终绝对值**。从 `current_settings` 出发，例如当前曝光 +0.40 EV，想提亮 0.15 EV，应写 0.55。只写确实需要改动且原片支持的键。无须改动时可写 `{}`。渲染成片使用增量型白平衡滑块的最终读数，RAW 按清单记录的色温与色调读数判断。旧清单缺基线时，已有显影的照片宜重新导出。
- `notes` 第一行写该片首要问题或保留理由。后续行记录人工复核的位置和原因，包括需要 Photoshop 仿制、修补或重建纹理的细节。用 `confidence` 反映可见证据。
- 逐张检查 `facial_skin`、`iris_pupil`、`hair`、`background`，需要时用 `subject` 定位眼窝或其他主体部位。把 `local_adjustments` 按对成片的影响排列。新建议用 `location` 定位人物及画面方位，`observation` 写可见迹象和参照，`instruction` 写操作顺序与需要避开的边界，`stop_when` 写回看原图时可判断的停手条件。状态为 `proposed_not_applied`。已有良好质感或区域不可见时，说明保留或跳过的理由，`settings` 用 `{}`。有可判断的数值时才填写相应的局部滑块。
- 跨光线组分别决定风格，同组根据每张曝光、肤色与背景微调。省略不确定的全局参数，保留个体肤色、皮肤纹理和场景氛围。

## 审阅与应用

运行 `& $pythonBin -m portrait_edit.cli validate --manifest "$job\manifest.json" --plan "$job\ai-edit-plan.json" --out "$job\output"`。使用 `normalized-plan.json` 和 `report.html` 核对代表照、限幅和局部建议。输出可点击的报告路径、照片数、分组数及主要复核点。

在 Lightroom 的 `Apply Plan to Virtual Copies` 菜单先选择 `preview-plan.csv`，经用户确认创建每组代表照。用户检查实际虚拟副本并明确认可本版效果后，再选择同目录的 `apply-plan.csv` 并确认。若修改了方案或手调了代表照，请把调整写回 JSON，重新生成并审阅。取消或中断后使用同一份 CSV 续做。

按实际进度说明「方案已生成」「代表照已创建」或「批量应用已完成」。已生成 CSV 时只能确认方案就绪。局部蒙版清单供使用者在虚拟副本上逐项操作。
