local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local PreviewExport = require "PreviewExport"
local runTask = require "Task"

runTask("导出人像预览", function(context)
    local catalog = LrApplication.activeCatalog()
    local photos = PreviewExport.photos(catalog)
    local folders = LrDialogs.runOpenPanel {
        title = "选择新的工作目录", prompt = "选择目录",
        canChooseFiles = false, canChooseDirectories = true, canCreateDirectories = true,
        allowsMultipleSelection = false,
    }
    if not folders or not folders[1] then return end
    local manifest = PreviewExport.write(context, catalog, photos, folders[1])
    if manifest then LrDialogs.message("预览已导出", #photos .. " 张\n" .. manifest, "info") end
end)
