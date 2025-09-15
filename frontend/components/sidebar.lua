Sidebar = Object:extend()

function Sidebar:new(chat, db)
    self.chat = chat
    self.db = db
    self.selectedChat = nil
    self.chatButtons = {}

    self.createChatButton = Button(10, 100, 200, 40, "New Chat", function()
        if chat.newChat == false then
            chat.newChat = true
            chat.messages = {}
            self.selectedChat = nil
        end
    end)
end

function Sidebar:update(dt)
    self.createChatButton:update(dt)
    for _, btn in ipairs(self.chatButtons) do
        btn:update(dt)
    end
end

function Sidebar:draw(width, height, sideBarWidth)
    self.deleteButtons = {}

    love.graphics.setColor(18/255, 17/255, 51/255)
    love.graphics.rectangle("fill", 0, height * 0.08, sideBarWidth, height)

    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 0, height * 0.08, sideBarWidth, height - height*0.08)

    local buttonHeight = height * 0.06
    local buttonY = height * 0.1

    self.createChatButton:draw()

    local lineY = buttonY + buttonHeight + height * 0.02
    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.line(0, lineY, sideBarWidth, lineY)

    local keys = self.db:GetAllKeys()
    local y = lineY + height * 0.02
    local chatButtonHeight = height * 0.05

    local mx, my = love.mouse.getPosition()

    for _, key in ipairs(keys) do
        local chatButton = Button(1, y, sideBarWidth - 2, chatButtonHeight, key, function ()
            self.selectedChat = key
            self.chat.chatName = key
            self.chat.newChat = false
            self.chat.messages = self.db:Read(key) or {}
        end)

        table.insert(self.chatButtons, chatButton)
        chatButton:draw()

        local radius = chatButtonHeight * 0.4
        local cx = sideBarWidth - 25
        local cy = y + chatButtonHeight / 2

        local dx, dy = mx - cx, my - cy
        local dist = math.sqrt(dx * dx + dy * dy)

        if dist <= radius then
            love.graphics.setColor(1, 0, 0, 1) -- rojo brillante en hover
        else
            love.graphics.setColor(0.2, 0.2, 0.2, 1) -- gris cuando no hay hover
        end
        love.graphics.circle("fill", cx, cy, radius)

        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.setLineWidth(2)
        love.graphics.line(cx - 5, cy - 5, cx + 5, cy + 5)
        love.graphics.line(cx + 5, cy - 5, cx - 5, cy + 5)

        table.insert(self.deleteButtons, {x = cx, y = cy, r = radius, chatKey = key})

        y = y + chatButtonHeight + height * 0.015
    end
end

function Sidebar:mousepressed(x, y, button)
    if button == 1 then
        for _, btn in ipairs(self.deleteButtons or {}) do
            local dx, dy = x - btn.x, y - btn.y
            if math.sqrt(dx * dx + dy * dy) <= btn.r then
                print("Eliminar chat:", btn.chatKey)
                self.db:Delete(btn.chatKey)
                self.selectedChat = nil
                self.chat.messages = {}
            end
        end
    end
end
