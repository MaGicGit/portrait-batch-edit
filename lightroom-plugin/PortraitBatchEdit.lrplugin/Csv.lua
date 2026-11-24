local Csv = {}

function Csv.quote(value)
    return '"' .. tostring(value or ""):gsub('"', '""') .. '"'
end

function Csv.parse(text)
    text = text:gsub("^\239\187\191", "")
    local records, fields, value = {}, {}, {}
    local quoted, closed = false, false
    local function endField()
        fields[#fields + 1] = table.concat(value)
        value, closed = {}, false
    end
    local i = 1
    while i <= #text do
        local ch = text:sub(i, i)
        if quoted then
            if ch ~= '"' then
                value[#value + 1] = ch
            elseif text:sub(i + 1, i + 1) == '"' then
                value[#value + 1] = '"'
                i = i + 1
            else
                quoted, closed = false, true
            end
        elseif ch == "," then
            endField()
        elseif ch == "\n" or ch == "\r" then
            endField()
            if #fields > 1 or fields[1] ~= "" then records[#records + 1] = fields end
            fields = {}
            if ch == "\r" and text:sub(i + 1, i + 1) == "\n" then i = i + 1 end
        elseif ch == '"' then
            assert(#value == 0 and not closed, "CSV 引号位置错误")
            quoted = true
        else
            assert(not closed, "CSV 引号后有多余字符")
            value[#value + 1] = ch
        end
        i = i + 1
    end
    assert(not quoted, "CSV 引号未闭合")
    if #fields > 0 or #value > 0 or closed then
        endField()
        records[#records + 1] = fields
    end
    local header = assert(records[1], "CSV 为空")
    local seen, rows = {}, {}
    for _, key in ipairs(header) do
        assert(key ~= "" and not seen[key], "CSV 表头重复或为空")
        seen[key] = true
    end
    for n = 2, #records do
        assert(#records[n] == #header, "CSV 列数错误，记录 " .. n)
        local row = {}
        for c, key in ipairs(header) do row[key] = records[n][c] end
        rows[#rows + 1] = row
    end
    return rows, header
end

return Csv
