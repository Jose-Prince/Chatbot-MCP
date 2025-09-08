TextInput = Object:extend()

function TextInput:new(x, y, width, height)
    self.x = x
    self.y = y
    self.width = width
    self.height = height
    self.text = ""
    self.hasFocus = false
    self.cursorPos = 0
    self.blinkTimer = 0
    self.blinkState = true
end

function TextInput:update(dt)
    if self.hasFocus then
        self.blinkTimer = self.blinkTimer + dt
        if self.blinkTimer >= 0.5 then
            self.blinkState = not self.blinkState
            self.blinkTimer = 0
        end
    else
        self.blinkState = false
    end
end

function TextInput:draw()
    -- Fondo negro
    love.graphics.setColor(0, 0, 0, 1)
    love.graphics.rectangle("fill", self.x, self.y, self.width, self.height)

    -- Borde blanco
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", self.x, self.y, self.width, self.height)

    -- Texto blanco
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.print(self.text, self.x + 5, self.y + 5)

    -- Cursor
    if self.hasFocus and self.blinkState then
        local font = love.graphics.getFont()
        local cursorX = self.x + 5 + font:getWidth(self.text:sub(1, self.cursorPos))
        love.graphics.line(cursorX, self.y + 3, cursorX, self.y + self.height - 3)
    end
end

function TextInput:textinput(t)
    if self.hasFocus then
        self.text = self.text:sub(1, self.cursorPos) .. t .. self.text:sub(self.cursorPos + 1)
        self.cursorPos = self.cursorPos + #t
    end
end

function TextInput:keypressed(key)
    if not self.hasFocus then return end
    if key == "backspace" then
        if self.cursorPos > 0 then
            self.text = self.text:sub(1, self.cursorPos - 1) .. self.text:sub(self.cursorPos + 1)
            self.cursorPos = self.cursorPos - 1
        end
    elseif key == "left" then
        if self.cursorPos > 0 then self.cursorPos = self.cursorPos - 1 end
    elseif key == "right" then
        if self.cursorPos < #self.text then self.cursorPos = self.cursorPos + 1 end
    end
end

function TextInput:mousepressed(mx, my, button)
    if button == 1 then
        self.hasFocus = mx >= self.x and mx <= self.x + self.width and
                        my >= self.y and my <= self.y + self.height
    end
end
