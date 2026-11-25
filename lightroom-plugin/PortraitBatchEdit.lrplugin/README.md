# Portrait Batch Edit 插件

从仓库根目录运行 `.\scripts\install-lightroom-plugin.ps1` 安装，也可在 Lightroom Classic 增效工具管理器中添加本目录。插件声明最低 SDK 11.0。

- 在 Codex 中调用 `$portrait-batch-edit` 并指定当前选区或已导入的原片文件夹，插件会将 JPEG 预览与 `lightroom-manifest.csv` 写入本批工作目录。按文件夹导出包含子目录里的原片。
- 在 Lightroom 图库的 Plug-in Extras 菜单使用 `Export Selected Previews` 可手工导出选区并选择工作目录。
- `Apply Plan to Virtual Copies` 接受 `preview-plan.csv` 和 `apply-plan.csv`，两份文件须位于同一目录。预览只创建每组代表照；用户认可后，批量入口续做该版本其余照片。同名副本的创建、进度和错误都会在 Lightroom 中显示。

局部精修建议保存在 Python 生成的 HTML 报告与 CSV 中。
