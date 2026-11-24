# 工作流与数据边界

Lightroom 导出选中的原片 → Python 生成清单与带编号的联系表 → 当前 Codex 对话看图并编写 JSON → Python 校验并发布两份 CSV → Lightroom 生成每组代表照 → 用户确认 → Lightroom 续做其余虚拟副本。

| 模块 | 职责 |
| --- | --- |
| `ExportPreviews.lua` | 请求渲染后的 JPEG，记录原片 UUID、路径、目录标识、显影指纹和支持的滑块读数。全部完成后发布 manifest |
| `scanner.py`、`contact_sheets.py` | 解析 Lightroom 或文件夹输入；索引保留每格到源照片的映射 |
| `plan.py`、`report.py` | 校验 v1.0 JSON、源片覆盖和风格组，限制数值范围，生成报告和同一版本的预览与批量 CSV |
| `Csv.lua`、`Bounds.lua`、`Develop.lua` | 解析带引号的 CSV，独立检查参数边界，校验实际显影回读。测试检查 Python 与 Lua 的范围一致 |
| `ApplyPlan.lua` | 逐项核对目录、原片、版本及代表照；用户确认后仅修改与该原片关联的虚拟副本 |

## 版本和中断恢复

输出 CSV 中的 `revision` 由归一化方案的 SHA-256 派生。插件比较两份 CSV 的全部代表行，使用整份批量 CSV 的摘要标识一次修图版本。摘要用于判别内容变化。每张照片的完成记录保存在 Lightroom 插件专属目录属性中。

创建副本前写入待完成标记，验证返回对象是预期原片的虚拟副本，写入绝对值并回读；成功后记录副本 UUID。重试会定位已完成副本，或继续本版唯一的待完成副本。如发现有歧义的同名副本会指出原片。原片显影已改变时需重新导出；已手调代表照时需把修改同步到新方案并重新预览。旧版 manifest 缺少的指纹无法事后还原。

Lightroom 的显影接口具有版本差异。SDK 对虚拟副本、显影与写入事务的说明见 [Adobe SDK 入口](https://developer.adobe.com/lightroom-classic/) 和 [LrPhoto API 参考](https://lrc.mcor.dev/modules/LrPhoto.html)。
