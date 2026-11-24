# Portrait Batch Edit 插件

在 Lightroom Classic 的增效工具管理器中添加本目录。插件声明最低 SDK 11.0，命令位于图库的 Plug-in Extras 菜单。

- `Export Selected Previews` 将选中的原片导出为 JPEG 预览与 `lightroom-manifest.csv`。选择一个新的工作目录，Windows 上建议使用英文工作路径。
- `Apply Plan to Virtual Copies` 接受 `preview-plan.csv` 和 `apply-plan.csv`，两份文件须位于同一目录。预览只创建每组代表照；用户认可后，批量入口续做该版本其余照片。同名副本的创建、进度和错误都会在 Lightroom 中显示。

局部精修建议保存在 Python 生成的 HTML 报告与 CSV 中。
