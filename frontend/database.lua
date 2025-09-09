Database = Object:extend()

function Database:new()
    self.env = lmdb.env_create()
    if not self.env then
        error("Failed to create LMDB environment")
    end

    os.execute("mkdir -p ./chats_db")

    local ok = self.env:set_mapsize(10485760)
    if not ok then
        error("Failed to set mapsize")
    end

    local ok = self.env:open("./chats_db", 0, 0644)
    if not ok then
        error("Failed to open LMDB environment")
    end

    self.dbi = nil
end

function Database:_begin_transaction(readonly)
    local flags = readonly and lmdb.MDB_RDONLY or 0
    local txn = self.env:txn_begin(nil, flags)
    if not txn then
        error("Failed to begin transaction")
    end

    local dbi = txn:dbi_open(nil, 0)
    if not dbi then
        txn:abort()
        error("Failed to open database")
    end

    return txn, dbi
end

function Database:Create(key, value)
    if not key or not value then
        error("Key and value are required")
    end

    local txn, dbi = self:_begin_transaction(false)

    local str_value = type(value) == "string" and value or tostring(value)

    local success = txn:put(dbi, tostring(key), str_value, 0)
    if success then
        txn:commit()
        return true
    else
        txn:abort()
        return false, "Failed to store data"
    end
end

function Database:Read(key)
    if not key then
        error("Key is required")
    end

    local txn, dbi = self:_begin_transaction(true)

    local value = txn:get(dbi, tostring(key))
    txn:abort()

    return value
end

function Database:Update(key, value)
    return self:Create(key, value)
end

function Database:Delete(key)
    if not key then
        error("Key is required")
    end

    local txn, dbi = self:_begin_transaction(false)

    local success = txn:del(dbi, tostring(key), nil)
    if success then
        txn:commit()
        return true
    else
        txn:abort()
        return false, "Key not found or failed to delete"
    end
end

function Database:Exists(key)
    local value = self:Read(key)
    return value ~= nil
end

function Database:Close()
    if self.env then
        self.env:close()
        self.env = nil
    end
end
