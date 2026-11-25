local LrDialogs = import "LrDialogs"
local LrTasks = import "LrTasks"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local LrDate = import "LrDate"
local Csv = require "Csv"
local Develop = require "Develop"
local PreviewExport = {}

function PreviewExport.writeNew(path, data)
    assert(not LrFileUtils.exists(path), "文件已存在，请选择新的工作目录 " .. path)
    local temp = path
    -- Lua's io.open on Windows may misinterpret UTF-8 directory names.
    if WIN_ENV and path:find("[\128-\255]") then
        temp = LrFileUtils.chooseUniqueFileName(LrPathUtils.child(
            LrPathUtils.getStandardFilePath("temp"), "portrait-" .. Develop.digest(path) .. ".tmp"))
    end
    local f, err = io.open(temp, "wb")
    assert(f, tostring(err) .. " " .. temp)
    local ok, why = f:write(data)
    local closed, reason = f:close()
    assert(ok and closed, why or reason or "写入失败")
    if temp ~= path then assert(LrFileUtils.move(temp, path), "写入失败 " .. path) end
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

function PreviewExport.photos(catalog, sourceFolder)
    local candidates
    if sourceFolder then
        local folder = assert(catalog:getFolderByPath(sourceFolder), "当前 Lightroom 目录未收录此文件夹 " .. sourceFolder)
        candidates = folder:getPhotos(true)
    else
        assert(catalog:getTargetPhoto(), "请先在 Lightroom 图库选中原片，或在提示词中指定已导入的原片目录")
        candidates = catalog:getTargetPhotos()
    end
    local photos = {}
    for _, photo in ipairs(candidates) do
        if not photo:getRawMetadata("isVirtualCopy") and not photo:getRawMetadata("isVideo") then
            photos[#photos + 1] = photo
        elseif not sourceFolder then
            error("请仅选择作为本次修图起点的原片，排除视频及虚拟副本")
        end
    end
    assert(#photos > 0, "指定范围内没有可导出的原片")
    if sourceFolder then
        table.sort(photos, function(a, b) return a.localIdentifier < b.localIdentifier end)
    end
    return photos
end

function PreviewExport.write(context, catalog, photos, root, runningRequest)
    local previewDir = LrPathUtils.child(root, "previews")
    local manifest = LrPathUtils.child(root, "lightroom-manifest.csv")
    assert(not LrFileUtils.exists(manifest) and not LrFileUtils.exists(previewDir),
           "该目录已有导出结果。请为本次导出选择新的目录。")
    local ok, created = LrFileUtils.createAllDirectories(previewDir)
    assert(ok and created, "无法创建新的预览目录 " .. previewDir)
    local progress = LrDialogs.showModalProgressDialog {
        title = "正在导出 Lightroom 预览", functionContext = context, cannotCancel = false,
    }
    local function canceled()
        return progress:isCanceled() or (runningRequest and not LrFileUtils.exists(runningRequest))
    end
    local keys = {}
    for key in pairs(Develop.bounds) do keys[#keys + 1] = key end
    table.sort(keys)
    local header = {"local_identifier", "uuid", "source_path", "file_name", "preview_path",
                    "width", "height", "captured_at", "file_format", "catalog_id", "develop_stamp"}
    for _, key in ipairs(keys) do header[#header + 1] = "base_" .. key end
    local lines = {table.concat(header, ",")}
    local catalogId = Develop.digest(catalog:getPath())
    for i, photo in ipairs(photos) do
        if canceled() then return end
        progress:setCaption(i .. " / " .. #photos)
        local current = photo:getDevelopSettings()
        local stamp = Develop.stamp(current)
        local data = thumbnail(photo, progress)
        if not data or canceled() then return end
        assert(stamp == Develop.stamp(photo:getDevelopSettings()), "导出过程中原片显影设置已更改，请重新导出")
        local uuid = assert(photo:getRawMetadata("uuid"))
        assert(uuid:match("^[%w%-_]+$"), "无效照片 UUID")
        local preview = LrPathUtils.child(previewDir, "photo_" .. uuid .. ".jpg")
        PreviewExport.writeNew(preview, data)
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
    if canceled() then return end
    local temp = LrPathUtils.child(root, "lightroom-manifest.tmp")
    PreviewExport.writeNew(temp, table.concat(lines, "\r\n") .. "\r\n")
    assert(LrFileUtils.move(temp, manifest), "发布清单失败")
    progress:done()
    return manifest
end

return PreviewExport
