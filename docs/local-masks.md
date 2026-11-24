# 虚拟副本上的局部精修

打开 `output/report.html` 或 `local-adjustment-review.csv`，按原片完整路径找到对应副本。全局预览通过并完成批量后，在 Lightroom「修改照片 → 蒙版」中按需要操作。

| 方案目标 | Lightroom 选区 | 检查要点 |
| --- | --- | --- |
| `facial_skin` | 人物 → 面部皮肤 | 选择正确人物，避开眉毛和唇缘；在 100% 视图检查毛孔 |
| `iris_pupil` | 人物 → 虹膜和瞳孔 | 放大核实选区，保留原有眼白与反光亮度 |
| `hair` | 人物 → 头发 | 检查发丝边缘与逆光轮廓，控制阴影及纹理 |
| `background` | 选择背景 | 检查发梢、衣服与高光边界，依报告降低干扰 |
| `subject` | 选择主体 | 检查人物间遮挡，用轻量局部曝光调整明暗关系 |

报告中的滑块值是当前照片的建议。多人画面先确认目标人物；区域过小、被遮挡或识别失败时保留现状并记录复核结果。局部建议的状态为 `proposed_not_applied`。

自动化的下一项主机测试是在活动的 Develop 模块创建一个 People 或 Background 蒙版，逐个验证人物部位能否稳定选择、局部滑块可读回、切图和重启后能够保留。验收范围和顺序见 [开发计划](phase-plan.md)。操作名称参见 [Adobe Lightroom Classic 蒙版说明](https://helpx.adobe.com/lightroom-classic/desktop/process-and-develop-photos/masking.html)。
