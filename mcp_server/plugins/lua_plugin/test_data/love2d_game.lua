-- Love2D Game Example
-- Demonstrates Love2D-specific patterns and callbacks

local Player = {}
Player.__index = Player

-- Constants for game
local SCREEN_WIDTH = 800
local SCREEN_HEIGHT = 600
local PLAYER_SPEED = 200
local ENEMY_SPEED = 100

-- Game state
local player
local enemies = {}
local score = 0
local gameState = "menu"

-- Create player object
function Player.new(x, y)
    local self = setmetatable({}, Player)
    self.x = x
    self.y = y
    self.width = 32
    self.height = 32
    self.speed = PLAYER_SPEED
    self.health = 100
    self.sprite = love.graphics.newImage("player.png")
    return self
end

function Player:update(dt)
    -- Handle input
    if love.keyboard.isDown("left") then
        self.x = self.x - self.speed * dt
    elseif love.keyboard.isDown("right") then
        self.x = self.x + self.speed * dt
    end
    
    if love.keyboard.isDown("up") then
        self.y = self.y - self.speed * dt
    elseif love.keyboard.isDown("down") then
        self.y = self.y + self.speed * dt
    end
    
    -- Keep player on screen
    self.x = math.max(0, math.min(self.x, SCREEN_WIDTH - self.width))
    self.y = math.max(0, math.min(self.y, SCREEN_HEIGHT - self.height))
end

function Player:draw()
    love.graphics.draw(self.sprite, self.x, self.y)
    -- Draw health bar
    love.graphics.setColor(1, 0, 0)
    love.graphics.rectangle("fill", self.x, self.y - 10, self.width * (self.health / 100), 5)
    love.graphics.setColor(1, 1, 1)
end

-- Enemy class
local Enemy = {}
Enemy.__index = Enemy

function Enemy.new(x, y)
    local self = setmetatable({}, Enemy)
    self.x = x
    self.y = y
    self.width = 24
    self.height = 24
    self.speed = ENEMY_SPEED
    self.color = {math.random(), math.random(), math.random()}
    return self
end

function Enemy:update(dt, target)
    -- Move towards player
    local dx = target.x - self.x
    local dy = target.y - self.y
    local dist = math.sqrt(dx^2 + dy^2)
    
    if dist > 0 then
        self.x = self.x + (dx / dist) * self.speed * dt
        self.y = self.y + (dy / dist) * self.speed * dt
    end
end

function Enemy:draw()
    love.graphics.setColor(self.color)
    love.graphics.rectangle("fill", self.x, self.y, self.width, self.height)
    love.graphics.setColor(1, 1, 1)
end

-- Love2D callbacks
function love.load()
    love.window.setTitle("Lua Game Example")
    love.window.setMode(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    -- Initialize game objects
    player = Player.new(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    
    -- Create initial enemies
    for i = 1, 5 do
        table.insert(enemies, Enemy.new(
            math.random(0, SCREEN_WIDTH),
            math.random(0, SCREEN_HEIGHT)
        ))
    end
    
    -- Load fonts
    font = love.graphics.newFont(18)
    love.graphics.setFont(font)
end

function love.update(dt)
    if gameState == "playing" then
        -- Update player
        player:update(dt)
        
        -- Update enemies
        for i, enemy in ipairs(enemies) do
            enemy:update(dt, player)
            
            -- Check collision with player
            if checkCollision(player, enemy) then
                player.health = player.health - 10
                table.remove(enemies, i)
                
                if player.health <= 0 then
                    gameState = "gameover"
                end
            end
        end
        
        -- Spawn new enemies occasionally
        if math.random() < 0.01 then
            table.insert(enemies, Enemy.new(
                math.random(0, SCREEN_WIDTH),
                math.random(0, SCREEN_HEIGHT)
            ))
        end
        
        -- Update score
        score = score + dt * 10
    end
end

function love.draw()
    if gameState == "menu" then
        love.graphics.print("Press SPACE to start", SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2)
    elseif gameState == "playing" then
        -- Draw game objects
        player:draw()
        
        for _, enemy in ipairs(enemies) do
            enemy:draw()
        end
        
        -- Draw UI
        love.graphics.print("Score: " .. math.floor(score), 10, 10)
        love.graphics.print("Health: " .. player.health, 10, 30)
        love.graphics.print("Enemies: " .. #enemies, 10, 50)
    elseif gameState == "gameover" then
        love.graphics.print("Game Over!", SCREEN_WIDTH/2 - 50, SCREEN_HEIGHT/2 - 20)
        love.graphics.print("Final Score: " .. math.floor(score), SCREEN_WIDTH/2 - 70, SCREEN_HEIGHT/2)
        love.graphics.print("Press R to restart", SCREEN_WIDTH/2 - 80, SCREEN_HEIGHT/2 + 20)
    end
end

function love.keypressed(key, scancode, isrepeat)
    if key == "space" and gameState == "menu" then
        gameState = "playing"
    elseif key == "r" and gameState == "gameover" then
        -- Reset game
        player.health = 100
        player.x = SCREEN_WIDTH / 2
        player.y = SCREEN_HEIGHT / 2
        enemies = {}
        score = 0
        gameState = "playing"
    elseif key == "escape" then
        love.event.quit()
    end
end

function love.mousepressed(x, y, button, istouch, presses)
    if button == 1 then  -- Left click
        -- Create explosion effect at click position
        createExplosion(x, y)
    end
end

-- Helper functions
function checkCollision(a, b)
    return a.x < b.x + b.width and
           a.x + a.width > b.x and
           a.y < b.y + b.height and
           a.y + a.height > b.y
end

function createExplosion(x, y)
    -- Remove nearby enemies
    for i = #enemies, 1, -1 do
        local enemy = enemies[i]
        local dist = math.sqrt((enemy.x - x)^2 + (enemy.y - y)^2)
        if dist < 50 then
            table.remove(enemies, i)
            score = score + 100
        end
    end
end

-- Additional Love2D callbacks
function love.quit()
    print("Thanks for playing!")
    return false
end

function love.focus(focused)
    if not focused and gameState == "playing" then
        gameState = "paused"
    end
end