package com.example.functional

import scala.concurrent.{Future, ExecutionContext}
import scala.util.{Try, Success, Failure}

// Algebraic Data Types
sealed trait Tree[+A]
case class Leaf[A](value: A) extends Tree[A]
case class Branch[A](left: Tree[A], right: Tree[A]) extends Tree[A]

// Type aliases and higher-kinded types
type Result[A] = Either[String, A]
type Reader[R, A] = R => A
type State[S, A] = S => (A, S)

// Trait with abstract types
trait Monad[F[_]] {
  def pure[A](a: A): F[A]
  def flatMap[A, B](fa: F[A])(f: A => F[B]): F[B]
  
  // Extension method
  def map[A, B](fa: F[A])(f: A => B): F[B] = 
    flatMap(fa)(a => pure(f(a)))
}

// Implicit conversions and classes
implicit class RichOption[A](opt: Option[A]) {
  def getOrThrow(msg: String): A = opt match {
    case Some(value) => value
    case None => throw new NoSuchElementException(msg)
  }
}

// Pattern matching with guards
object TreeOps {
  def depth[A](tree: Tree[A]): Int = tree match {
    case Leaf(_) => 1
    case Branch(left, right) => 
      1 + math.max(depth(left), depth(right))
  }
  
  // For comprehension
  def traverse[A, B](tree: Tree[A])(f: A => Option[B]): Option[Tree[B]] = 
    tree match {
      case Leaf(value) => 
        for {
          b <- f(value)
        } yield Leaf(b)
      
      case Branch(left, right) =>
        for {
          l <- traverse(left)(f)
          r <- traverse(right)(f)
        } yield Branch(l, r)
    }
}

// Higher-order functions
class FunctionalService(implicit ec: ExecutionContext) {
  
  def compose[A, B, C](f: B => C, g: A => B): A => C = 
    a => f(g(a))
  
  def curry[A, B, C](f: (A, B) => C): A => B => C = 
    a => b => f(a, b)
  
  // Partial functions
  val dividePartial: PartialFunction[(Int, Int), Int] = {
    case (x, y) if y != 0 => x / y
  }
  
  // Lazy evaluation
  lazy val expensiveComputation: Int = {
    Thread.sleep(1000)
    42
  }
  
  // By-name parameters
  def retry[A](times: Int)(block: => A): Try[A] = {
    if (times <= 0) {
      Try(block)
    } else {
      Try(block) match {
        case Success(value) => Success(value)
        case Failure(_) => retry(times - 1)(block)
      }
    }
  }
}

// Variance annotations
trait Container[+A] {
  def get: A
}

trait MutableContainer[-A] {
  def put(value: A): Unit
}

// Self-types
trait Database { self: Logging =>
  def query(sql: String): Unit = {
    log(s"Executing: $sql")
  }
}

trait Logging {
  def log(message: String): Unit = println(message)
}

// Companion object with factory methods
object FunctionalPatterns {
  def apply(): FunctionalPatterns = new FunctionalPatterns()
  
  // Implicit parameter
  implicit val defaultOrdering: Ordering[Int] = Ordering.Int
  
  def sortWithImplicit[A](list: List[A])(implicit ord: Ordering[A]): List[A] = 
    list.sorted
}

class FunctionalPatterns {
  // Abstract type member
  type T
  
  // Path-dependent types
  class Inner {
    def process(other: FunctionalPatterns#Inner): Unit = {}
  }
}