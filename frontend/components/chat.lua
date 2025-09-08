-- components/chat.lua
Chat = Object:extend()
require "components.textInput"
require "components.button"

function Chat:new(width, height, sideBarWidth)
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
    
    -- Message history
    self.messages = {}
    self.scrollOffset = 0
    self.maxMessages = 100
    self.debugMode = true -- Enable debug logging
end

function Chat:addMessage(sender, content)
    local message = {
        sender = sender,
        content = tostring(content), -- Ensure content is a string
        timestamp = os.time()
    }
    
    table.insert(self.messages, message)
    
    if self.debugMode then
        print("💬 Message added to chat:")
        print("   Sender:", sender)
        print("   Content:", content)
        print("   Total messages:", #self.messages)
    end
    
    -- Limit message history
    if #self.messages > self.maxMessages then
        table.remove(self.messages, 1)
        if self.debugMode then
            print("   Removed old message, new total:", #self.messages)
        end
    end
    
    -- Auto-scroll to bottom
    self.scrollOffset = math.max(0, #self.messages - self:getVisibleMessageCount())
    
    if self.debugMode then
        print("   Scroll offset set to:", self.scrollOffset)
    end
end

function Chat:getVisibleMessageCount()
    -- Calculate how many messages can fit in the chat area
    local chatHeight = love.graphics.getHeight() - 150 -- Space for input and margins
    local messageHeight = 30 -- Height per message line
    local visibleCount = math.floor(chatHeight / messageHeight)
    
    if self.debugMode then
        print("📏 Visible message count calculated:", visibleCount, "chatHeight:", chatHeight)
    end
    
    return math.max(5, visibleCount) -- Minimum 5 messages visible
end

function Chat:drawMessages(width, height, sideBarWidth)
    -- Calculate message area dimensions
    local messageAreaX = sideBarWidth + 10
    local messageAreaY = height * 0.08 + 10
    local messageAreaWidth = width - sideBarWidth - 20
    local messageAreaHeight = height - height * 0.08 - 80 -- Leave space for input
    
    -- Background for message area
    love.graphics.setColor(0.2, 0.2, 0.3, 0.8)
    love.graphics.rectangle("fill", messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)
    
    -- Border for message area (for debugging)
    love.graphics.setColor(1, 1, 1, 0.3)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)
    
    -- Debug info
    if self.debugMode then
        love.graphics.setColor(1, 1, 0, 0.8)
        love.graphics.print("Messages: " .. #self.messages .. " | Scroll: " .. self.scrollOffset, messageAreaX + 10, messageAreaY + 5)
    end
    
    -- Draw messages
    love.graphics.setColor(1, 1, 1, 1)
    local y = messageAreaY + (self.debugMode and 25 or 10) -- Account for debug text
    local messageHeight = 25
    local lineHeight = 20
    
    if #self.messages == 0 then
        -- Show "no messages" indicator
        love.graphics.setColor(0.7, 0.7, 0.7, 1)
        love.graphics.print("No messages yet. Send a message to start chatting!", messageAreaX + 10, y)
        return
    end
    
    local startIndex = math.max(1, self.scrollOffset + 1)
    local endIndex = math.min(#self.messages, startIndex + self:getVisibleMessageCount() - 1)
    
    if self.debugMode then
        print("🎨 Drawing messages from", startIndex, "to", endIndex, "out of", #self.messages)
    end
    
    for i = startIndex, endIndex do
        local message = self.messages[i]
        if not message then
            if self.debugMode then
                print("⚠️ Message at index", i, "is nil!")
            end
            goto continue
        end
        
        local displayText = string.format("[%s]: %s", message.sender or "Unknown", message.content or "")
        
        -- Set color based on sender
        if message.sender == "You" then
            love.graphics.setColor(0.7, 0.9, 1, 1) -- Light blue for user
        elseif message.sender == "Assistant" then
            love.graphics.setColor(0.9, 1, 0.7, 1) -- Light green for assistant
        elseif message.sender == "Error" then
            love.graphics.setColor(1, 0.7, 0.7, 1) -- Light red for errors
        elseif message.sender == "System" then
            love.graphics.setColor(1, 1, 0.7, 1) -- Light yellow for system
        else
            love.graphics.setColor(1, 1, 1, 1) -- White for others
        end
        
        -- Word wrap for long messages
        local wrappedText = self:wrapText(displayText, messageAreaWidth - 20)
        for lineIndex, line in ipairs(wrappedText) do
            if y + lineHeight > messageAreaY + messageAreaHeight - 10 then
                break
            end
            love.graphics.print(line, messageAreaX + 10, y)
            y = y + lineHeight
        end
        
        y = y + 5 -- Small gap between messages
        
        ::continue::
    end
end

function Chat:wrapText(text, maxWidth)
    local font = love.graphics.getFont()
    local words = {}
    
    -- Split text into words
    for word in tostring(text):gmatch("%S+") do
        table.insert(words, word)
    end
    
    local lines = {}
    local currentLine = ""
    
    for _, word in ipairs(words) do
        local testLine = currentLine == "" and word or currentLine .. " " .. word
        if font:getWidth(testLine) > maxWidth and maxWidth > 0 then
            if currentLine ~= "" then
                table.insert(lines, currentLine)
                currentLine = word
            else
                -- Word is too long, force it on its own line
                table.insert(lines, word)
                currentLine = ""
            end
        else
            currentLine = testLine
        end
    end
    
    if currentLine ~= "" then
        table.insert(lines, currentLine)
    end
    
    return #lines > 0 and lines or {""}
end

function Chat:sendMessage(message)
    if message and self:trim(message) ~= "" then
        if self.debugMode then
            print("📤 Chat: Sending message:", message)
        end
        
        self:addMessage("You", message)
        
        if networkManager then
            networkManager:sendMessage(message)
        else
            if self.debugMode then
                print("⚠️ NetworkManager not available!")
            end
            self:addMessage("Error", "Network not available")
        end
    end
end

function Chat:setDebugMode(enabled)
    self.debugMode = enabled
end

function Chat:draw(type, height, width, sideBarWidth)
    -- Background
    love.graphics.setColor(46/255, 41/255, 78/255)
    love.graphics.rectangle("fill", sideBarWidth, height * 0.08, width - sideBarWidth, height * 0.92)

    -- Draw messages
    self:drawMessages(width, height, sideBarWidth)

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
    if networkManager then
        local statusText = networkManager.isConnected and "Connected" or "Disconnected"
        local statusColor = networkManager.isConnected and {0, 1, 0, 1} or {1, 0, 0, 1}
        
        love.graphics.setColor(statusColor)
        love.graphics.print(statusText, width - 100, 10)
        
        -- Show pending messages count if any
        if #networkManager.pendingMessages > 0 then
            love.graphics.setColor(1, 1, 0, 1) -- Yellow
            love.graphics.print("Pending: " .. #networkManager.pendingMessages, width - 100, 30)
        end
        
        -- Show waiting for response indicator
        if networkManager:isWaitingForResponse() then
            love.graphics.setColor(1, 1, 0, 1) -- Yellow
            love.graphics.print("⏳ Waiting...", width - 100, 50)
        end
    end
end

-- Helper function to trim whitespace
function Chat:trim(s)
    if not s then return "" end
    return (s:gsub("^%s*(.-)%s*$", "%1"))
end
