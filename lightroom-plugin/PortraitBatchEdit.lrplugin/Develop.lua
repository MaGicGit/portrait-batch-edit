local LrMD5 = import "LrMD5"
local Develop = {bounds = require "Bounds"}

function Develop.digest(text)
    local digest = LrMD5.digest(text)
    if #digest == 16 then
        return (digest:gsub(".", function(c) return string.format("%02x", c:byte()) end))
    end
    return digest:lower()
end

-- Include inherited crops, profiles and masks, which can all change the preview.
local function encode(value)
    if type(value) == "table" then
        local fields = {}
        for key, item in pairs(value) do fields[#fields + 1] = encode(key) .. encode(item) end
        table.sort(fields)
        return "{" .. table.concat(fields) .. "}"
    end
    local s = type(value) == "number" and string.format("%.17g", value) or tostring(value)
    return type(value) .. #s .. ":" .. s
end

function Develop.stamp(settings)
    return Develop.digest(encode(settings))
end

function Develop.settings(row)
    local result = {}
    for key, bounds in pairs(Develop.bounds) do
        local raw = row[key]
        if raw and raw ~= "" then
            local value = tonumber(raw)
            assert(value and value >= bounds[1] and value <= bounds[2], "显影参数超限 " .. key)
            result[key] = value
        end
    end
    if result.Temperature or result.Tint or result.IncrementalTemperature or result.IncrementalTint then
        result.WhiteBalance = "Custom"
    end
    return result
end

-- Lightroom may quantize slider values to its display precision.
function Develop.verify(applied, requested)
    for key, target in pairs(requested) do
        if type(target) == "number" then
            local tolerance = 0.50001
            if key == "Exposure2012" then tolerance = 0.00501 end
            if key == "SharpenRadius" then tolerance = 0.05001 end
            local actual = applied[key]
            assert(type(actual) == "number" and math.abs(actual - target) <= tolerance,
                   "Lightroom 未保留目标参数 " .. key .. "，实际值 " .. tostring(actual))
        end
    end
end

return Develop
