local loveFrames = require("LoveFrames/loveframes")
local width = love.graphics.getWidth()
local height = love.graphics.getHeight()

function love.load()
    local frame = loveFrames.Create("frame")
    frame:SetName("Example")
    frame:SetSize(width, height)
    frame:ShowCloseButton(false)
    frame:CenterWithinArea(0, 0, love.graphics.getWidth(), love.graphics.getHeight())

    local button = loveFrames.Create("button", frame)
    button:SetText("Press me")
    button:SetPos(50, 50)
end

function love.update(dt)
    loveFrames.update(dt)
end

function love.draw()
    loveFrames.draw()
end

function love.mousepressed(x, y, button)
    loveFrames.mousepressed(x, y, button)
end
