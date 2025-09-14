TextInput = Object:extend()

function TextInput:new(x, y, width, height)
    self.x = x
    self.y = y
    self.width = width
    self.height = height
    self.font = love.graphics.newFont(22)
    self.text = ""
    self.hasFocus = false
    self.cursorPos = 0
    self.blinkTimer = 0
    self.blinkState = true
    self.lineHeight = self.font:getHeight()
    self.padding = 5
    self.scrollOffset = 0
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
    -- Background
    love.graphics.setColor(18/255, 17/255, 51/255, 1)
    love.graphics.rectangle("fill", self.x, self.y, self.width, self.height)

    -- Border
    love.graphics.setColor(197/255, 216/255, 109/255, 1)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", self.x, self.y, self.width, self.height)

    -- Set scissor to prevent text from overflowing
    love.graphics.setScissor(self.x + self.padding, self.y + self.padding, self.width - 2 * self.padding, self.height - 2 * self.padding)

    -- Set the font to be drawn
    love.graphics.setFont(self.font)

    -- Draw text
    love.graphics.setColor(197/255, 216/255, 109/255, 1)
    love.graphics.print(self.text, self.x + self.padding, self.y + self.padding)

    -- Draw cursor
    if self.hasFocus and self.blinkState then
        local cursorX = self.x + self.padding + self.font:getWidth(self.text:sub(1, self.cursorPos))
        local cursorY = self.y + self.padding
        love.graphics.line(cursorX, cursorY, cursorX, cursorY + self.lineHeight)
    end

    love.graphics.setScissor()
end

function TextInput:textinput(t)
    if not self.hasFocus then return end

    -- Allow adding text regardless of width
    self.text = self.text:sub(1, self.cursorPos) .. t .. self.text:sub(self.cursorPos + 1)
    self.cursorPos = self.cursorPos + #t
end

function TextInput:keypressed(key)
    if not self.hasFocus then return end

    if key == "backspace" then
        if self.cursorPos > 0 then
            self.text = self.text:sub(1, self.cursorPos - 1) .. self.text:sub(self.cursorPos + 1)
            self.cursorPos = self.cursorPos - 1
        end
    elseif key == "delete" then
        if self.cursorPos < #self.text then
            self.text = self.text:sub(1, self.cursorPos) .. self.text:sub(self.cursorPos + 2)
        end
    elseif key == "left" then
        self.cursorPos = math.max(0, self.cursorPos - 1)
    elseif key == "right" then
        self.cursorPos = math.min(#self.text, self.cursorPos + 1)
    elseif key == "home" then
        self.cursorPos = 0
    elseif key == "end" then
        self.cursorPos = #self.text
    end
end

function TextInput:mousepressed(mx, my, button)
    if button == 1 then
        self.hasFocus = mx >= self.x and mx <= self.x + self.width and
                        my >= self.y and my <= self.y + self.height

        if self.hasFocus then
            local clickX = mx - self.x - self.padding
            local bestPos = 0
            local bestDistance = math.huge

            for i = 0, #self.text do
                local charX = self.font:getWidth(self.text:sub(1, i))
                local distance = math.abs(charX - clickX)
                if distance < bestDistance then
                    bestDistance = distance
                    bestPos = i
                end
            end

            self.cursorPos = bestPos
        end
    end
end
