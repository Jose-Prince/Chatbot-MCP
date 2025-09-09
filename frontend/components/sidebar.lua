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

function Sidebar:draw(width, height, sideBarWidth)
    love.graphics.setColor(18/255, 17/255, 51/255)
    love.graphics.rectangle("fill", 0, height * 0.08, sideBarWidth, height)

    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 0, height * 0.08, sideBarWidth, height - height*0.08)


    self.createChatButton:draw()

    love.graphics.line(0, 120, width, 120)

    local keys = self.db:GetAllKeys()
    local y = 140
    for _, key in ipairs(keys) do
        local chatButton = Button(0, y, 200, 40, key, function ()
            self.selectedChat = key
            self.chat.chatName = key
            self.chat.newChat = false
            self.chat.messages = self.db:Read(key) or {}
        end)
        table.insert(self.chatButtons, chatButton)
        chatButton:draw()
        y = y + 40
    end
end
