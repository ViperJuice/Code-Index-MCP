package com.example.akka

import akka.actor._
import akka.pattern.ask
import akka.util.Timeout
import scala.concurrent.duration._
import scala.concurrent.{Future, ExecutionContext}

// Message protocol
sealed trait Command
case class Start(name: String) extends Command
case class Stop(reason: String) extends Command
case class Process(data: String) extends Command
case object GetStatus extends Command

sealed trait Event
case class Started(name: String) extends Event
case class Stopped(reason: String) extends Event
case class ProcessingComplete(result: String) extends Event
case class Status(state: String, processed: Int) extends Event

// Classic Actor
class WorkerActor extends Actor with ActorLogging {
  private var processedCount = 0
  private var currentState = "idle"
  
  override def preStart(): Unit = {
    log.info("WorkerActor starting")
  }
  
  override def postStop(): Unit = {
    log.info("WorkerActor stopped")
  }
  
  def receive: Receive = idle
  
  def idle: Receive = {
    case Start(name) =>
      log.info(s"Starting work for $name")
      currentState = "working"
      context.become(working)
      sender() ! Started(name)
    
    case GetStatus =>
      sender() ! Status(currentState, processedCount)
  }
  
  def working: Receive = {
    case Process(data) =>
      log.info(s"Processing: $data")
      processedCount += 1
      // Simulate work
      Thread.sleep(100)
      sender() ! ProcessingComplete(s"Processed: $data")
    
    case Stop(reason) =>
      log.info(s"Stopping: $reason")
      currentState = "idle"
      context.become(idle)
      sender() ! Stopped(reason)
    
    case GetStatus =>
      sender() ! Status(currentState, processedCount)
  }
}

// Supervisor Actor
class SupervisorActor extends Actor with ActorLogging {
  import context.dispatcher
  
  private val workers = scala.collection.mutable.Map[String, ActorRef]()
  
  override val supervisorStrategy = OneForOneStrategy(
    maxNrOfRetries = 3,
    withinTimeRange = 1.minute
  ) {
    case _: ArithmeticException => Resume
    case _: NullPointerException => Restart
    case _: IllegalArgumentException => Stop
    case _: Exception => Escalate
  }
  
  def receive: Receive = {
    case "create-worker" =>
      val worker = context.actorOf(
        Props[WorkerActor],
        name = s"worker-${workers.size}"
      )
      workers += (worker.path.name -> worker)
      sender() ! worker
    
    case "list-workers" =>
      sender() ! workers.keys.toList
    
    case ("forward", workerName: String, message: Any) =>
      workers.get(workerName) match {
        case Some(worker) => worker forward message
        case None => sender() ! s"Worker $workerName not found"
      }
  }
}

// Router Actor
class RouterActor(routees: Vector[ActorRef]) extends Actor {
  private var currentIndex = 0
  
  def receive: Receive = {
    case message =>
      routees(currentIndex) ! message
      currentIndex = (currentIndex + 1) % routees.size
  }
}

// FSM Actor
class FSMActor extends Actor with FSM[FSMActor.State, FSMActor.Data] {
  import FSMActor._
  
  startWith(Idle, Uninitialized)
  
  when(Idle) {
    case Event(Initialize(name), Uninitialized) =>
      goto(Active) using Initialized(name, 0)
  }
  
  when(Active) {
    case Event(Increment, Initialized(name, count)) =>
      stay using Initialized(name, count + 1)
    
    case Event(GetCount, data @ Initialized(_, count)) =>
      sender() ! count
      stay using data
  }
  
  whenUnhandled {
    case Event(e, s) =>
      log.warning(s"Unhandled event $e in state $stateName with data $s")
      stay
  }
  
  initialize()
}

object FSMActor {
  sealed trait State
  case object Idle extends State
  case object Active extends State
  
  sealed trait Data
  case object Uninitialized extends Data
  case class Initialized(name: String, count: Int) extends Data
  
  case class Initialize(name: String)
  case object Increment
  case object GetCount
}

// Actor with Stash
class StashActor extends Actor with Stash {
  import context.dispatcher
  
  def receive: Receive = {
    case "init" =>
      context.become(initialized)
      unstashAll()
    
    case _ =>
      stash()
  }
  
  def initialized: Receive = {
    case msg =>
      println(s"Processing: $msg")
  }
}

// Main application
object AkkaApplication extends App {
  implicit val system: ActorSystem = ActorSystem("example-system")
  implicit val timeout: Timeout = Timeout(5.seconds)
  implicit val ec: ExecutionContext = system.dispatcher
  
  // Create actors
  val supervisor = system.actorOf(Props[SupervisorActor], "supervisor")
  val worker = system.actorOf(Props[WorkerActor], "main-worker")
  
  // Ask pattern
  val futureResult: Future[Any] = worker ? Start("MainJob")
  
  futureResult.foreach {
    case Started(name) => println(s"Successfully started: $name")
    case _ => println("Unexpected response")
  }
  
  // Selection
  val selection = system.actorSelection("/user/supervisor/worker-*")
  selection ! Process("bulk data")
  
  // Scheduled messages
  system.scheduler.scheduleOnce(2.seconds) {
    worker ! Stop("Scheduled stop")
  }
  
  // Graceful shutdown
  sys.addShutdownHook {
    system.terminate()
  }
}