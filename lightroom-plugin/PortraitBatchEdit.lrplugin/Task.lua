local Context = import "LrFunctionContext"
local Dialogs = import "LrDialogs"
local Tasks = import "LrTasks"

return function(title, run)
    Context.postAsyncTaskWithContext(title, function()
        local ok, err = Tasks.pcall(function()
            Context.callWithContext(title, run)
        end)
        if not ok then Dialogs.showError(title .. "\n" .. tostring(err)) end
    end)
end
