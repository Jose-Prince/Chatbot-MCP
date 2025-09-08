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
end

function Chat:draw(type, height, width, sideBarWidth)
    --Background
    love.graphics.setColor(46/255, 41/255, 78/255)
    love.graphics.rectangle("fill", sideBarWidth, height * 0.08, width - sideBarWidth, height * 0.92)

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

    if type then
    else
        print("Bye")
    end
end

function Chat:sendMessage(message)
    if client then
        local ok, err = client:send(message .. "\n")
        if not ok then
            print("Error enviando mensaje:", err)
        end
    end
end

