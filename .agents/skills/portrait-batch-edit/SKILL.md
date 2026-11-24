---
name: portrait-batch-edit
description: 在当前 Codex 对话查看本地人像预览，按场景拟定逐张 Lightroom Classic 显影和皮肤、眼睛、头发、背景精修方案，生成代表照预览和经确认后用于虚拟副本的批量计划。
---

# Lightroom Classic 人像批量修图

使用当前对话的图像查看能力（例如 `view_image`）进行视觉判断。Python 负责清单、联系表、校验和报告；Lua 插件负责 Lightroom 显影。视觉输入不可用时请用户附上预览图。本工作流无需 OpenAI API 或密钥。

## 找到输入与工具

项目内的 Skill 位于 `.agents/skills/portrait-batch-edit`，项目根目录含 `python/portrait_edit`。若通过用户级安装脚本调用，从本 Skill 目录的 `project-path.txt` 读取项目位置。将 `$pythonBin` 设为项目的 `.venv/Scripts/python.exe` 完整路径，`$job` 表示本次独立工作目录。

- Lightroom 导出目录中有 `lightroom-manifest.csv` 和 `previews`。运行 `& $pythonBin -m portrait_edit.cli scan-lightroom --manifest "$job\lightroom-manifest.csv" --workdir $job`。
- 本地成片目录使用 `& $pythonBin -m portrait_edit.cli scan --input <照片目录> --workdir $job`。对缺少预览的 RAW，用插件的 `Export Selected Previews` 导出。图像打不开时记录对应照片，请求可读预览。
- 运行 `& $pythonBin -m portrait_edit.cli sheets --manifest "$job\manifest.json" --out "$job\contact-sheets"`。按 `index.json` 中的格子编号定位完整路径，尤其注意不同子目录中的同名文件。

## 看图与写方案

打开本次索引列出的每张联系表，按主光方向、环境色及背景分组。查看每张需要显影判断的原尺寸预览。代表照、混合光、眼部或发丝细节难以看清时单独放大；仍无法判断的项目写入复核备注。需要场景与肤色判断准则时读取本 Skill 的 `references/editing-policy.md`。

在 `$job\ai-edit-plan.json` 写入 v1.0 方案。项目内 `examples/ai-edit-plan.example.json` 有完整样例，`python/portrait_edit/edit-plan.schema.json` 定义结构，`python/portrait_edit/develop-settings.json` 给出支持的滑块及范围。

- 每组给出 `id`、`style_name`、`rationale`，说明选择该风格的画面依据。逐张使用清单中的完整 `source_path` 和 `preview_path`，覆盖全部照片。每组标记一张 `preview: true`。
- `global_settings` 填 Lightroom 滑块的**最终绝对值**。从 `current_settings` 出发，例如当前曝光 +0.40 EV，想提亮 0.15 EV，应写 0.55。只写确实需要改动且原片支持的键。无须改动时可写 `{}`。渲染成片使用增量型白平衡滑块的最终读数，RAW 按清单记录的色温与色调读数判断。旧清单缺基线时，已有显影的照片宜重新导出。
- 逐张检查 `facial_skin`、`iris_pupil`、`hair`、`background`。在 `local_adjustments` 记录目标、可操作的 `instruction`、数值 `settings` 和 `status: proposed_not_applied`。已有良好质感或区域不可见时，写明保留或跳过的依据，设置留空。补充 `confidence` 和 `notes`，标明需要人工查看的位置。
- 跨光线组分别决定风格，同组根据每张曝光、肤色与背景微调。省略不确定的全局参数，保留个体肤色、皮肤纹理和场景氛围。

## 审阅与应用

运行 `& $pythonBin -m portrait_edit.cli validate --manifest "$job\manifest.json" --plan "$job\ai-edit-plan.json" --out "$job\output"`。使用 `normalized-plan.json` 和 `report.html` 核对代表照、限幅和局部建议。输出可点击的报告路径、照片数、分组数及主要复核点。

在 Lightroom 的 `Apply Plan to Virtual Copies` 菜单先选择 `preview-plan.csv`，经用户确认创建每组代表照。用户检查实际虚拟副本并明确认可本版效果后，再选择同目录的 `apply-plan.csv` 并确认。若修改了方案或手调了代表照，请把调整写回 JSON，重新生成并审阅。取消或中断后使用同一份 CSV 续做。

按实际进度说明「方案已生成」「代表照已创建」或「批量应用已完成」。已生成 CSV 时只能确认方案就绪。局部蒙版清单供使用者在虚拟副本上逐项操作。
