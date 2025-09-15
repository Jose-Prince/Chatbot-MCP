Button = Object:extend()

function Button:new(x, y, width, height, text, onClick)
    self.x = x or 0
    self.y = y or 0
    self.width = width or 100
    self.height = height or 30
    self.text = text or "Button"
    self.onClick = onClick or function() end

    self.normalColor = {18/255, 17/255, 51/255, 1}
    self.hoverColor = {22/255, 21/255, 61/255, 1}
    self.pressedColor = {14/255, 13/255, 41/255, 1}
    self.textColor = {1, 1, 1, 1}
    self.borderColor = {197/255, 216/255, 109/255, 1}
    self.borderWidth = 2

    self.isHovered = false
    self.isPressed = false
    self.isEnabled = true

    self.cornerRadius = 4
end

function Button:SetPosition(x, y)
    self.x = x
    self.y = y
end

function Button:SetSize(width, height)
    self.width = width
    self.height = height
end

function Button:setText(text)
    self.text = text
end

function Button:setColors(normal, hover, pressed, text)
    if normal then self.normalColor = normal end
    if hover then self.hoverColor = hover end
    if pressed then self.pressedColor = pressed end
    if text then self.textColor = text end
end

function Button:isMouseOver(mx, my)
    return mx >= self.x and mx <= self.x + self.width and
           my >= self.y and my <= self.y + self.height
end

function Button:update(dt)
    if not self.isEnabled then
        self.isHovered = false
        return
    end

    local mx, my = love.mouse.getPosition()
    self.isHovered = self:isMouseOver(mx, my)
end

function Button:draw()
    if not self.isEnabled then
        love.graphics.setColor(0.5, 0.5, 0.5, 0.7)
    elseif self.isPressed and self.isHovered then
        love.graphics.setColor(self.pressedColor)
    elseif self.isHovered then
        love.graphics.setColor(self.hoverColor)
    else
        love.graphics.setColor(self.normalColor)
    end

    if self.cornerRadius > 0 then
        love.graphics.rectangle("fill", self.x, self.y, self.width, self.height, self.cornerRadius)
    else
        love.graphics.rectangle("fill", self.x, self.y, self.width, self.height)
    end

    if self.borderWidth > 0 then
        love.graphics.setColor(self.borderColor)
        love.graphics.setLineWidth(self.borderWidth)
        if self.cornerRadius > 0 then
            love.graphics.rectangle("line", self.x, self.y, self.width, self.height, self.cornerRadius)
        else
            love.graphics.rectangle("line", self.x, self.y, self.width, self.height)
        end
    end

    love.graphics.setColor(self.textColor)
    local font = love.graphics.getFont()
    local textWidth = font:getWidth(self.text)
    local textHeight = font:getHeight()

    local textX = self.x + (self.width - textWidth) / 2
    local textY = self.y + (self.height - textHeight) / 2

    love.graphics.print(self.text, textX, textY)
end

function Button:mousepressed(x, y, button)
    if not self.isEnabled then return false end

    if button == 1 and self:isMouseOver(x, y) then
        self.isPressed = true
        return true 
    end
    return false
end

function Button:mousereleased(x, y, button)
    if not self.isEnabled then return false end

    if button == 1 and self.isPressed then
        self.isPressed = false
        if self:isMouseOver(x, y) then
            self.onClick(self)
            return true
        end
    end
    return false
end

function Button:setEnabled(enabled)
    self.isEnabled = enabled
    if not enabled then
        self.isHovered = false
        self.isPressed = false
    end
end
