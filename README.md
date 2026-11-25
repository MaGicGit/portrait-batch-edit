# AI Portrait Retoucher · Lightroom Classic 人像批量修图助手

将一组人像从 Lightroom Classic 导出为预览，在当前 Codex 对话中按光线和场景分组，逐张生成曝光、白平衡和 HSL 调整方案。每组先在 Lightroom 里生成一张代表照虚拟副本。你检查实际画面并确认后，插件才把同一版方案应用到其余照片的虚拟副本。

中文审阅报告先写每张人像最值得处理或保留的细节，再按优先级列出位置、依据、操作和停手条件。例如，同样是额头发亮，孤立油斑可以局部收亮，沿颧骨自然渐退的高光应当保留。判断方法、案例与两本原书的页码见[人像修图手册](.agents/skills/portrait-batch-edit/references/editing-policy.md)。

## 运行环境

- Windows 与 PowerShell，Python 3.10 或更高版本。
- Lightroom Classic 桌面版。插件声明的最低 SDK 版本为 11。
- 能查看本地图片的 Codex 对话。视觉分析使用当前对话，项目无需单独配置模型 API 密钥。

## 开始使用

1. 首次使用时，在仓库根目录安装 Python 工具和 Lightroom 插件。如果已下载或克隆仓库，可直接从创建虚拟环境开始。

   ```powershell
   git clone https://github.com/MaGicGit/portrait-batch-edit.git
   cd portrait-batch-edit
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e .\python
   .\scripts\install-lightroom-plugin.ps1
   ```

2. 在 Lightroom Classic 打开这批照片所在的目录。要处理其中几张，就在图库中选中原片。要处理整个已导入的文件夹，直接在提示词里写它的路径即可。安装脚本把插件复制到 Lightroom 的 Modules 目录。如果安装或更新时 Lightroom 已打开，可以在增效工具管理器中重新载入插件，或重启一次。
3. 在项目内打开 Codex，输入下面的提示词。Codex 会让 Lightroom 导出预览，等清单写完后继续看图。项目已包含同名 Skill，需要在其他项目调用时可运行 `.\scripts\install-skill.ps1`。

   ```text
   $portrait-batch-edit 处理 Lightroom 当前选中的原片。按场景分组，让每组有自己的风格。
   逐张检查肤色、眼睛、头发和背景，生成方案、代表照预览清单和中文审阅报告。
   ```

   按文件夹处理时，可把第一句换成「处理 Lightroom 已导入的原片目录 `D:\照片\秋日人像`，包含子目录」。默认工作目录为 `%USERPROFILE%\PortraitBatchEdit\jobs\session-001`，每批自动取下一个可用编号。也可以在提示词中写「工作目录用 `D:\LrAI\session-001`」。给出已有的 Lightroom 导出清单时会直接从该批次继续。

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

若要从 Lightroom 当前选区新建一批，可运行 `.\.venv\Scripts\python.exe -m portrait_edit.cli export-lightroom`。命令成功时输出完整清单路径。可选参数 `--source-folder` 指定 Lightroom 已导入的原片目录，`--workdir` 指定新的或空的工作目录。已有预览也可以从扫描命令开始。

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
| 自动导出提示未收到请求 | 在 Lightroom Classic「文件 → 增效工具管理器」确认 Portrait Batch Edit 已启用，首次安装或更新后重新载入插件或重启 Lightroom。也可用插件菜单 `Export Selected Previews` 导出到新目录，再把目录交给 Codex。 |
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
