Chat = Object:extend()
require "components.textInput"
require "components.button"

function Chat:new(width, height, sideBarWidth, db, font)
    local inputWidth = 300
    local inputHeight = 30

    local x = sideBarWidth + (width - sideBarWidth - inputWidth) / 2
    local y = height - inputHeight - 10

    self.queryInput = TextInput(x, y, inputWidth, inputHeight)

    local buttonWidth = 80
    local buttonHeight = inputHeight
    local buttonX = x + inputWidth + 10
    local buttonY = y
    self.sendButton = Button(buttonX, buttonY, buttonWidth, buttonHeight, "Enviar", function()
        self:sendMessage(self.queryInput.text)
    end)

    self.db = db
    self.newChat = true
    self.font = font

    self.messages = {}
    self.chatName = ""
    self.scrollOffset = 0

    self.bubbleColors = {
        You = {197/255, 216/255, 109/255, 1}, 
        Assistant = {18/255, 17/255, 51/255, 1}, 
    }

    self.textColors = {
        You = {18/255, 17/255, 51/255, 1},
        Assistant = {197/255, 216/255, 109/255, 1}, 
    }

    self.bubblePadding = 12
    self.bubbleMargin = 8
    self.maxBubbleWidth = 0.8
end

function Chat:addMessage(sender, content)
    table.insert(self.messages, {sender = sender, content = content})

    if not self.newChat and self.chatName and self.chatName ~= "" then
        self:saveMessagesToDatabase()
    end

    self:scrollToBottom()
end

function Chat:saveMessagesToDatabase()
    if self.chatName and self.chatName ~= "" then
        local success, error_msg = self.db:Update(self.chatName, self.messages)
        if not success then
            print("Error saving messages to database:", error_msg)
        end
    end
end

function Chat:scrollToBottom()
    self.scrollOffset = 0
end

function Chat:getVisibleMessageCount()
    local height = love.graphics.getHeight()
    local messageAreaHeight = height - height * 0.08 - 70
    local averageMessageHeight = 60
    return math.floor(messageAreaHeight / averageMessageHeight)
end

function Chat:drawMessages(width, height, sideBarWidth)
    -- Messages Area
    local messageAreaX = sideBarWidth + 10
    local messageAreaY = height * 0.08 + 10
    local messageAreaWidth = width - sideBarWidth - 20
    local messageAreaHeight = height - height * 0.08 - 70

    love.graphics.setColor(0.2, 0.2, 0.3, 0.8)  
    love.graphics.rectangle("fill", messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)

    love.graphics.setScissor(messageAreaX, messageAreaY, messageAreaWidth, messageAreaHeight)

    if self.newChat then
        local msg = "Start chatting with me"
        local textWidth = self.font:getWidth(msg)
        local textHeight = self.font:getHeight()

        local centerX = messageAreaX + (messageAreaWidth - textWidth) / 2
        local centerY = messageAreaY + (messageAreaHeight - textHeight) / 2

        love.graphics.setColor(0.6, 0.6, 0.6, 1)
        love.graphics.setFont(self.font)
        love.graphics.print(msg, centerX, centerY)
    else
        local maxBubbleWidth = messageAreaWidth * self.maxBubbleWidth

        local currentY = messageAreaY + messageAreaHeight - 10

        local totalMessages = #self.messages
        local startIndex = math.max(1, totalMessages - self.scrollOffset - self:getVisibleMessageCount() + 1)
        local endIndex = totalMessages - self.scrollOffset

        local messagesToDraw = {}
        local totalHeight = 0

        for i = endIndex, startIndex, -1 do
            local message = self.messages[i]
            local wrappedText = self:wrapText(message.content, maxBubbleWidth - self.bubblePadding * 2)
            local textHeight = #wrappedText * self.font:getHeight()
            local bubbleHeight = textHeight + self.bubblePadding * 2

            table.insert(messagesToDraw, 1, {
                message = message,
                height = bubbleHeight,
                wrappedText = wrappedText
            })

            totalHeight = totalHeight + bubbleHeight + self.bubbleMargin
        end

        currentY = messageAreaY + messageAreaHeight - 10

        for i = #messagesToDraw, 1, -1 do
            local msgData = messagesToDraw[i]
            currentY = currentY - msgData.height - self.bubbleMargin

            if currentY < messageAreaY then
                break
            end

            self:drawMessageBubbleAtPosition(msgData.message, messageAreaX, currentY, messageAreaWidth, maxBubbleWidth, msgData.wrappedText, msgData.height)
        end
    end

    love.graphics.setScissor()
end

function Chat:drawMessageBubbleAtPosition(message, areaX, bubbleY, areaWidth, maxBubbleWidth, wrappedText, bubbleHeight)
    local isFromUser = message.sender == "You"
    local bubbleColor = self.bubbleColors[message.sender] or {0.3, 0.3, 0.3, 1}
    local textColor = self.textColors[message.sender] or {1, 1, 1, 1}

    -- Find the widest line to determine bubble width
    local maxLineWidth = 0
    for _, line in ipairs(wrappedText) do
        local lineWidth = self.font:getWidth(line)
        if lineWidth > maxLineWidth then
            maxLineWidth = lineWidth
        end
    end

    local bubbleWidth = math.min(maxLineWidth + self.bubblePadding * 2, maxBubbleWidth)

    -- Position bubble (right for user, left for others)
    local bubbleX
    if isFromUser then
        bubbleX = areaX + areaWidth - bubbleWidth - self.bubbleMargin
    else
        bubbleX = areaX + self.bubbleMargin
    end

    -- Draw bubble
    love.graphics.setColor(bubbleColor)
    love.graphics.rectangle("fill", bubbleX, bubbleY, bubbleWidth, bubbleHeight, 8, 8)

    -- Draw text
    love.graphics.setColor(textColor)
    local textY = bubbleY + self.bubblePadding
    for _, line in ipairs(wrappedText) do
        local textX
        if isFromUser then
            -- Right align text for user
            local lineWidth = self.font:getWidth(line)
            textX = bubbleX + bubbleWidth - lineWidth - self.bubblePadding
        else
            -- Left align text for others
            textX = bubbleX + self.bubblePadding
        end

        love.graphics.setFont(self.font)
        love.graphics.print(line, textX, textY)
        textY = textY + self.font:getHeight()
    end

