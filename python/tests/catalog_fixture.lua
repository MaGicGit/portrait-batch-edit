-- A small SDK double. Only selection-based createVirtualCopies can produce a writable photo.
local modules, sources, byUuid, selected, props = {}, {}, {}, {}, {}
local catalog = {}
local function clone(t) local r = {}; for k,v in pairs(t) do r[k] = v end; return r end
local function newPhoto(id, path, master, name)
    local p = {localIdentifier=id, uuid="id-" .. id, path=path, master=master, copies={},
               name=name, settings={Exposure2012=0.2, Texture=3}}
    if master then p.settings = clone(master.settings) end
    function p:getRawMetadata(key)
        local fields = {uuid=self.uuid, path=self.path, isVirtualCopy=self.master ~= nil, masterPhoto=self.master,
                        virtualCopies=self.copies, fileFormat="RAW", width=20, height=40, isVideo=self.video or false}
        return fields[key]
    end
    function p:getFormattedMetadata(key) assert(key == "copyName"); return self.name end
    function p:checkPhotoAvailability() return true end
    function p:getDevelopSettings() return clone(self.settings) end
    function p:requestJpegThumbnail(w,h,cb) cb(jpegBytes); return {} end
    function p:applyDevelopSettings(settings)
        assert(self.master and catalog.writing, "write to master or outside gate")
        if failApply then failApply=false; error("simulated write failure") end
        if ignoreApply then return end
        for k,v in pairs(settings) do self.settings[k]=v end
    end
    byUuid[p.uuid] = p
    return p
end
function catalog:getPath() return "test.lrcat" end
function catalog:getTargetPhoto() return selected[1] end
function catalog:getTargetPhotos() return #selected > 0 and selected or sources end
function catalog:getFolderByPath(path)
    if path ~= sourceFolder then return nil end
    return {getPhotos=function(_, includeChildren)
        assert(includeChildren)
        local photos = {}
        for _, photo in ipairs(sources) do
            table.insert(photos, photo)
            for _, copy in ipairs(photo.copies) do table.insert(photos, copy) end
        end
        return photos
    end}
end
function catalog:setSelectedPhotos(photo, others)
    selected={photo}; for _, p in ipairs(others) do table.insert(selected,p) end
end
function catalog:createVirtualCopies(name)
    assert(not self.writing and #selected == 1)
    local src = selected[1]
    local p = newPhoto(100 * src.localIdentifier + #src.copies, src.path, src, name)
    table.insert(src.copies,p); selected={p}
    return selected
end
function catalog:findPhotoByUuid(uuid) return byUuid[uuid] end
function catalog:findPhotoByPath(path)
    for _,p in ipairs(sources) do if path==p.path then return p end end
end
function catalog:getPropertyForPlugin(plugin,k) return props[k] end
function catalog:setPropertyForPlugin(plugin,k,v) assert(self.writing); props[k]=v end
function catalog:withWriteAccessDo(name,fn)
    assert(not self.writing); self.writing=true
    local ok,err=pcall(fn)
    self.writing=false; assert(ok,err)
end
for i=1,3 do sources[i]=newPhoto(i, sourcePath(i)); selected[i]=sources[i] end
local progress = {setPortionComplete=function() end, setCaption=function() end,
                  isCanceled=function() return cancelProgress end, done=function() end}
modules.LrApplication = {activeCatalog=function() return catalog end}
modules.LrMD5 = {digest=md5}
modules.LrTasks = {pcall=pcall}
modules.LrFunctionContext = {postAsyncTaskWithContext=function(t,fn) fn({}) end,
                             callWithContext=function(t,fn) fn({}) end}
modules.LrPathUtils = {leafName=leaf, parent=parent, child=child, isAbsolute=isAbsolute,
                       getStandardFilePath=function(key) return assert(({home=requestHome, temp=tempDir})[key]) end}
modules.LrFileUtils = {exists=exists, readFile=read, createAllDirectories=mkdir, move=move,
                       chooseUniqueFileName=function(path) assert(not exists(path)); return path end}
modules.LrDate = {currentTime=os.time}
modules.LrDialogs = {runOpenPanel=function() panelCount=(panelCount or 0)+1; return {chosenPath} end,
                     showError=function(msg) lastError=msg end,
                     message=function(title, msg) lastMessage=msg end,
                     showModalProgressDialog=function() return progress end,
                     confirm=function() return answer end}
function import(name) return assert(modules[name], name) end
function copyCount(i) return #sources[i].copies end
function settings(i, copy) return (copy and sources[i].copies[1] or sources[i]).settings end
_PLUGIN={}; WIN_ENV=true; answer="ok"
