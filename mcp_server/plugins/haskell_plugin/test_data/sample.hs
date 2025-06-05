-- | Sample Haskell module demonstrating various language features
module Sample 
  ( Person(..)
  , greet
  , Maybe(..)
  , safeDivide
  ) where

import Data.List (sort, nub)
import qualified Data.Map as M
import Control.Monad (forM_, when)

-- Language extensions
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE TypeFamilies #-}

-- | Person data type with record syntax
data Person = Person
  { name :: String
  , age :: Int
  , email :: Maybe String
  } deriving (Eq, Show, Read)

-- | Greeting function with type signature
greet :: Person -> String
greet Person{name = n, age = a} = 
  "Hello, " ++ n ++ "! You are " ++ show a ++ " years old."

-- | Custom Maybe type (shadowing Prelude)
data Maybe a = Nothing | Just a
  deriving (Eq, Ord, Show)

-- | Safe division function
safeDivide :: Double -> Double -> Maybe Double
safeDivide _ 0 = Nothing
safeDivide x y = Just (x / y)

-- | Type class example
class Printable a where
  toString :: a -> String
  print :: a -> IO ()
  print x = putStrLn (toString x)

-- | Instance declaration
instance Printable Person where
  toString = greet

-- | Higher-order function
mapMaybe :: (a -> b) -> Maybe a -> Maybe b
mapMaybe _ Nothing = Nothing
mapMaybe f (Just x) = Just (f x)

-- | List comprehension example
squares :: [Int] -> [Int]
squares xs = [x * x | x <- xs, x > 0]

-- | Pattern matching with guards
classify :: Int -> String
classify n
  | n < 0     = "negative"
  | n == 0    = "zero"
  | n < 10    = "single digit"
  | otherwise = "large"

-- | Infix operator
infixl 7 <+>
(<+>) :: Num a => a -> a -> a
x <+> y = x + y + 1

-- | Type synonym
type Name = String
type Age = Int
type PersonInfo = (Name, Age)

-- | Newtype wrapper
newtype UserId = UserId Int
  deriving (Eq, Show)

-- | GADT example
data Expr a where
  Lit :: a -> Expr a
  Add :: Num a => Expr a -> Expr a -> Expr a
  Equal :: Eq a => Expr a -> Expr a -> Expr Bool

-- | Type family
type family Element container where
  Element [a] = a
  Element (Maybe a) = a
  Element (M.Map k v) = v

-- | Main function
main :: IO ()
main = do
  let john = Person "John" 30 (Just "john@example.com")
  putStrLn $ greet john
  
  forM_ [1..5] $ \n -> do
    when (even n) $ putStrLn $ "Even: " ++ show n
  
  case safeDivide 10 2 of
    Nothing -> putStrLn "Division by zero!"
    Just result -> putStrLn $ "Result: " ++ show result