end

function Chat:drawMessageBubble(message, areaX, startY, areaWidth, maxBubbleWidth)
    local isFromUser = message.sender == "You"
    local bubbleColor = self.bubbleColors[message.sender] or {0.3, 0.3, 0.3, 1}
    local textColor = self.textColors[message.sender] or {1, 1, 1, 1}

    -- Wrap text to fit bubble width
    local wrappedText = self:wrapText(message.content, maxBubbleWidth - self.bubblePadding * 2)

    -- Calculate bubble dimensions
    local textHeight = #wrappedText * self.font:getHeight()
    local bubbleHeight = textHeight + self.bubblePadding * 2

    -- Find the widest line to determine bubble width
    local maxLineWidth = 0
    for _, line in ipairs(wrappedText) do
        local lineWidth = self.font:getWidth(line)
        if lineWidth > maxLineWidth then
            maxLineWidth = lineWidth
        end
    end

    local bubbleWidth = math.min(maxLineWidth + self.bubblePadding * 2, maxBubbleWidth)

    -- Position bubble (right for user, left for others)
    local bubbleX
    if isFromUser then
        bubbleX = areaX + areaWidth - bubbleWidth - self.bubbleMargin
    else
        bubbleX = areaX + self.bubbleMargin
    end

    local bubbleY = startY

    -- Draw bubble
    love.graphics.setColor(bubbleColor)
    love.graphics.rectangle("fill", bubbleX, bubbleY, bubbleWidth, bubbleHeight, 8, 8)
    
    -- Draw bubble tail (WhatsApp-style pointer)
    if isFromUser then
        -- Right tail for user messages
        local tailPoints = {
            bubbleX + bubbleWidth, bubbleY + bubbleHeight - 10,
            bubbleX + bubbleWidth + 8, bubbleY + bubbleHeight - 5,
            bubbleX + bubbleWidth, bubbleY + bubbleHeight - 2
        }
        love.graphics.polygon("fill", tailPoints)
    else
        -- Left tail for other messages
        local tailPoints = {
            bubbleX, bubbleY + bubbleHeight - 10,
            bubbleX - 8, bubbleY + bubbleHeight - 5,
            bubbleX, bubbleY + bubbleHeight - 2
        }
        love.graphics.polygon("fill", tailPoints)
    end
    
    -- Draw text
    love.graphics.setColor(textColor)
    local textY = bubbleY + self.bubblePadding
    for _, line in ipairs(wrappedText) do
        local textX
        if isFromUser then
            -- Right align text in user bubbles
            local lineWidth = self.font:getWidth(line)
            textX = bubbleX + bubbleWidth - lineWidth - self.bubblePadding
        else
            -- Left align text in other bubbles
            textX = bubbleX + self.bubblePadding
        end

        love.graphics.setFont(self.font)
        love.graphics.print(line, textX, textY)
        textY = textY + self.font:getHeight()
    end


    -- Return next Y position
    return startY + bubbleHeight + self.bubbleMargin
end

function Chat:wrapText(text, maxWidth)
    local words = {}
    for word in text:gmatch("%S+") do
        table.insert(words, word)
    end

    local lines = {}
    local currentLine = ""

    for _, word in ipairs(words) do
        local testLine = currentLine == "" and word or currentLine .. " " .. word
        if self.font:getWidth(testLine) > maxWidth then
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
        if self.newChat then
            self.newChat = false

            local totalChats = #self.db:GetAllKeys() + 1
            self.chatName = "chat" .. totalChats
            self.db:Create(self.chatName, "")
            self.messages = {}
        end

        self:addMessage("You", message)
        networkManager:sendMessage(message)

        self.queryInput.text = ""
        self.queryInput.cursorPos = 0
    end
end

function Chat:draw(height, width, sideBarWidth)
    -- Background
    love.graphics.setColor(46/255, 41/255, 78/255)
    love.graphics.rectangle("fill", sideBarWidth, height * 0.08, width - sideBarWidth, height * 0.92)

    self:drawMessages(width, height, sideBarWidth)

    -- Draw input area
    local inputWidth = self.queryInput.width
    local inputHeight = self.queryInput.height
    self.queryInput.x = sideBarWidth + (width - sideBarWidth - inputWidth) / 2
    self.queryInput.y = height - inputHeight - 15
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

    if #networkManager.pendingMessages > 0 then
        love.graphics.setColor(1, 1, 0, 1) -- Yellow
        love.graphics.print("Pending: " .. #networkManager.pendingMessages, width - 100, 30)
    end
end

function Chat:scroll(amount)
    local visibleCount = self:getVisibleMessageCount()
    local maxOffset = math.max(0, #self.messages - visibleCount)
    
    -- For bottom-up display: 0 = newest messages, higher = older messages
    self.scrollOffset = math.min(math.max(self.scrollOffset + amount, 0), maxOffset)
end
