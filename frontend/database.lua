json = require("dkjson")

Database = Object:extend()

function Database:new()
    self.db_file = "chats_db.json"
    self.data = self:_load_data()
end

function Database:_load_data()
    local info = love.filesystem.getInfo(self.db_file)
    if info and info.type == "file" then
        local content = love.filesystem.read(self.db_file)
        if content and content ~= "" then
            local data, _, err = json.decode(content)
            if not err then
                return data
            end
        end
    end
    return {}
end

function Database:_save_data()
    local content = json.encode(self.data, { indent = true })
    local success, error_msg = love.filesystem.write(self.db_file, content)
    return success, error_msg
end

function Database:Create(key, value)
    self.data[key] = value
    return self:_save_data()
end

function Database:Read(key)
    if not key then
        error("Key is required")
    end

    return self.data[tostring(key)]
end

function Database:Update(key, value)
    self.data[key] = value
    return self:_save_data()
end

function Database:Delete(key)
    if not key then
        error("Key is required")
    end

    local key_str = tostring(key)
    if self.data[key_str] then
        self.data[key_str] = nil
        local success, error_msg = self:_save_data()

        if success then
            return true
        else
            return false, error_msg or "Failed to save data"
        end
    else
        return false, "Key not found"
    end
end

function Database:Exists(key)
    return self.data[tostring(key)] ~= nil
end

function Database:Close()
    self:_save_data()
end

function Database:GetAllKeys()
    local keys = {}
    for key, _ in pairs(self.data) do
        table.insert(keys, key)
    end
    return keys
end
