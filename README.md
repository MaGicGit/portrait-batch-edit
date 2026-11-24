# AI Portrait Retoucher · Lightroom Classic 人像批量修图助手

将一组人像从 Lightroom Classic 导出为预览，在当前 Codex 对话中按光线和场景分组，逐张生成曝光、白平衡和 HSL 调整方案。每组先在 Lightroom 里生成一张代表照虚拟副本。你检查实际画面并确认后，插件才把同一版方案应用到其余照片的虚拟副本。

v0.2 支持全局显影、中文审阅报告和中断续做。皮肤、眼睛、头发和背景的局部调整会列出选区、滑块和建议值，供你在 Lightroom 蒙版面板中操作。

## 运行环境

- Windows 与 PowerShell，Python 3.10 或更高版本。
- Lightroom Classic 桌面版。插件声明的最低 SDK 版本为 11。
- 能查看本地图片的 Codex 对话。视觉分析使用当前对话，项目无需单独配置模型 API 密钥。

## 开始使用

1. 获取项目，并在仓库根目录安装 Python 工具。如果已下载或克隆仓库，可直接从创建虚拟环境开始。

   ```powershell
   git clone https://github.com/MaGicGit/portrait-batch-edit.git
   cd portrait-batch-edit
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e .\python
   ```

2. 在 Lightroom Classic 的「文件 → 增效工具管理器 → 添加」选择插件目录。在图库中选中原片，运行 `Portrait Batch Edit - Export Selected Previews`，为这批照片选择一个新目录，例如 `D:\LrAI\session-001`。Windows 上建议用英文导出目录，原片可以使用中文名称。[Lightroom 插件目录](lightroom-plugin/PortraitBatchEdit.lrplugin/)
3. 在项目内打开 Codex，把下面的目录替换成刚导出的目录。项目已包含同名 Skill。需要在其他项目调用时可运行 `.\scripts\install-skill.ps1`。

   ```text
   $portrait-batch-edit 处理 D:\LrAI\session-001。按场景分组，让每组有自己的风格。
   逐张检查肤色、眼睛、头发和背景，生成方案、代表照预览清单和中文审阅报告。
   ```

4. 打开 `output\report.html` 审阅分组与参数。在 Lightroom 运行 `Portrait Batch Edit - Apply Plan to Virtual Copies`，选择 `output\preview-plan.csv` 并确认。每组会生成一张名为 `AI Retouch …` 的代表照虚拟副本。在「修改照片」中与原片对照，特别检查肤色、高光和背景。
5. 满意后运行同一个菜单，选择同一目录的 `apply-plan.csv`，点击「确认并批量应用」。代表照计入最终数量，只为其余照片续做副本。要修改风格时，让 Codex 更新 JSON 再次运行校验，新版方案需要重新预览。

## 产物

| 文件 | 用途 |
| --- | --- |
| `lightroom-manifest.csv`、`previews\` | Lightroom 导出的照片身份、当前显影状态和输入预览 |
| `manifest.json`、`contact-sheets\index.json` | 每张照片与联系表格子的对应关系 |
| `ai-edit-plan.json` | Codex 根据实际画面拟定的分组、逐张调整与局部建议 |
| `output\normalized-plan.json` | 已校验的目标值、代表照及限幅记录 |
| `output\preview-plan.csv`、`output\apply-plan.csv` | 同一版本的两个 Lightroom 入口，需要放在同一目录 |
| `output\report.html`、`output\local-adjustment-review.csv` | 中文审阅报告与逐张局部蒙版操作清单 |

报告缩略图来自输入预览，最终效果请在 Lightroom 的代表照虚拟副本中检查。局部蒙版的选区名称、多人画面及检测失败时的处理见 [局部精修](docs/local-masks.md)。

## 单独运行 Python

```powershell
$job = 'D:\LrAI\session-001'
$pythonBin = '.\.venv\Scripts\python.exe'
& $pythonBin -m portrait_edit.cli scan-lightroom --manifest "$job\lightroom-manifest.csv" --workdir $job
& $pythonBin -m portrait_edit.cli sheets --manifest "$job\manifest.json" --out "$job\contact-sheets"
# 在当前 Codex 对话看图并生成 ai-edit-plan.json 后运行
& $pythonBin -m portrait_edit.cli validate --manifest "$job\manifest.json" --plan "$job\ai-edit-plan.json" --out "$job\output"
```

只有 JPEG、PNG 或 TIFF 等本地成片时，可从 `scan --input <照片目录> --workdir <独立工作目录>` 开始。RAW 需要 Lightroom 渲染的预览。手工编写或调整方案时可参考 [v1.0 方案样例](examples/ai-edit-plan.example.json) 和 [滑块可用范围](python/portrait_edit/develop-settings.json)。

## 常见情况

| 遇到的情况 | 处理方式 |
| --- | --- |
| 打开批量 CSV 后提示先生成代表照 | 在同一目录选择 `preview-plan.csv`，确认创建并查看各组代表照，再打开 `apply-plan.csv`。 |
| 预览后修改过原片或代表照 | 原片显影已变更时，重新导出预览。若要沿用手调代表照的风格，将调整写回 JSON，运行 `validate` 并重新预览。 |
| 批量应用中断 | 修复提示的问题后，重新打开同一份 CSV。插件通过原片和已完成副本的身份记录续做。 |
| 从 starter 版本升级 | 可重用 v1.0 方案和旧 manifest，运行 `validate` 重新生成一对 CSV。若旧清单缺少显影指纹且原片已有修图，建议重新导出。 |

## 验证

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\python[test]"
.\run-tests.ps1
```

测试包含 Python 扫描、联系表、方案校验及中文报告，并在 Lua 5.1 SDK 模拟环境运行实际插件入口。Lightroom 主机上仍需验收插件加载、真实虚拟副本画面和目录持久化。步骤和后续阶段见 [开发与验收计划](docs/phase-plan.md)；模块之间的数据流见 [架构](docs/architecture.md)。
