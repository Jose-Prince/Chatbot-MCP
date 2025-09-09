-- components/chat.lua
Chat = Object:extend()
require "components.textInput"
require "components.button"

function Chat:new(width, height, sideBarWidth, db)
    local inputWidth = 300
    local inputHeight = 30

    local x = sideBarWidth + (width - sideBarWidth - inputWidth) / 2
    local y = height - inputHeight - 10

    self.queryInput = TextInput(x, y, inputWidth, inputHeight)
    self.sendButton = Button()

    local buttonWidth = 80
    local buttonHeight = inputHeight
    local buttonX = x + inputWidth + 10
    local buttonY = y
    self.sendButton = Button(buttonX, buttonY, buttonWidth, buttonHeight, "Enviar", function()
        local mensaje = self.queryInput.text
        if mensaje ~= "" then
            self:sendMessage(mensaje)
            self.queryInput.text = ""
            self.queryInput.cursorPos = 0
        end
    end)

    self.db = db

    -- Message history
    self.messages = {}
    self.scrollOffset = 0
    self.maxMessages = 100
end

function Chat:addMessage(sender, content)
    table.insert(self.messages, {sender = sender, content = content})

    -- Auto-scroll al último mensaje
    local visibleCount = self:getVisibleMessageCount()
    if #self.messages > visibleCount then
        self.scrollOffset = #self.messages - visibleCount
    else
        self.scrollOffset = 0
    end
end

function Chat:getVisibleMessageCount()
    local height = love.graphics.getHeight()
    local messageAreaHeight = height - height * 0.08 - 60
    local messageHeight = 25
    return math.floor(messageAreaHeight / messageHeight)
end

function Chat:drawMessages(width, height, sideBarWidth)
    -- Área de mensajes
    local messageAreaX = sideBarWidth + 10
    local messageAreaY = height * 0.08 + 10
    local messageAreaWidth = width - sideBarWidth - 20
    local messageAreaHeight = height - height * 0.08 - 60

    -- Fondo
    love.graphics.setColor(0.2, 0.2, 0.3, 0.8)
    love.graphics.rectangle("fill", messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)

    -- Activa recorte (scissor)
    love.graphics.setScissor(messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)

    -- Dibuja mensajes
    love.graphics.setColor(1, 1, 1, 1)
    local y = messageAreaY + 10
    local messageHeight = 25

    local startIndex = math.max(1, self.scrollOffset + 1)
    local endIndex = math.min(#self.messages, startIndex + self:getVisibleMessageCount() - 1)

    for i = startIndex, endIndex do
        local message = self.messages[i]
        local displayText = string.format("[%s]: %s", message.sender, message.content)

        -- Color por tipo de mensaje
        if message.sender == "You" then
            love.graphics.setColor(0.7, 0.9, 1, 1)
        elseif message.sender == "Assistant" then
            love.graphics.setColor(0.9, 1, 0.7, 1)
        elseif message.sender == "Error" then
            love.graphics.setColor(1, 0.7, 0.7, 1)
        else
            love.graphics.setColor(1, 1, 1, 1)
        end

        -- Word wrap
        local wrappedText = self:wrapText(displayText, messageAreaWidth - 20)
        for _, line in ipairs(wrappedText) do
            love.graphics.print(line, messageAreaX + 10, y)
            y = y + messageHeight
            if y > messageAreaY + messageAreaHeight - messageHeight then
                break
            end
        end
    end

    -- Desactiva scissor
    love.graphics.setScissor()
end

function Chat:wrapText(text, maxWidth)
    local font = love.graphics.getFont()
    local words = {}
    for word in text:gmatch("%S+") do
        table.insert(words, word)
    end
    
    local lines = {}
    local currentLine = ""
    
    for _, word in ipairs(words) do
        local testLine = currentLine == "" and word or currentLine .. " " .. word
        if font:getWidth(testLine) > maxWidth then
            if currentLine ~= "" then
                table.insert(lines, currentLine)
                currentLine = word
            else
                table.insert(lines, word)
            end
        else
            currentLine = testLine
        end
    end
    
    if currentLine ~= "" then
        table.insert(lines, currentLine)
    end
    
    return lines
end

function Chat:sendMessage(message)
    if message and message:trim() ~= "" then
        self:addMessage("You", message)
        networkManager:sendMessage(message)
    end
end

function Chat:draw(isNewChat, height, width, sideBarWidth)
    -- Background
    love.graphics.setColor(46/255, 41/255, 78/255)
    love.graphics.rectangle("fill", sideBarWidth, height * 0.08, width - sideBarWidth, height * 0.92)

    -- Draw messages
    --self:drawMessages(width, height, sideBarWidth)

    -- Draw input area
    local inputWidth = self.queryInput.width
    local inputHeight = self.queryInput.height
    self.queryInput.x = sideBarWidth + (width - sideBarWidth - inputWidth) / 2
    self.queryInput.y = height - inputHeight - 10
    self.queryInput:draw()

    local buttonX = self.queryInput.x + inputWidth + 10
    local buttonY = self.queryInput.y
    self.sendButton:SetPosition(buttonX, buttonY)
    self.sendButton:SetSize(80, inputHeight)
    self.sendButton:draw()

    -- Connection status indicator
    local statusText = networkManager.isConnected and "Connected" or "Disconnected"
    local statusColor = networkManager.isConnected and {0, 1, 0, 1} or {1, 0, 0, 1}
    
    love.graphics.setColor(statusColor)
    love.graphics.print(statusText, width - 100, 10)
    
    -- Show pending messages count if any
    if #networkManager.pendingMessages > 0 then
        love.graphics.setColor(1, 1, 0, 1) -- Yellow
        love.graphics.print("Pending: " .. #networkManager.pendingMessages, width - 100, 30)
    end
end

function Chat:scroll(amount)
    local visibleCount = self:getVisibleMessageCount()
    local maxOffset = math.max(0, #self.messages - visibleCount)

    self.scrollOffset = math.min(math.max(self.scrollOffset + amount, 0), maxOffset)
end

