"""Comprehensive tests for Haskell plugin."""

import pytest
from pathlib import Path
from .plugin import Plugin


class TestHaskellPlugin:
    """Test cases for Haskell plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported Haskell extensions
        assert self.plugin.supports("test.hs")
        assert self.plugin.supports("test.lhs")  # Literate Haskell
        assert self.plugin.supports("test.hsc")  # Haskell with C
        
        # Test project files
        assert self.plugin.supports("myproject.cabal")
        assert self.plugin.supports("stack.yaml")
        assert self.plugin.supports("package.yaml")
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.py")
        assert not self.plugin.supports("test.js")
    
    def test_parse_simple_haskell(self):
        """Test parsing simple Haskell code."""
        content = '''module Main where

--  < /dev/null |  Main entry point
main :: IO ()
main = putStrLn "Hello, World\!"

-- | Add two numbers
add :: Int -> Int -> Int
add x y = x + y
'''
        
        result = self.plugin.indexFile("test.hs", content)
        assert result["language"] == "haskell"
        assert len(result["symbols"]) >= 3
        
        # Check module
        module_symbols = [s for s in result["symbols"] if s["kind"] == "module"]
        assert len(module_symbols) == 1
        assert module_symbols[0]["symbol"] == "Main"
        
        # Check functions
        func_symbols = [s for s in result["symbols"] if s["kind"] == "function"]
        assert len(func_symbols) == 2
        func_names = {s["symbol"] for s in func_symbols}
        assert "main" in func_names
        assert "add" in func_names
    
    def test_parse_type_signatures(self):
        """Test parsing type signatures and functions."""
        content = '''module TypeSigs where

-- Multiple names in one signature
map, filter :: (a -> b) -> [a] -> [b]
map f [] = []
map f (x:xs) = f x : map f xs

filter p [] = []
filter p (x:xs) 
  | p x       = x : filter p xs
  | otherwise = filter p xs

-- Complex type signature
foldr :: (a -> b -> b) -> b -> [a] -> b
foldr f z [] = z
foldr f z (x:xs) = f x (foldr f z xs)
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check functions with type signatures
        func_symbols = [s for s in result["symbols"] if s["kind"] == "function"]
        assert len(func_symbols) >= 3
        
        # Check that type signatures are captured
        map_func = next((s for s in func_symbols if s["symbol"] == "map"), None)
        assert map_func is not None
        assert "::" in map_func["signature"]
        assert map_func["metadata"]["has_type_signature"]
    
    def test_parse_data_types(self):
        """Test parsing data types and newtypes."""
        content = '''module DataTypes where

-- Simple data type
data Bool = True | False

-- Parameterized data type
data Maybe a = Nothing | Just a

-- Record syntax
data Person = Person 
  { name :: String
  , age :: Int
  , email :: Maybe String
  }

-- Newtype
newtype Identity a = Identity { runIdentity :: a }

-- Type alias
type String = [Char]
type Predicate a = a -> Bool

-- GADT syntax
data Expr a where
  Lit :: a -> Expr a
  Add :: Num a => Expr a -> Expr a -> Expr a
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check data types
        type_symbols = [s for s in result["symbols"] if s["kind"] in ["data", "newtype", "type_alias"]]
        assert len(type_symbols) >= 6
        
        type_names = {s["symbol"]: s["kind"] for s in type_symbols}
        assert type_names.get("Bool") == "data"
        assert type_names.get("Maybe") == "data"
        assert type_names.get("Person") == "data"
        assert type_names.get("Identity") == "newtype"
        assert type_names.get("String") == "type_alias"
        assert type_names.get("Expr") == "data"
    
    def test_parse_type_classes(self):
        """Test parsing type classes and instances."""
        content = '''module TypeClasses where

-- Simple type class
class Eq a where
  (==) :: a -> a -> Bool
  (/=) :: a -> a -> Bool
  x /= y = not (x == y)

-- Type class with constraints
class Eq a => Ord a where
  compare :: a -> a -> Ordering
  (<), (<=), (>), (>=) :: a -> a -> Bool
  max, min :: a -> a -> a

-- Instance declaration
instance Eq Bool where
  True == True = True
  False == False = True
  _ == _ = False

-- Instance with constraints
instance Eq a => Eq (Maybe a) where
  Nothing == Nothing = True
  Just x == Just y = x == y
  _ == _ = False

-- Type family
type family Elem a where
  Elem [a] = a
  Elem (Maybe a) = a
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check type classes
        class_symbols = [s for s in result["symbols"] if s["kind"] == "class"]
        assert len(class_symbols) >= 2
        class_names = {s["symbol"] for s in class_symbols}
        assert "Eq" in class_names
        assert "Ord" in class_names
        
        # Check instances
        instance_symbols = [s for s in result["symbols"] if s["kind"] == "instance"]
        assert len(instance_symbols) >= 2
    
    def test_parse_imports_exports(self):
        """Test parsing imports and module exports."""
        content = '''module MyModule 
  ( MyType(..)
  , myFunction
  , MyClass(method1, method2)
  , module Data.List
  ) where

import Data.List
import qualified Data.Map as M
import Data.Maybe (Maybe(..), fromMaybe)
import Control.Monad hiding (forM)
import qualified Control.Concurrent

-- Rest of module
data MyType = MyConstructor
myFunction :: Int -> Int
myFunction = id

class MyClass a where
  method1 :: a -> String
  method2 :: a -> a -> Bool
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check module with exports
        module_symbol = next(s for s in result["symbols"] if s["kind"] == "module")
        assert module_symbol["symbol"] == "MyModule"
        assert "exports" in module_symbol["metadata"]
        
        # Check imports
        import_symbols = [s for s in result["symbols"] if s["kind"] == "import"]
        assert len(import_symbols) == 5
        
        # Check qualified imports
        data_map = next(s for s in import_symbols if s["symbol"] == "Data.Map")
        assert data_map["metadata"]["qualified"]
        assert data_map["metadata"]["alias"] == "M"
    
    def test_parse_language_pragmas(self):
        """Test parsing language pragmas."""
        content = '''{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE TypeFamilies #-}
{-# OPTIONS_GHC -Wall #-}
{-# INLINE myFunction #-}

module Pragmas where

{-# SPECIALIZE myFunction :: Int -> Int #-}
myFunction :: Num a => a -> a
myFunction x = x + 1
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check pragmas in metadata
        assert "pragmas" in result["metadata"]
        pragmas = result["metadata"]["pragmas"]
        assert len(pragmas) >= 4
        
        language_pragmas = [p for p in pragmas if p["type"] == "LANGUAGE"]
        assert len(language_pragmas) >= 3
        pragma_contents = {p["content"] for p in language_pragmas}
        assert "DataKinds" in pragma_contents
        assert "GADTs" in pragma_contents
        assert "TypeFamilies" in pragma_contents
    
    def test_parse_literate_haskell(self):
        """Test parsing literate Haskell files."""
        content = '''This is a literate Haskell file.

> module LiterateExample where
> 
> -- | Main function
> main :: IO ()
> main = putStrLn "Hello from literate Haskell\!"

Some explanation text here.

> -- | Helper function
> helper :: String -> String
> helper = map toUpper

More text.
'''
        
        result = self.plugin.indexFile("test.lhs", content)
        assert result["language"] == "haskell"
        assert result["metadata"]["is_literate"]
        
        # Check that code was extracted correctly
        func_symbols = [s for s in result["symbols"] if s["kind"] == "function"]
        assert len(func_symbols) == 2
        func_names = {s["symbol"] for s in func_symbols}
        assert "main" in func_names
        assert "helper" in func_names
    
    def test_parse_operators(self):
        """Test parsing infix operators."""
        content = '''module Operators where

infixl 7 *., <.>
infixr 5 +++
infix 4 `elem`

(*.) :: Num a => a -> a -> a
x *. y = x * y

(<.>) :: (b -> c) -> (a -> b) -> a -> c
f <.> g = \\x -> f (g x)

(+++) :: [a] -> [a] -> [a]
(+++) = (++)
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Check operators
        operator_symbols = [s for s in result["symbols"] if s["kind"] == "operator"]
        assert len(operator_symbols) >= 3
        
        op_names = {s["symbol"] for s in operator_symbols}
        assert "*." in op_names
        assert "<.>" in op_names
        assert "+++" in op_names
        
        # Check precedence
        mult_op = next(s for s in operator_symbols if s["symbol"] == "*.")
        assert mult_op["metadata"]["precedence"] == "7"
    
    def test_parse_cabal_file(self):
        """Test parsing Cabal project files."""
        content = '''name:                myproject
version:             0.1.0.0
synopsis:            A test project
license:             BSD3
author:              Test Author
maintainer:          test@example.com

library
  exposed-modules:     MyLib
                     , MyLib.Utils
                     , MyLib.Types
  build-depends:       base >= 4.14 && < 5
                     , text >= 1.2
                     , containers >= 0.6
  hs-source-dirs:      src
  default-language:    Haskell2010

executable myproject-exe
  main-is:             Main.hs
  build-depends:       base >= 4.14 && < 5
                     , myproject
  hs-source-dirs:      app
  default-language:    Haskell2010

test-suite myproject-test
  type:                exitcode-stdio-1.0
  main-is:             Spec.hs
  build-depends:       base >= 4.14 && < 5
                     , myproject
                     , hspec >= 2.7
  hs-source-dirs:      test
  default-language:    Haskell2010
'''
        
        result = self.plugin.indexFile("myproject.cabal", content)
        assert result["language"] == "cabal"
        
        # Check package name
        package_symbols = [s for s in result["symbols"] if s["kind"] == "package"]
        assert len(package_symbols) == 1
        assert package_symbols[0]["symbol"] == "myproject"
        
        # Check sections
        section_kinds = {"library", "executable", "test-suite"}
        sections = [s for s in result["symbols"] if s["kind"] in section_kinds]
        assert len(sections) >= 3
        
        # Check exposed modules
        exposed_modules = [s for s in result["symbols"] if s["kind"] == "exposed-module"]
        assert len(exposed_modules) >= 3
        module_names = {s["symbol"] for s in exposed_modules}
        assert "MyLib" in module_names
        assert "MyLib.Utils" in module_names
        
        # Check dependencies
        deps = [s for s in result["symbols"] if s["kind"] == "dependency"]
        assert len(deps) >= 3
        dep_names = {s["symbol"] for s in deps}
        assert "base" in dep_names
        assert "text" in dep_names
        assert "containers" in dep_names
    
    def test_parse_stack_yaml(self):
        """Test parsing Stack configuration files."""
        content = '''resolver: lts-18.28

packages:
- .
- ../my-other-package

extra-deps:
- acme-missiles-0.3@sha256:2ba66a092a32593880a87fb00f3213762d7bca65a687d45965778deb8694c5d1,613
- some-package-1.2.3

flags:
  myproject:
    dev: true
'''
        
        result = self.plugin.indexFile("stack.yaml", content)
        assert result["language"] == "yaml"
        
        # Check resolver
        resolver_symbols = [s for s in result["symbols"] if s["kind"] == "resolver"]
        assert len(resolver_symbols) == 1
        assert resolver_symbols[0]["symbol"] == "lts-18.28"
        
        # Check packages
        package_symbols = [s for s in result["symbols"] if s["kind"] == "package"]
        assert len(package_symbols) >= 2
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        content = '''module Definitions where

data MyType = MyConstructor Int String

myFunction :: MyType -> String
myFunction (MyConstructor n s) = s ++ show n

class MyClass a where
  myMethod :: a -> Int
'''
        
        # Index the file first
        self.plugin.indexFile("test.hs", content)
        
        # Test finding definitions
        func_def = self.plugin.getDefinition("myFunction")
        assert func_def is not None
        assert func_def["kind"] == "function"
        assert "MyType -> String" in func_def["signature"]
        
        type_def = self.plugin.getDefinition("MyType")
        assert type_def is not None
        assert type_def["kind"] == "data"
        
        class_def = self.plugin.getDefinition("MyClass")
        assert class_def is not None
        assert class_def["kind"] == "class"
    
    def test_find_references(self):
        """Test finding symbol references."""
        content1 = '''module Module1 where

data MyType = MyConstructor

useMyType :: MyType -> Int
useMyType MyConstructor = 42
'''
        
        content2 = '''module Module2 where

import Module1

example :: MyType -> MyType
example x = MyConstructor
'''
        
        # Create test files
        Path("module1.hs").write_text(content1)
        Path("module2.hs").write_text(content2)
        
        try:
            # Index files
            self.plugin.indexFile("module1.hs", content1)
            self.plugin.indexFile("module2.hs", content2)
            
            # Find references
            refs = self.plugin.findReferences("MyType")
            assert len(refs) >= 2
            
            file_names = {ref.file for ref in refs}
            assert "module1.hs" in file_names
            assert "module2.hs" in file_names
            
        finally:
            # Clean up
            Path("module1.hs").unlink(missing_ok=True)
            Path("module2.hs").unlink(missing_ok=True)
    
    def test_search_functionality(self):
        """Test search functionality."""
        content = '''module Search where

-- | Calculate fibonacci numbers
fibonacci :: Int -> Int
fibonacci 0 = 0
fibonacci 1 = 1
fibonacci n = fibonacci (n - 1) + fibonacci (n - 2)

-- | Quick sort implementation
quickSort :: Ord a => [a] -> [a]
quickSort [] = []
quickSort (x:xs) = quickSort smaller ++ [x] ++ quickSort larger
  where
    smaller = filter (< x) xs
    larger = filter (>= x) xs
'''
        
        self.plugin.indexFile("test.hs", content)
        
        # Search for fibonacci
        results = self.plugin.search("fibonacci")
        assert len(results) > 0
        
        # Search for sort
        results = self.plugin.search("sort")
        assert len(results) > 0
        
        # Limit results
        results = self.plugin.search("fibonacci", {"limit": 1})
        assert len(results) <= 1
    
    def test_complex_type_signatures(self):
        """Test parsing complex type signatures."""
        content = '''module ComplexTypes where

-- Higher-rank types
runST :: (forall s. ST s a) -> a

-- Constraint kinds
type family All (c :: k -> Constraint) (xs :: [k]) :: Constraint where
  All c '[] = ()
  All c (x ': xs) = (c x, All c xs)

-- Type-level programming
data Nat = Zero | Succ Nat

type family Add (m :: Nat) (n :: Nat) :: Nat where
  Add Zero n = n
  Add (Succ m) n = Succ (Add m n)

-- Poly-kinded type
data Proxy (a :: k) = Proxy

-- Existential types
data SomeException = forall e. Exception e => SomeException e
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Should still parse basic structure even with complex types
        assert len(result["symbols"]) > 0
        
        # Check for type families
        type_families = [s for s in result["symbols"] if s["kind"] == "type_family"]
        assert len(type_families) >= 2
    
    def test_template_haskell(self):
        """Test handling Template Haskell syntax."""
        content = '''module TemplateHaskell where

import Language.Haskell.TH

-- Template Haskell splice
$(deriveJSON defaultOptions ''Person)

-- Quasi-quotation
example = [expr| 1 + 2 |]

-- Normal function after TH
normalFunction :: Int -> Int
normalFunction x = x * 2
'''
        
        result = self.plugin.indexFile("test.hs", content)
        
        # Should still parse normal functions
        func_symbols = [s for s in result["symbols"] if s["kind"] == "function"]
        assert any(s["symbol"] == "normalFunction" for s in func_symbols)
