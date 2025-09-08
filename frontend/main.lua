Object = require "classic"

loveFrames = require("LoveFrames.loveframes")
socket = require("socket")

require "components.button"
require "components.chat"
require "networkManager"

function string:trim()
    return self:match("^%s*(.-)%s*$")
end

-- Improved JSON parsing
json = {}
function json.decode(str)
    if not str or str == "" then
        return nil
    end
    
    -- Remove whitespace
    str = str:trim()
    
    -- Basic JSON object parser
    if str:match("^%s*{.*}%s*$") then
        local result = {}
        
        -- Try to extract status
        local status = str:match('"status"%s*:%s*"([^"]*)"')
        if status then
            result.status = status
        end
        
        -- Try to extract data - handle both string and object data
        local data = str:match('"data"%s*:%s*"([^"]*)"')
        if not data then
            -- Try to extract data as object or array
            local dataStart = str:find('"data"%s*:%s*')
            if dataStart then
                local afterColon = str:find(":", dataStart)
                if afterColon then
                    local remaining = str:sub(afterColon + 1)
                    -- Simple extraction - find the value until next comma or end
                    local dataValue = remaining:match('^%s*"([^"]*)"') or 
                                    remaining:match('^%s*([^,}]*)')
                    if dataValue then
                        data = dataValue:trim()
                    end
                end
            end
        end
        if data then
            result.data = data
        end
        
        -- Try to extract error
        local error = str:match('"error"%s*:%s*"([^"]*)"')
        if error then
            result.error = error
        end
        
        -- Try to extract timestamp
        local timestamp = str:match('"timestamp"%s*:%s*([%d%.]+)')
        if timestamp then
            result.timestamp = tonumber(timestamp)
        end
        
        return result
    end
    
    return nil
end

-- Alternative: use loadstring for JSON parsing (more robust but potentially unsafe)
function json.decode_safe(str)
    if not str or str == "" then
        return nil
    end
    
    -- Replace JSON syntax with Lua syntax
    local luaStr = str:gsub('null', 'nil')
                     :gsub('true', 'true')
                     :gsub('false', 'false')
                     :gsub('"([^"]*)":', '["%1"]=')
    
    -- Try to load as Lua code
    local func, err = loadstring("return " .. luaStr)
    if func then
        local success, result = pcall(func)
        if success then
            return result
        end
    end
    
    return nil
end

networkManager = NetworkManager()

local width = love.graphics.getWidth()
local height = love.graphics.getHeight()

local chat
local createChatButton
local sideBarWidth
local font
local newChat = true

local function updateFont()
    local h = love.graphics.getHeight()
    local size = math.floor(h * 0.03)
    font = love.graphics.newFont(size)
    love.graphics.setFont(font)
end

function love.load()
    print("Starting application...")
    networkManager:connect()

    love.window.setMode(800, 600, {
        resizable = true,
        minwidth = 400,
        minheight = 300
    })

    local desiredSideBarWidth = width * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desiredSideBarWidth, maxSideBarWidth)

    createChatButton = Button(10, 100, 200, 40, "New Chat", function()
        print("New chat clicked")
        newChat = not newChat
        if newChat then
            chat.messages = {}
            print("Chat messages cleared")
        end
    end)

    chat = Chat(width, height, sideBarWidth)

    font = love.graphics.newFont(24)
    love.graphics.setFont(font)
    
    print("Application loaded successfully")
end

function love.update(dt)
    loveFrames.update(dt)
    networkManager:update(dt)

    chat.queryInput:update(dt)

    width = love.graphics.getWidth()
    height = love.graphics.getHeight()

    local desiredSideBarWidth = width * 0.25
    local maxSideBarWidth = 300
    sideBarWidth = math.min(desiredSideBarWidth, maxSideBarWidth)

    createChatButton:SetSize(sideBarWidth - 20, 40)
    createChatButton:SetPosition(10, height * 0.08 + 10)
    createChatButton:update(dt)
end

function love.draw()
    updateFont()

    love.graphics.setColor(18/255, 17/255, 51/255)
    love.graphics.rectangle("fill", 0, 0, width, height * 0.08)
    love.graphics.rectangle("fill", 0, height * 0.08, sideBarWidth, height)

    love.graphics.setColor(197/255, 216/255, 109/255)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 0, 0, width, height * 0.08)
    love.graphics.rectangle("line", 0, height * 0.08, sideBarWidth, height - height*0.08)
    love.graphics.print("ChispitasGPT", 20, height * 0.021)

    createChatButton:draw()
    chat:draw(newChat, height, width, sideBarWidth)

    -- Debug info
    love.graphics.setColor(1, 1, 1, 0.7)
    love.graphics.print("Messages: " .. #chat.messages, 10, height - 40)
    love.graphics.print("Connected: " .. (networkManager.isConnected and "YES" or "NO"), 10, height - 20)

    loveFrames.draw()
end

function love.textinput(t)
    chat.queryInput:textinput(t)
end

function love.mousepressed(x, y, button)
    local buttonHandled = createChatButton:mousepressed(x, y, button)

    if not buttonHandled then
        loveFrames.mousepressed(x, y, button)
    end

    chat.queryInput:mousepressed(x, y, button)
    chat.sendButton:mousepressed(x, y, button)
end

function love.mousereleased(x, y, button)
    local buttonHandled = createChatButton:mousereleased(x, y, button)

    chat.sendButton:mousereleased(x, y, button)

    if not buttonHandled then
        loveFrames.mousereleased(x, y, button)
    end
end

function love.keypressed(key, unicode)
    loveFrames.keypressed(key, unicode)
    chat.queryInput:keypressed(key)

    if key == "return" and chat.queryInput.hasFocus then
        local message = chat.queryInput.text
        if message ~= "" then
            print("Sending message:", message)
            chat:sendMessage(message)
            chat.queryInput.text = ""
            chat.queryInput.cursorPos = 0
        end
    end
end

function love.keyreleased(key)
    loveFrames.keyreleased(key)
end

function love.resize(w, h)
    updateFont()
end

function love.quit()
    print("Closing application...")
    networkManager:close()
end
