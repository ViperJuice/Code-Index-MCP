Introduction to Functional Programming in Haskell
================================================

This is a literate Haskell file that combines documentation with executable code.
In literate Haskell, code is marked with '>' at the beginning of each line.

> module Tutorial where
>
> import Data.List (sort, group)
> import Control.Monad (guard)

Basic Functions
--------------

Let's start with some basic function definitions:

> -- | Factorial function using recursion
> factorial :: Integer -> Integer
> factorial 0 = 1
> factorial n = n * factorial (n - 1)

> -- | Fibonacci sequence using pattern matching
> fibonacci :: Int -> Int
> fibonacci 0 = 0
> fibonacci 1 = 1
> fibonacci n = fibonacci (n - 1) + fibonacci (n - 2)

List Processing
--------------

Haskell excels at list processing. Here are some examples:

> -- | Remove duplicates from a list
> unique :: Eq a => [a] -> [a]
> unique [] = []
> unique (x:xs) = x : unique (filter (/= x) xs)

> -- | Count occurrences of each element
> countOccurrences :: Ord a => [a] -> [(a, Int)]
> countOccurrences = map (\xs -> (head xs, length xs)) . group . sort

Higher-Order Functions
---------------------

Functions that take or return other functions are called higher-order functions:

> -- | Apply a function twice
> twice :: (a -> a) -> a -> a
> twice f x = f (f x)

> -- | Compose two functions
> compose :: (b -> c) -> (a -> b) -> a -> c
> compose f g x = f (g x)

> -- | Create a curried addition function
> add :: Int -> Int -> Int
> add x y = x + y
>
> -- | Partially applied function
> addFive :: Int -> Int
> addFive = add 5

Monads and Do Notation
---------------------

The Maybe monad is useful for handling computations that might fail:

> -- | Safe division
> safeDiv :: Double -> Double -> Maybe Double
> safeDiv _ 0 = Nothing
> safeDiv x y = Just (x / y)

> -- | Chain operations that might fail
> calculate :: Double -> Maybe Double
> calculate x = do
>   y <- safeDiv x 2
>   z <- safeDiv y 3
>   return (z + 1)

List Comprehensions
------------------

List comprehensions provide a concise way to create lists:

> -- | Generate Pythagorean triples
> pythTriples :: Int -> [(Int, Int, Int)]
> pythTriples n = [(a, b, c) | a <- [1..n],
>                              b <- [a..n],
>                              c <- [b..n],
>                              a^2 + b^2 == c^2]

> -- | Using guards in list comprehensions
> evenSquares :: [Int] -> [Int]
> evenSquares xs = [x^2 | x <- xs, even x, x > 0]

Custom Data Types
----------------

We can define our own algebraic data types:

> -- | Binary tree data structure
> data Tree a = Empty
>             | Node a (Tree a) (Tree a)
>             deriving (Show, Eq)

> -- | Insert into a binary search tree
> insert :: Ord a => a -> Tree a -> Tree a
> insert x Empty = Node x Empty Empty
> insert x (Node y left right)
>   | x < y     = Node y (insert x left) right
>   | x > y     = Node y left (insert x right)
>   | otherwise = Node y left right

> -- | In-order traversal
> inorder :: Tree a -> [a]
> inorder Empty = []
> inorder (Node x left right) = inorder left ++ [x] ++ inorder right

Type Classes
-----------

Type classes define interfaces that types can implement:

> -- | A type class for things that can be reversed
> class Reversible a where
>   rev :: a -> a

> -- | Instance for lists
> instance Reversible [a] where
>   rev = reverse

> -- | Instance for our Tree type
> instance Reversible (Tree a) where
>   rev Empty = Empty
>   rev (Node x left right) = Node x (rev right) (rev left)

Conclusion
----------

This tutorial has covered some fundamental concepts in Haskell including:
- Basic function definitions
- Pattern matching
- Higher-order functions
- Monads and do-notation
- List comprehensions
- Custom data types
- Type classes

These building blocks form the foundation for writing elegant and powerful
functional programs in Haskell.