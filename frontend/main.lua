local loveFrames = require("LoveFrames/loveframes")
local width = love.graphics.getWidth()
local height = love.graphics.getHeight()

local sideBarWidth = width * 0.25

local font

local function updateFont()
    local h = love.graphics.getHeight()
    local size = math.floor(h * 0.05)
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

    love.graphics.setColor(18/255, 17/255, 51/255)
    love.graphics.rectangle("fill", 0, 0, width, height * 0.08)
    love.graphics.rectangle("fill", 0, 0, sideBarWidth, height)

    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.print("CHAT", 20, 10)

    love.graphics.setColor(46/255, 41/255, 78/255)
    love.graphics.rectangle("fill", width * 0.25, height * 0.08, width * 0.75, height * 0.92)
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
    local desireSideBarWidth = w * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desireSideBarWidth, maxSideBarWidth)
end
