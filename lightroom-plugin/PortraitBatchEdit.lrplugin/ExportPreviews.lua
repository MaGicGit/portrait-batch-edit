local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrTasks = import "LrTasks"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local LrDate = import "LrDate"
local Csv = require "Csv"
local Develop = require "Develop"
local runTask = require "Task"

local function writeNew(path, data)
    assert(not LrFileUtils.exists(path), "文件已存在，请选择新的工作目录 " .. path)
    local f, err = io.open(path, "wb")
    assert(f, tostring(err) .. " " .. path)
    local ok, why = f:write(data)
    local closed, reason = f:close()
    assert(ok and closed, why or reason or "写入失败")
end

local function thumbnail(photo, progress)
    local done, jpeg, err
    local request = photo:requestJpegThumbnail(2048, 2048, function(data, message)
        jpeg, err, done = data, message, true
    end)
    local deadline = LrDate.currentTime() + 120
    while not done do
        assert(request and LrDate.currentTime() < deadline, "Lightroom 预览请求超时")
        if progress:isCanceled() then return nil end
        LrTasks.sleep(0.05)
    end
    return assert(jpeg, err or "Lightroom 未返回预览")
end

runTask("导出人像预览", function(context)
    local catalog = LrApplication.activeCatalog()
    assert(catalog:getTargetPhoto(), "请先在图库选中原片")
    local photos = catalog:getTargetPhotos()
    for _, photo in ipairs(photos) do
        assert(not photo:getRawMetadata("isVirtualCopy") and not photo:getRawMetadata("isVideo"),
               "请仅选择作为本次修图起点的原片，排除视频及虚拟副本")
    end
    local folders = LrDialogs.runOpenPanel {
        title = "选择新的工作目录（Windows 建议使用英文工作路径）", prompt = "选择目录",
        canChooseFiles = false, canChooseDirectories = true, canCreateDirectories = true,
        allowsMultipleSelection = false,
    }
    if not folders or not folders[1] then return end
    local root = folders[1]
    local previewDir = LrPathUtils.child(root, "previews")
    local manifest = LrPathUtils.child(root, "lightroom-manifest.csv")
    assert(not LrFileUtils.exists(manifest) and not LrFileUtils.exists(previewDir),
           "该目录已有导出结果。请为本次导出选择新的目录。")
    LrFileUtils.createAllDirectories(previewDir)
    local progress = LrDialogs.showModalProgressDialog {
        title = "正在导出 Lightroom 预览", functionContext = context, cannotCancel = false,
    }
    local keys = {}
    for key in pairs(Develop.bounds) do keys[#keys + 1] = key end
    table.sort(keys)
    local header = {"local_identifier", "uuid", "source_path", "file_name", "preview_path",
                    "width", "height", "captured_at", "file_format", "catalog_id", "develop_stamp"}
    for _, key in ipairs(keys) do header[#header + 1] = "base_" .. key end
    local lines = {table.concat(header, ",")}
    local catalogId = Develop.digest(catalog:getPath())
    for i, photo in ipairs(photos) do
        if progress:isCanceled() then return end
        progress:setCaption(i .. " / " .. #photos)
        local current = photo:getDevelopSettings()
        local stamp = Develop.stamp(current)
        local data = thumbnail(photo, progress)
        if not data or progress:isCanceled() then return end
        assert(stamp == Develop.stamp(photo:getDevelopSettings()), "导出过程中原片显影设置已更改，请重新导出")
        local uuid = assert(photo:getRawMetadata("uuid"))
        assert(uuid:match("^[%w%-_]+$"), "无效照片 UUID")
        local preview = LrPathUtils.child(previewDir, "photo_" .. uuid .. ".jpg")
        writeNew(preview, data)
        local source = photo:getRawMetadata("path")
        local values = {photo.localIdentifier, uuid, source, LrPathUtils.leafName(source), preview,
                        photo:getRawMetadata("width") or "", photo:getRawMetadata("height") or "",
                        photo:getRawMetadata("dateTimeOriginalISO8601") or "",
                        photo:getRawMetadata("fileFormat") or "", catalogId, stamp}
        for _, key in ipairs(keys) do
            values[#values + 1] = type(current[key]) == "number" and current[key] or ""
        end
        for j, value in ipairs(values) do values[j] = Csv.quote(value) end
        lines[#lines + 1] = table.concat(values, ",")
        progress:setPortionComplete(i, #photos)
    end
    local temp = LrPathUtils.child(root, "lightroom-manifest.tmp")
    writeNew(temp, table.concat(lines, "\r\n") .. "\r\n")
    assert(LrFileUtils.move(temp, manifest), "发布清单失败")
    progress:done()
    LrDialogs.message("预览已导出", #photos .. " 张\n" .. manifest, "info")
end)
