local LrApplication = import "LrApplication"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local Csv = require "Csv"
local PreviewExport = require "PreviewExport"
local runTask = require "Task"

local function handle(url)
    local id = url:match("^lightroom://com%.example%.portraitbatchedit/export/(req%-[a-z0-9_]+)$")
    if not id then return end
    runTask("Codex 导出人像预览", function(context)
        local child = LrPathUtils.child
        local base = child(LrPathUtils.getStandardFilePath("home"), "PortraitBatchEdit")
        local request = child(child(base, "requests"), id)
        local pending, running = child(request, "pending.csv"), child(request, "running.csv")
        -- Only a live local request can supply paths. Re-delivery cannot claim it twice.
        if not LrFileUtils.exists(pending) or not LrFileUtils.move(pending, running) then return end
        local ok, err = LrTasks.pcall(function()
            local rows = Csv.parse(assert(LrFileUtils.readFile(running)))
            local row = rows[1]
            assert(#rows == 1 and row.source_folder and LrPathUtils.isAbsolute(row.workdir), "无效的导出请求")
            local catalog = LrApplication.activeCatalog()
            local folder = row.source_folder ~= "" and row.source_folder or nil
            local photos = PreviewExport.photos(catalog, folder)
            assert(PreviewExport.write(context, catalog, photos, row.workdir, running), "预览导出已取消")
        end)
        if not LrFileUtils.exists(running) then return end
        if not ok then
            local written = LrTasks.pcall(function()
                PreviewExport.writeNew(child(request, "error.txt"), tostring(err))
            end)
            assert(LrFileUtils.move(running, child(request, "failed")), "无法报告导出失败")
            if not written then error(err) end
        else
            assert(LrFileUtils.move(running, child(request, "done")), "无法报告导出完成")
        end
    end)
end

return { URLHandler = handle }
