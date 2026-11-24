local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local Csv = require "Csv"
local Develop = require "Develop"
local runTask = require "Task"

local function readPlans(path)
    local dir = LrPathUtils.parent(path)
    local function read(name)
        return assert(LrFileUtils.readFile(LrPathUtils.child(dir, name)), "找不到 " .. name)
    end
    local fullText = read("apply-plan.csv")
    local rows, header = Csv.parse(fullText)
    local preview, previewHeader = Csv.parse(read("preview-plan.csv"))
    assert(#rows > 0 and #preview > 0, "方案缺少照片")
    assert(table.concat(header, "\t") == table.concat(previewHeader, "\t"), "两份 CSV 的版本不同")
    local meta = {revision=true, source_path=true, uuid=true, catalog_id=true, develop_stamp=true,
                  style_group=true, representative=true}
    for _, key in ipairs(header) do
        assert(meta[key] or Develop.bounds[key], "未知 CSV 字段 " .. key)
    end
    for key in pairs(meta) do assert(rows[1][key], "请用新版 validate 重新导出 CSV") end

    local groups, sources, count = {}, {}, 0
    local revision = rows[1].revision
    assert(#revision == 64 and revision:match("^%x+$"), "版本标识无效")
    for _, row in ipairs(rows) do
        assert(row.revision == revision and row.style_group ~= "" and row.source_path ~= "", "方案行无效")
        assert(not sources[row.source_path], "原片路径重复 " .. row.source_path)
        sources[row.source_path] = true
        local group = row.style_group
        groups[group] = groups[group] or 0
        assert(row.representative == "0" or row.representative == "1", "代表照标志无效")
        if row.representative == "1" then
            count = count + 1
            groups[group] = groups[group] + 1
            local other = assert(preview[count], "缺少代表照")
            for _, key in ipairs(header) do
                assert(row[key] == other[key], "预览与批量方案不一致，请重新运行 validate")
            end
        end
        row.settings = Develop.settings(row)
    end
    assert(count == #preview, "预览照片数量不匹配")
    for group, n in pairs(groups) do assert(n == 1, "每组需要一张代表照 " .. group) end
    return rows, Develop.digest(fullText), count
end

local function checkSource(catalog, row)
    local photo
    if row.uuid ~= "" then
        photo = catalog:findPhotoByUuid(row.uuid)
    else
        photo = catalog:findPhotoByPath(row.source_path)
    end
    assert(photo and not photo:getRawMetadata("isVirtualCopy") and not photo:getRawMetadata("isVideo"),
           "目录中找不到原片 " .. row.source_path)
    local function pathKey(path)
        if WIN_ENV then return path:gsub("/", "\\"):lower() end
        return path
    end
    assert(pathKey(photo:getRawMetadata("path")) == pathKey(row.source_path), "原片路径已变更 " .. row.source_path)
    if row.develop_stamp ~= "" then
        assert(Develop.stamp(photo:getDevelopSettings()) == row.develop_stamp,
               "原片显影设置已更改，请重新导出预览 " .. row.source_path)
    end
    assert(photo:checkPhotoAvailability(), "原片离线 " .. row.source_path)
    return photo
end

local function matches(copy, source)
    if not copy or not copy:getRawMetadata("isVirtualCopy") then return false end
    local master = copy:getRawMetadata("masterPhoto")
    return master and master.localIdentifier == source.localIdentifier
end

local function completedCopy(catalog, item, requirePreviewStamp)
    local uuid = catalog:getPropertyForPlugin(_PLUGIN, item.key)
    if not uuid or uuid == "pending" then return nil end
    local copy = catalog:findPhotoByUuid(uuid)
    if matches(copy, item.source) then
        if requirePreviewStamp then
            assert(Develop.stamp(copy:getDevelopSettings()) == catalog:getPropertyForPlugin(_PLUGIN, item.key .. "_stamp"),
                   "代表照在预览后被手动修改。请将改动写入方案，重新生成预览 " .. item.row.source_path)
        end
        return copy
    end
end

local function applyOne(catalog, item, name)
    if completedCopy(catalog, item) then return false end
    local source, row = item.source, item.row
    checkSource(catalog, row)
    -- A crash between createVirtualCopies and the write transaction can leave one named copy.
    local pending = catalog:getPropertyForPlugin(_PLUGIN, item.key) == "pending"
    local copy
    for _, candidate in ipairs(source:getRawMetadata("virtualCopies") or {}) do
        if candidate:getFormattedMetadata("copyName") == name then
            assert(pending and not copy and matches(candidate, source),
                   "有同名副本，请检查并重命名后重试 " .. row.source_path)
            copy = candidate
        end
    end
    if not copy then
        catalog:withWriteAccessDo("记录待创建的虚拟副本", function()
            catalog:setPropertyForPlugin(_PLUGIN, item.key, "pending")
        end)
        catalog:setSelectedPhotos(source, {})
        local selected = catalog:getTargetPhotos()
        assert(catalog:getTargetPhoto() == source and #selected == 1 and selected[1] == source,
               "无法单选原片。请切换到图库的所有照片并检查筛选条件 " .. row.source_path)
        local copies = catalog:createVirtualCopies(name)
        assert(copies and #copies == 1 and matches(copies[1], source), "Lightroom 返回的虚拟副本与原片不匹配")
        copy = copies[1]
    end
    catalog:withWriteAccessDo("AI 人像显影", function()
        assert(matches(copy, source), "虚拟副本身份校验失败")
        if next(row.settings) then copy:applyDevelopSettings(row.settings, "AI Portrait Retoucher") end
    end)
    local applied = copy:getDevelopSettings()
    Develop.verify(applied, row.settings)
    local stamp = row.representative == "1" and Develop.stamp(applied)
    catalog:withWriteAccessDo("记录已完成的虚拟副本", function()
        catalog:setPropertyForPlugin(_PLUGIN, item.key, assert(copy:getRawMetadata("uuid")))
        if stamp then catalog:setPropertyForPlugin(_PLUGIN, item.key .. "_stamp", stamp) end
    end)
    return true
end

runTask("AI 人像批量修图", function(context)
    local selected = LrDialogs.runOpenPanel {
        title = "选择 preview-plan.csv 或 apply-plan.csv", fileTypes = {"csv"},
        canChooseFiles = true, canChooseDirectories = false, allowsMultipleSelection = false,
    }
    if not selected or not selected[1] then return end
    local file = LrPathUtils.leafName(selected[1])
    local preview = file == "preview-plan.csv"
    assert(preview or file == "apply-plan.csv", "请选择 validate 生成的预览或批量 CSV")
    local rows, digest, reps = readPlans(selected[1])
    local catalog = LrApplication.activeCatalog()
    local catalogId = Develop.digest(catalog:getPath())
    local name = "AI Retouch " .. digest
    local work, seen, existing = {}, {}, 0
    for _, row in ipairs(rows) do
        assert(row.catalog_id == "" or row.catalog_id == catalogId, "请打开导出该批次时使用的 Lightroom 目录")
        local source = checkSource(catalog, row)
        local id = source.localIdentifier
        assert(not seen[id], "计划重复引用同一原片 " .. row.source_path)
        seen[id] = true
        local item = {source = source, row = row, key = "copy_" .. digest .. "_" .. tostring(id)}
        local done = completedCopy(catalog, item, row.representative == "1")
        if not preview and row.representative == "1" then
            assert(done, "请先打开同目录的 preview-plan.csv，生成并检查本版每组代表照")
        end
        if not preview or row.representative == "1" then
            if done then existing = existing + 1 else work[#work + 1] = item end
        end
    end
    if #work == 0 then
        LrDialogs.message("本版副本已就绪", "已存在 " .. existing .. " 张\n副本名称 " .. name, "info")
        return
    end
    local title = preview and "创建每组的代表照预览？" or "已检查并认可此版本的代表照效果？"
    local answer = LrDialogs.confirm(title,
        reps .. " 个风格组，新建或续做 " .. #work .. " 张，沿用已完成 " .. existing .. " 张。\n副本名称 " .. name,
        preview and "生成预览" or "确认并批量应用", "取消")
    if answer ~= "ok" then return end
    local progress = LrDialogs.showModalProgressDialog {title = title, functionContext = context, cannotCancel = false}
    local applied = 0
    for i, item in ipairs(work) do
        if progress:isCanceled() then break end
        progress:setCaption(i .. " / " .. #work .. "   " .. item.row.source_path)
        if applyOne(catalog, item, name) then applied = applied + 1 end
        progress:setPortionComplete(i, #work)
    end
    progress:done()
    LrDialogs.message("AI 人像批量修图", "本次完成 " .. applied .. " 张，已存在 " .. existing ..
        " 张，待完成 " .. (#work - applied) .. " 张。\n副本名称 " .. name ..
        (preview and "\n请在修改照片模块检查各组代表照。" or ""), "info")
end)
