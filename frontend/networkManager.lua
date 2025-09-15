NetworkManager = Object:extend()

function NetworkManager:new()
    self.client = nil
    self.isConnected = false
    self.host = "127.0.0.1"
    self.port = 8081
    self.reconnectTimer = 0
    self.reconnectInterval = 5
    self.responseBuffer = ""
    self.pendingMessages = {}
    self.waitingForResponse = false
    self.lastMessageTime = 0
    self.responseTimeout = 30
    self.debugMode = false
end

function NetworkManager:connect()
    if self.debugMode then
        print("Trying to connect to " .. self.host .. ":" .. self.port)
    end
    
    if self.client then
        self.client:close()
    end

    self.client = socket.tcp()
    self.client:settimeout(0.001)

    local success, err = self.client:connect(self.host, self.port)
    if success then
        self.isConnected = true
        if self.debugMode then
            print("Connected to MCP server!")
        end
        return true
    else
        if self.debugMode then
            print("Connection failed:", err)
        end
        self.isConnected = false
        return false
    end
end

function NetworkManager:update(dt)
    if not self.isConnected then
        self.reconnectTimer = self.reconnectTimer + dt
        if self.reconnectTimer >= self.reconnectInterval then
            self.reconnectTimer = 0
            if self.debugMode then
                print("Attempting to reconnect...")
            end
            self:connect()
        end
        return
    end

    if self.waitingForResponse then
        local currentTime = os.clock()
        if currentTime - self.lastMessageTime > self.responseTimeout then
            if self.debugMode then
                print("Response timeout")
            end
            self.waitingForResponse = false
            if chat then
                chat:addMessage("System", "Timeout: No response from server")
            end
        end
    end

    self:receiveData()

    self:sendPendingMessages()
end

function NetworkManager:receiveData()
    if not self.client or not self.isConnected then return end

    local data, err, partial = self.client:receive("*a")
    
    if partial and partial ~= "" then
        if self.debugMode then
            print("Partial data received (" .. #partial .. " bytes):", partial)
        end
        data = partial
        err = nil
    end

    if data and data ~= "" then
        if self.debugMode then
            print("Full data received (" .. #data .. " bytes):", data)
        end
        self.responseBuffer = self.responseBuffer .. data
        self:processResponses()
    elseif err == "closed" then
        if self.debugMode then
            print("Connection closed by server")
        end
        self.isConnected = false
        self.client = nil
        self.waitingForResponse = false
    elseif err == "timeout" then
    elseif err then
        if self.debugMode then
            print("Error receiving data:", err)
        end
    end
end

function NetworkManager:processResponses()
    if self.debugMode then
        print("Processing response buffer (length: " .. #self.responseBuffer .. "):", self.responseBuffer)
    end

    while true do
        local lineEnd = self.responseBuffer:find("\n")
        if not lineEnd then
            break
        end

        local line = self.responseBuffer:sub(1, lineEnd - 1)
        self.responseBuffer = self.responseBuffer:sub(lineEnd + 1)

        if self:trim(line) ~= "" then
            if self.debugMode then
                print("Processing complete line:", line)
            end
            self:handleResponse(line)
        end
    end
end

function NetworkManager:handleResponse(responseData)
    if self.debugMode then
        print("Handling response:", responseData)
    end
    self.waitingForResponse = false

    local success, response = pcall(function()
        return json.decode(responseData)
    end)

    if success and response and type(response) == "table" then
        if self.debugMode then
            print("JSON parsed successfully - Status:", response.status, "Data:", response.data, "Error:", response.error)
        end

        if response.status == "success" then
            local data = response.data or "Empty response"
            if self.debugMode then
                print("Success response, adding to chat:", data)
            end
            if chat then
                chat:addMessage("Assistant", tostring(data))
            end
        elseif response.status == "error" then
            local error = response.error or "Unknown error"
            if self.debugMode then
                print("Error response:", error)
            end
            if chat then
                chat:addMessage("Error", "Error: " .. tostring(error))
            end
        else
            if self.debugMode then
                print("Unknown status:", response.status)
            end
            if chat then
                chat:addMessage("System", "Unknown response: " .. tostring(response.status))
            end
        end
    else
        if self.debugMode then
            print("JSON parsing failed, treating as plain text")
            print("Parse error - success:", success, "response type:", type(response))
        end

        if chat then
            chat:addMessage("Assistant", tostring(responseData))
        end
    end
end

function NetworkManager:sendMessage(message)
    if self.debugMode then
        print("Attempting to send message:", message)
    end

    if not self.isConnected then
        table.insert(self.pendingMessages, message)
        if self.debugMode then
            print("Message queued (not connected):", message)
        end
        return false
    end

    local messageWithNewline = message .. "\n"
    local success, err = self.client:send(messageWithNewline)

    if success then
        if self.debugMode then
            print("Message sent successfully:", message)
        end
        self.waitingForResponse = true
        self.lastMessageTime = os.clock()
        return true
    else
        if self.debugMode then
            print("Failed to send message:", err)
        end
        self.isConnected = false
        self.waitingForResponse = false
        table.insert(self.pendingMessages, message)
        return false
    end
end

function NetworkManager:sendPendingMessages()
    if not self.isConnected then return end

    while #self.pendingMessages > 0 do
        local message = table.remove(self.pendingMessages, 1)
        if self.debugMode then
            print("Sending pending message:", message)
        end
        if not self:sendMessage(message) then
            table.insert(self.pendingMessages, 1, message)
            break
        end
    end
end

function NetworkManager:getConnectionStatus()
    if self.isConnected then
        return "Connected"
    elseif #self.pendingMessages > 0 then
        return "Disconnected (" .. #self.pendingMessages .. " pending)"
    else
        return "Disconnected"
    end
end

function NetworkManager:isWaitingForResponse()
    return self.waitingForResponse
end

function NetworkManager:setDebugMode(enabled)
    self.debugMode = enabled
end

function NetworkManager:close()
    if self.debugMode then
        print("Closing network connection...")
    end
    if self.client then
        self.client:close()
        self.client = nil
    end
    self.isConnected = false
    self.waitingForResponse = false
end

function NetworkManager:trim(s)
    if not s then return "" end
    return (s:gsub("^%s*(.-)%s*$", "%1"))
end
