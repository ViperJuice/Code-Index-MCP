-- OpenResty/Nginx Lua API Example
-- Demonstrates OpenResty-specific patterns and APIs

local cjson = require "cjson"
local redis = require "resty.redis"
local mysql = require "resty.mysql"

-- Constants
local REDIS_HOST = "127.0.0.1"
local REDIS_PORT = 6379
local MYSQL_CONFIG = {
    host = "127.0.0.1",
    port = 3306,
    database = "myapp",
    user = "root",
    password = "secret"
}

-- Rate limiting module
local RateLimiter = {}
RateLimiter.__index = RateLimiter

function RateLimiter.new(redis_conn)
    local self = setmetatable({}, RateLimiter)
    self.redis = redis_conn
    self.window = 60  -- 1 minute window
    self.max_requests = 100
    return self
end

function RateLimiter:check(key)
    local current = ngx.time()
    local window_start = current - self.window
    
    -- Remove old entries
    self.redis:zremrangebyscore(key, 0, window_start)
    
    -- Count requests in window
    local count = self.redis:zcard(key)
    
    if count < self.max_requests then
        -- Add current request
        self.redis:zadd(key, current, current)
        self.redis:expire(key, self.window)
        return true
    end
    
    return false
end

-- Cache module
local Cache = {}
Cache.__index = Cache

function Cache.new(redis_conn)
    local self = setmetatable({}, Cache)
    self.redis = redis_conn
    self.default_ttl = 300  -- 5 minutes
    return self
end

function Cache:get(key)
    local value = self.redis:get(key)
    if value and value ~= ngx.null then
        return cjson.decode(value)
    end
    return nil
end

function Cache:set(key, value, ttl)
    ttl = ttl or self.default_ttl
    local json_value = cjson.encode(value)
    self.redis:setex(key, ttl, json_value)
end

-- Database wrapper
local Database = {}
Database.__index = Database

function Database.new(config)
    local self = setmetatable({}, Database)
    self.config = config
    return self
end

function Database:query(sql, params)
    local db = mysql:new()
    db:set_timeout(1000)
    
    local ok, err = db:connect(self.config)
    if not ok then
        ngx.log(ngx.ERR, "Failed to connect to database: ", err)
        return nil, err
    end
    
    -- Execute query
    local res, err = db:query(sql)
    if not res then
        ngx.log(ngx.ERR, "Query failed: ", err)
        return nil, err
    end
    
    -- Close connection
    db:set_keepalive(10000, 100)
    
    return res
end

-- API handlers
local function handle_auth()
    local token = ngx.var.http_authorization
    if not token then
        ngx.status = ngx.HTTP_UNAUTHORIZED
        ngx.say(cjson.encode({error = "Missing authorization token"}))
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end
    
    -- Validate token
    local user_id = validate_jwt_token(token)
    if not user_id then
        ngx.status = ngx.HTTP_UNAUTHORIZED
        ngx.say(cjson.encode({error = "Invalid token"}))
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end
    
    ngx.ctx.user_id = user_id
end

local function handle_get_user()
    local user_id = ngx.var.arg_id or ngx.ctx.user_id
    
    -- Initialize Redis
    local red = redis:new()
    red:set_timeout(1000)
    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        ngx.log(ngx.ERR, "Failed to connect to Redis: ", err)
        return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end
    
    -- Check cache
    local cache = Cache.new(red)
    local cache_key = "user:" .. user_id
    local user = cache:get(cache_key)
    
    if not user then
        -- Fetch from database
        local db = Database.new(MYSQL_CONFIG)
        local result = db:query("SELECT * FROM users WHERE id = ?", {user_id})
        
        if result and #result > 0 then
            user = result[1]
            cache:set(cache_key, user)
        else
            ngx.status = ngx.HTTP_NOT_FOUND
            ngx.say(cjson.encode({error = "User not found"}))
            return ngx.exit(ngx.HTTP_NOT_FOUND)
        end
    end
    
    ngx.header.content_type = "application/json"
    ngx.say(cjson.encode(user))
end

local function handle_create_user()
    local body = ngx.req.get_body_data()
    if not body then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.say(cjson.encode({error = "Missing request body"}))
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    
    local data = cjson.decode(body)
    
    -- Validate input
    if not data.username or not data.email then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.say(cjson.encode({error = "Missing required fields"}))
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    
    -- Create user in database
    local db = Database.new(MYSQL_CONFIG)
    local result = db:query(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        {data.username, data.email}
    )
    
    if result then
        ngx.status = ngx.HTTP_CREATED
        ngx.say(cjson.encode({id = result.insert_id, message = "User created"}))
    else
        ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
        ngx.say(cjson.encode({error = "Failed to create user"}))
    end
end

-- Middleware functions
local function cors_headers()
    ngx.header["Access-Control-Allow-Origin"] = "*"
    ngx.header["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    ngx.header["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
end

local function log_request()
    ngx.log(ngx.INFO, string.format(
        "[%s] %s %s - User: %s",
        ngx.var.remote_addr,
        ngx.var.request_method,
        ngx.var.uri,
        ngx.ctx.user_id or "anonymous"
    ))
end

-- Rate limiting check
local function check_rate_limit()
    local red = redis:new()
    red:set_timeout(1000)
    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        ngx.log(ngx.ERR, "Failed to connect to Redis for rate limiting: ", err)
        return true  -- Allow request if Redis is down
    end
    
    local limiter = RateLimiter.new(red)
    local key = "rate_limit:" .. (ngx.var.remote_addr or "unknown")
    
    if not limiter:check(key) then
        ngx.status = ngx.HTTP_TOO_MANY_REQUESTS
        ngx.say(cjson.encode({error = "Rate limit exceeded"}))
        return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
    end
end

-- Utility functions
local function validate_jwt_token(token)
    -- JWT validation logic here
    -- This is a simplified example
    if token == "valid_token" then
        return "user123"
    end
    return nil
end

local function get_request_id()
    return ngx.var.request_id or ngx.md5(ngx.var.remote_addr .. ngx.time())
end

-- Main request handler
local function main()
    -- Set request ID
    ngx.ctx.request_id = get_request_id()
    
    -- Apply middleware
    cors_headers()
    check_rate_limit()
    log_request()
    
    -- Route requests
    local method = ngx.var.request_method
    local uri = ngx.var.uri
    
    if uri == "/api/auth" and method == "POST" then
        handle_auth()
    elseif uri == "/api/users" and method == "GET" then
        handle_auth()
        handle_get_user()
    elseif uri == "/api/users" and method == "POST" then
        handle_auth()
        handle_create_user()
    elseif uri == "/health" and method == "GET" then
        ngx.say(cjson.encode({status = "healthy", timestamp = ngx.time()}))
    else
        ngx.status = ngx.HTTP_NOT_FOUND
        ngx.say(cjson.encode({error = "Route not found"}))
    end
end

-- Error handling
local function error_handler(err)
    ngx.log(ngx.ERR, "Unhandled error: ", err)
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say(cjson.encode({
        error = "Internal server error",
        request_id = ngx.ctx.request_id
    }))
end

-- Entry point
local ok, err = pcall(main)
if not ok then
    error_handler(err)
end