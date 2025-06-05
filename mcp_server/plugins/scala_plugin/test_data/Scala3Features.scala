package com.example.scala3

// Scala 3 enum
enum Color:
  case Red, Green, Blue
  case RGB(r: Int, g: Int, b: Int)
  
  def toHex: String = this match
    case Red => "#FF0000"
    case Green => "#00FF00"
    case Blue => "#0000FF"
    case RGB(r, g, b) => f"#$r%02X$g%02X$b%02X"

// Union types
type StringOrInt = String | Int
type Nullable[T] = T | Null

// Intersection types
trait Resettable:
  def reset(): Unit

trait Growable[T]:
  def add(t: T): Unit

type ResetGrowable[T] = Resettable & Growable[T]

// Given instances (replacing implicits)
given intOrdering: Ordering[Int] = Ordering.Int.reverse

given listOrdering[T](using ord: Ordering[T]): Ordering[List[T]] with
  def compare(x: List[T], y: List[T]): Int = 
    (x, y) match
      case (Nil, Nil) => 0
      case (Nil, _) => -1
      case (_, Nil) => 1
      case (xh :: xt, yh :: yt) =>
        val c = ord.compare(xh, yh)
        if c != 0 then c else compare(xt, yt)

// Using clauses (context parameters)
def max[T](x: T, y: T)(using ord: Ordering[T]): T =
  if ord.compare(x, y) >= 0 then x else y

// Extension methods
extension (s: String)
  def greet: String = s"Hello, $s!"
  def shout: String = s.toUpperCase + "!"

extension [T](xs: List[T])
  def second: Option[T] = xs match
    case _ :: second :: _ => Some(second)
    case _ => None

// Opaque type aliases
object Ids:
  opaque type UserId = Long
  opaque type ProductId = Long
  
  object UserId:
    def apply(id: Long): UserId = id
    
  object ProductId:
    def apply(id: Long): ProductId = id
  
  extension (id: UserId)
    def value: Long = id

// Match types
type Elem[X] = X match
  case String => Char
  case Array[t] => t
  case Iterable[t] => t

// Dependent function types
trait Entry:
  type Key
  val key: Key

def extractKey(e: Entry): e.Key = e.key

// Context functions (implicit function types)
type Executable[T] = ExecutionContext ?=> T

def execute[T](executable: Executable[T]): T =
  given ExecutionContext = ExecutionContext.global
  executable

// Inline and metaprogramming
inline def power(x: Double, inline n: Int): Double =
  inline if n == 0 then 1.0
  else inline if n % 2 == 1 then x * power(x, n - 1)
  else power(x * x, n / 2)

// New control syntax
object ControlFlow:
  def repeatUntil(condition: => Boolean)(body: => Unit): Unit =
    body
    if !condition then repeatUntil(condition)(body)
  
  // Scala 3 if-then-else
  def checkAge(age: Int): String =
    if age >= 18 then "Adult"
    else if age >= 13 then "Teenager"
    else "Child"
  
  // Pattern matching with guards
  def describe(x: Any): String = x match
    case i: Int if i > 0 => "positive integer"
    case i: Int if i < 0 => "negative integer"
    case 0 => "zero"
    case s: String => s"string: $s"
    case _ => "something else"

// Structural types
type Closeable = {
  def close(): Unit
}

def autoClose[T <: Closeable](resource: T)(f: T => Unit): Unit =
  try f(resource)
  finally resource.close()

// Export clauses
class StringBuilder:
  private val sb = new java.lang.StringBuilder
  
  export sb.{append, toString}
  
  def clear(): Unit = sb.setLength(0)

// Main annotation
@main def hello(name: String, count: Int = 1): Unit =
  for i <- 1 to count do
    println(s"Hello, $name!")