local loveFrames = require("LoveFrames/loveframes")
local width = love.graphics.getWidth()
local height = love.graphics.getHeight()

local sideBarWidth
local font

local function updateFont()
    local h = love.graphics.getHeight()
    local size = math.floor(h * 0.03)
    font = love.graphics.newFont(size)
    love.graphics.setFont(font)
end

function love.load()
    love.window.setMode(800, 600, {
        resizable = true,
        minwidth = 400,
        minheight = 300
    })

    textinput = loveFrames.Create("textinput")
    textinput:SetPos( width * 0.3, height - 50)
    textinput:SetWidth(200)
    textinput:SetText("Write Here..")

    font = love.graphics.newFont(24)
    love.graphics.setFont(font)
end

function love.update(dt)
    loveFrames.update(dt)
end

function love.draw()
    width = love.graphics.getWidth()
    height = love.graphics.getHeight()

    updateFont()

    local desiredSideBarWidth = width * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desiredSideBarWidth, maxSideBarWidth)

    love.graphics.setColor(18/255, 17/255, 51/255)
    --Top bar
    love.graphics.rectangle("fill", 0, 0, width, height * 0.08)

    --Side bar
    love.graphics.rectangle("fill", 0, height * 0.08, sideBarWidth, height)

    --Bars border
    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 0, 0, width, height * 0.08)
    love.graphics.rectangle("line", 0, height * 0.08, sideBarWidth, height - height*0.08)
    love.graphics.print("ChispitasGPT", 20, height * 0.021)

    love.graphics.setColor(46/255, 41/255, 78/255)
    --Chat content
    love.graphics.rectangle("fill", sideBarWidth, height * 0.08, width - sideBarWidth, height * 0.92)
    loveFrames.draw()
end

function love.mousepressed(x, y, button)
    loveFrames.mousepressed(x, y, button)
end

function love.mousereleased(x, y, button)
    loveFrames.mousereleased(x, y, button)
end

function love.keypressed(key, unicode)
    loveFrames.keypressed(key, unicode)
end

function love.keyreleased(key)
    loveFrames.keyreleased(key)
end

function love.textinput(text)
    loveFrames.textinput(text)
end

function love.resize(w, h)
    updateFont()
end
