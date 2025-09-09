Object = require "classic"

loveFrames = require("LoveFrames.loveframes")
socket = require("socket")

require "components.button"
require "components.chat"
require "components.sidebar"
require "networkManager"
require "database"

function string:trim()
    return self:match("^%s*(.-)%s*$")
end

networkManager = NetworkManager()

local width = love.graphics.getWidth()
local height = love.graphics.getHeight()

local sideBarWidth
local font
local sidebar

local function updateFont()
    local h = love.graphics.getHeight()
    local size = math.floor(h * 0.03)
    font = love.graphics.newFont(size)
    love.graphics.setFont(font)
end

function love.load()

    networkManager:connect()

    love.window.setMode(800, 600, {
        resizable = true,
        minwidth = 400,
        minheight = 300
    })

    local desiredSideBarWidth = width * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desiredSideBarWidth, maxSideBarWidth)

    font = love.graphics.newFont(24)

    local db = Database()
    chat = Chat(width, height, sideBarWidth, db, font)
    sidebar = Sidebar(chat, db)

    love.graphics.setFont(font)
end

function love.update(dt)
    loveFrames.update(dt)
    networkManager:update(dt)

    chat.queryInput:update(dt)
    sidebar.createChatButton:update(dt)

    width = love.graphics.getWidth()
    height = love.graphics.getHeight()

    local desiredSideBarWidth = width * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desiredSideBarWidth, maxSideBarWidth)

    sidebar.createChatButton:SetSize(sideBarWidth - 20, 40)
    sidebar.createChatButton:SetPosition(10, height * 0.08 + 10)
    sidebar.createChatButton:update(dt)
end

function love.draw()
    updateFont()

    love.graphics.setColor(18/255, 17/255, 51/255)
    love.graphics.rectangle("fill", 0, 0, width, height * 0.08)

    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 0, 0, width, height * 0.08)
    love.graphics.print("ChispitasGPT", 20, height * 0.021)

    sidebar:draw(width, height, sideBarWidth)
    chat:draw(height, width, sideBarWidth)

    loveFrames.draw()
end

function love.textinput(t)
    chat.queryInput:textinput(t)
end

function love.mousepressed(x, y, button)
    local handled = sidebar.createChatButton:mousepressed(x, y, button)
    for _, btn in ipairs(sidebar.chatButtons) do
        if btn:mousepressed(x, y, button) then
            handled = true
        end
    end

    if not handled then
        loveFrames.mousepressed(x, y, button)
    end

    chat.queryInput:mousepressed(x, y, button)
    chat.sendButton:mousepressed(x, y, button)
end

function love.mousereleased(x, y, button)
    sidebar.createChatButton:mousereleased(x, y, button)
    for _, btn in ipairs(sidebar.chatButtons) do
        btn:mousereleased(x, y, button)
    end

    chat.sendButton:mousereleased(x, y, button)
    loveFrames.mousereleased(x, y, button)
end

function love.keypressed(key, unicode)
    loveFrames.keypressed(key, unicode)
    chat.queryInput:keypressed(key)

    if key == "return" and chat.queryInput.hasFocus then
        chat.sendButton:onClick()
    end
end


function love.keyreleased(key)
    loveFrames.keyreleased(key)
end

function love.wheelmoved(x, y)
    print("moving scroll")
end


function love.resize(w, h)
    updateFont()
end

function love.quit()
    networkManager:close()
end
