NetworkManager = Object:extend()

function NetworkManager:new()
    self.client = nil
    self.isConnected = false
    self.host = "127.0.0.1"
    self.port = 8080
    self.reconnectTimer = 0
    self.reconnectInterval = 5
    self.responseBuffer = ""
    self.pendingMessages = {}
end

function NetworkManager:connect()
    if self.client then
        self.client:close()
    end

    self.client = socket.tcp()
    self.client:settimeout(5) -- Non-blocking

    local success, err = self.client:connect(self.host, self.port)
    if success then
        self.isConnected = true
        print("Conectado al servidor MCP")
        return true
    else
        print("No se pudo conectar:", err)
        self.isConnected = false
        return false
    end
end


function NetworkManager:update(dt)
    if not self.isConnected then
        self.reconnectTimer = self.reconnectTimer + dt
        if self.reconnectTimer >= self.reconnectInterval then
            self.reconnectTimer = 0
            print("Intentando reconectar...")
            self:connect()
        end
        return
    end

    -- Check for incoming data
    self:receiveData()

    -- Send any pending messages
    self:sendPendingMessages()
end

function NetworkManager:receiveData()
    if not self.client or not self.isConnected then return end

    local data, err = self.client:receive("*a")
    if data then
        self.responseBuffer = self.responseBuffer .. data
        self:processResponses()
    elseif err == "closed" then
        print("Conexión cerrada por el servidor")
        self.isConnected = false
        self.client = nil
    elseif err ~= "timeout" then
        print("Error recibiendo datos:", err)
        self.isConnected = false
    end
end

function NetworkManager:processResponses()
    -- Process complete JSON responses (assuming each response ends with newline)
    while self.responseBuffer:find("\n") do
        local lineEnd = self.responseBuffer:find("\n")
        local line = self.responseBuffer:sub(1, lineEnd - 1)
        self.responseBuffer = self.responseBuffer:sub(lineEnd + 1)

        if line:trim() ~= "" then
            self:handleResponse(line)
        end
    end
end

function NetworkManager:handleResponse(responseData)
    print("Respuesta recibida:", responseData)
    -- Parse JSON response
    local success, response = pcall(function()
        return json.decode(responseData)
    end)
    
    if success and response then
        if response.status == "success" then
            chat:addMessage("Assistant", response.data)
        else
            chat:addMessage("Error", response.error or "Error desconocido")
        end
    else
        -- If JSON parsing fails, treat as plain text
        chat:addMessage("Assistant", responseData)
    end
end

function NetworkManager:sendMessage(message)
    if not self.isConnected then
        table.insert(self.pendingMessages, message)
        print("Mensaje agregado a la cola (no conectado)")
        return false
    end
    
    local success, err = self.client:send(message .. "\n")
    if success then
        print("Mensaje enviado:", message)
        return true
    else
        print("Error enviando mensaje:", err)
        self.isConnected = false
        table.insert(self.pendingMessages, message)
        return false
    end
end

function NetworkManager:sendPendingMessages()
    if not self.isConnected then return end
    
    while #self.pendingMessages > 0 do
        local message = table.remove(self.pendingMessages, 1)
        if not self:sendMessage(message) then
            -- Re-add message to front of queue if send failed
            table.insert(self.pendingMessages, 1, message)
            break
        end
    end
end

function NetworkManager:close()
    if self.client then
        self.client:close()
        self.client = nil
    end
    self.isConnected = false
end

