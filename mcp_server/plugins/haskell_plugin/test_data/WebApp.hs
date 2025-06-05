{-# LANGUAGE DataKinds #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE FlexibleInstances #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE ScopedTypeVariables #-}
{-# LANGUAGE TypeOperators #-}
{-# LANGUAGE TypeFamilies #-}

-- | Example web application using Servant
module WebApp where

import Control.Monad.IO.Class (liftIO)
import Control.Monad.Trans.Reader (ReaderT, asks, runReaderT)
import Data.Aeson (FromJSON, ToJSON)
import Data.Text (Text)
import qualified Data.Text as T
import GHC.Generics (Generic)
import Network.Wai (Application)
import Network.Wai.Handler.Warp (run)
import Servant

-- | User data type
data User = User
  { userId :: Int
  , userName :: Text
  , userEmail :: Text
  } deriving (Eq, Show, Generic)

instance ToJSON User
instance FromJSON User

-- | Post data type
data Post = Post
  { postId :: Int
  , postTitle :: Text
  , postContent :: Text
  , postAuthorId :: Int
  } deriving (Eq, Show, Generic)

instance ToJSON Post
instance FromJSON Post

-- | API type definition using Servant
type UserAPI = "users" :> Get '[JSON] [User]
          :<|> "users" :> Capture "id" Int :> Get '[JSON] User
          :<|> "users" :> ReqBody '[JSON] User :> Post '[JSON] User
          :<|> "users" :> Capture "id" Int :> Delete '[JSON] ()

type PostAPI = "posts" :> Get '[JSON] [Post]
          :<|> "posts" :> Capture "id" Int :> Get '[JSON] Post
          :<|> "posts" :> ReqBody '[JSON] Post :> Post '[JSON] Post

type API = UserAPI :<|> PostAPI

-- | Application configuration
data AppConfig = AppConfig
  { configPort :: Int
  , configDBPath :: FilePath
  , configLogLevel :: Text
  }

-- | Application monad
newtype AppM a = AppM (ReaderT AppConfig IO a)
  deriving (Functor, Applicative, Monad, MonadIO)

runAppM :: AppConfig -> AppM a -> IO a
runAppM config (AppM m) = runReaderT m config

-- | User handlers
userHandlers :: ServerT UserAPI AppM
userHandlers = getAllUsers
          :<|> getUser
          :<|> createUser
          :<|> deleteUser
  where
    getAllUsers :: AppM [User]
    getAllUsers = return
      [ User 1 "Alice" "alice@example.com"
      , User 2 "Bob" "bob@example.com"
      ]
    
    getUser :: Int -> AppM User
    getUser uid = do
      users <- getAllUsers
      case filter (\u -> userId u == uid) users of
        [] -> throwError err404 { errBody = "User not found" }
        (u:_) -> return u
    
    createUser :: User -> AppM User
    createUser user = do
      liftIO $ putStrLn $ "Creating user: " ++ show user
      return user
    
    deleteUser :: Int -> AppM ()
    deleteUser uid = do
      liftIO $ putStrLn $ "Deleting user: " ++ show uid
      return ()

-- | Post handlers
postHandlers :: ServerT PostAPI AppM
postHandlers = getAllPosts
          :<|> getPost
          :<|> createPost
  where
    getAllPosts :: AppM [Post]
    getAllPosts = return
      [ Post 1 "First Post" "Hello, World!" 1
      , Post 2 "Second Post" "Another post" 2
      ]
    
    getPost :: Int -> AppM Post
    getPost pid = do
      posts <- getAllPosts
      case filter (\p -> postId p == pid) posts of
        [] -> throwError err404 { errBody = "Post not found" }
        (p:_) -> return p
    
    createPost :: Post -> AppM Post
    createPost post = do
      liftIO $ putStrLn $ "Creating post: " ++ show post
      return post

-- | Combined server
server :: ServerT API AppM
server = userHandlers :<|> postHandlers

-- | API proxy
api :: Proxy API
api = Proxy

-- | Natural transformation from AppM to Handler
appToHandler :: AppConfig -> AppM a -> Handler a
appToHandler config appM = liftIO $ runAppM config appM

-- | WAI Application
app :: AppConfig -> Application
app config = serve api $ hoistServer api (appToHandler config) server

-- | Middleware for logging
loggingMiddleware :: Application -> Application
loggingMiddleware app req respond = do
  putStrLn $ "Request: " ++ show (pathInfo req)
  app req respond

-- | Main entry point
main :: IO ()
main = do
  let config = AppConfig
        { configPort = 8080
        , configDBPath = "app.db"
        , configLogLevel = "info"
        }
  
  putStrLn $ "Starting server on port " ++ show (configPort config)
  run (configPort config) $ loggingMiddleware $ app config

-- | Database types using type families
type family DBKey entity where
  DBKey User = Int
  DBKey Post = Int

-- | Repository type class
class Repository entity where
  findById :: DBKey entity -> AppM (Maybe entity)
  findAll :: AppM [entity]
  save :: entity -> AppM entity
  delete :: DBKey entity -> AppM ()

-- | User repository instance
instance Repository User where
  findById uid = do
    users <- getAllUsers
    return $ find (\u -> userId u == uid) users
    where
      getAllUsers = return
        [ User 1 "Alice" "alice@example.com"
        , User 2 "Bob" "bob@example.com"
        ]
      find p xs = case filter p xs of
        [] -> Nothing
        (x:_) -> Just x
  
  findAll = return
    [ User 1 "Alice" "alice@example.com"
    , User 2 "Bob" "bob@example.com"
    ]
  
  save user = return user
  delete _ = return ()