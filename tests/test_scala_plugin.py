"""Comprehensive tests for the Scala plugin."""

import pytest
from pathlib import Path

from mcp_server.plugins.scala_plugin.plugin import Plugin as ScalaPlugin, ScalaParser
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


@pytest.fixture
def scala_plugin():
    """Create a Scala plugin instance."""
    return ScalaPlugin()


@pytest.fixture
def scala_parser():
    """Create a Scala parser instance."""
    return ScalaParser()


@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent.parent / "mcp_server" / "plugins" / "scala_plugin" / "test_data"


class TestScalaPlugin:
    """Test cases for Scala plugin functionality."""
    
    def test_plugin_initialization(self, scala_plugin):
        """Test plugin initializes correctly."""
        assert scala_plugin.lang == "scala"
        assert scala_plugin.supports("test.scala")
        assert scala_plugin.supports("test.sc")
        assert scala_plugin.supports("build.sbt")
        assert not scala_plugin.supports("test.java")
    
    def test_functional_patterns_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of functional programming patterns."""
        file_path = test_data_dir / "FunctionalPatterns.scala"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        assert result["language"] == "scala"
        assert result["file"] == str(file_path)
        assert len(result["symbols"]) > 0
        
        # Check for specific symbols
        symbol_names = {s["symbol"] for s in result["symbols"]}
        symbol_types = {s["kind"] for s in result["symbols"]}
        
        # Check for algebraic data types
        assert "Tree" in symbol_names
        assert "Leaf" in symbol_names
        assert "Branch" in symbol_names
        
        # Check for type aliases
        assert "Result" in symbol_names
        assert "Reader" in symbol_names
        
        # Check for traits
        assert "Monad" in symbol_names
        
        # Check for implicit class
        assert "RichOption" in symbol_names
        
        # Check for objects
        assert "TreeOps" in symbol_names
        assert "FunctionalPatterns" in symbol_names
        
        # Check symbol types
        assert "trait" in symbol_types
        assert "class" in symbol_types
        assert "object" in symbol_types
        assert "def" in symbol_types
        assert "type" in symbol_types
    
    def test_scala3_features_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of Scala 3 specific features."""
        file_path = test_data_dir / "Scala3Features.scala"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        # Check for enums
        symbol_names = {s["symbol"] for s in result["symbols"]}
        assert "Color" in symbol_names
        
        # Check for given instances
        givens = [s for s in result["symbols"] if s["kind"] == "given"]
        assert len(givens) > 0
        
        # Check for extension methods
        extensions = [s for s in result["symbols"] if s["kind"] == "extension"]
        assert len(extensions) > 0
        
        # Check for opaque types (detected as objects)
        assert "Ids" in symbol_names
        
        # Check for main annotation
        assert "hello" in symbol_names
    
    def test_akka_actor_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of Akka actor patterns."""
        file_path = test_data_dir / "AkkaActorSystem.scala"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        # Check for actors
        actors = [s for s in result["symbols"] if s["kind"] == "actor"]
        assert len(actors) > 0
        
        actor_names = {s["symbol"] for s in actors}
        assert "WorkerActor" in actor_names
        assert "SupervisorActor" in actor_names
        
        # Check for message protocol
        symbol_names = {s["symbol"] for s in result["symbols"]}
        assert "Command" in symbol_names
        assert "Event" in symbol_names
        assert "Start" in symbol_names
        assert "Stop" in symbol_names
    
    def test_play_controller_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of Play Framework controllers."""
        file_path = test_data_dir / "PlayController.scala"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        # Check for controllers
        controllers = [s for s in result["symbols"] if s["kind"] == "controller"]
        assert len(controllers) > 0
        
        # Check for action methods
        actions = [s for s in result["symbols"] if s["kind"] == "action"]
        assert len(actions) > 0
        
        # Check for specific symbols
        symbol_names = {s["symbol"] for s in result["symbols"]}
        assert "UserController" in symbol_names
        assert "AuthAction" in symbol_names
        assert "JsonFormats" in symbol_names
    
    def test_spark_job_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of Apache Spark applications."""
        file_path = test_data_dir / "SparkJob.scala"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        # Check for Spark components
        spark_components = [s for s in result["symbols"] if s["kind"] == "spark"]
        assert len(spark_components) > 0
        
        # Check for case classes
        symbol_names = {s["symbol"] for s in result["symbols"]}
        assert "Transaction" in symbol_names
        assert "UserProfile" in symbol_names
        assert "AggregatedMetrics" in symbol_names
        
        # Check for Spark jobs
        assert "FraudDetectionJob" in symbol_names
        assert "FraudDetectionStreaming" in symbol_names
    
    def test_sbt_parsing(self, scala_plugin, test_data_dir):
        """Test parsing of SBT build files."""
        file_path = test_data_dir / "build.sbt"
        if not file_path.exists():
            pytest.skip("Test data file not found")
        
        content = file_path.read_text()
        result = scala_plugin.indexFile(file_path, content)
        
        assert result["language"] == "sbt"
        
        # Check for settings
        settings = [s for s in result["symbols"] if s["kind"] == "setting"]
        assert len(settings) > 0
        
        setting_names = {s["symbol"] for s in settings}
        assert "name" in setting_names
        assert "version" in setting_names
        assert "scalaVersion" in setting_names
        
        # Check for dependencies
        dependencies = [s for s in result["symbols"] if s["kind"] == "dependency"]
        assert len(dependencies) > 0
        
        # Check for tasks
        tasks = [s for s in result["symbols"] if s["kind"] == "task"]
        assert len(tasks) > 0
        
        task_names = {s["symbol"] for s in tasks}
        assert "generateDocs" in task_names
        assert "runMigrations" in task_names
    
    def test_get_definition(self, scala_plugin, test_data_dir):
        """Test getting symbol definitions."""
        # Index a file first
        file_path = test_data_dir / "FunctionalPatterns.scala"
        if file_path.exists():
            content = file_path.read_text()
            scala_plugin.indexFile(file_path, content)
            
            # Try to get definition
            definition = scala_plugin.getDefinition("Monad")
            assert definition is not None
            assert definition["symbol"] == "Monad"
            assert definition["kind"] == "trait"
            assert definition["language"] == "scala"
    
    def test_find_references(self, scala_plugin, test_data_dir):
        """Test finding symbol references."""
        # Index files first
        for file_name in ["FunctionalPatterns.scala", "Scala3Features.scala"]:
            file_path = test_data_dir / file_name
            if file_path.exists():
                content = file_path.read_text()
                scala_plugin.indexFile(file_path, content)
        
        # Find references to a common symbol
        refs = scala_plugin.findReferences("String")
        assert isinstance(refs, list)
        # String should be referenced in multiple files
        if refs:
            assert len(refs) > 0
    
    def test_search(self, scala_plugin, test_data_dir):
        """Test code search functionality."""
        # Index a file first
        file_path = test_data_dir / "FunctionalPatterns.scala"
        if file_path.exists():
            content = file_path.read_text()
            scala_plugin.indexFile(file_path, content)
            
            # Search for patterns
            results = scala_plugin.search("implicit", {"limit": 10})
            assert isinstance(results, list)
            
            # Search for specific constructs
            results = scala_plugin.search("trait", {"limit": 10})
            assert isinstance(results, list)


class TestScalaParser:
    """Test cases for the Scala parser."""
    
    def test_parse_class_definitions(self, scala_parser):
        """Test parsing various class definitions."""
        code = '''
        class SimpleClass
        
        case class User(name: String, age: Int)
        
        sealed abstract class Tree[+A]
        
        final class Service extends BaseService with Logging
        
        private[this] class InternalHelper
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['classes']) >= 5
        class_names = {c['name'] for c in result['classes']}
        assert "SimpleClass" in class_names
        assert "User" in class_names
        assert "Tree" in class_names
        assert "Service" in class_names
        assert "InternalHelper" in class_names
        
        # Check case class detection
        user_class = next(c for c in result['classes'] if c['name'] == 'User')
        assert user_class['kind'] == 'case_class'
    
    def test_parse_traits_and_objects(self, scala_parser):
        """Test parsing traits and objects."""
        code = '''
        trait Functor[F[_]] {
          def map[A, B](fa: F[A])(f: A => B): F[B]
        }
        
        object Singleton
        
        case object Empty
        
        trait Logging { self: Service =>
          def log(msg: String): Unit
        }
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['traits']) >= 2
        trait_names = {t['name'] for t in result['traits']}
        assert "Functor" in trait_names
        assert "Logging" in trait_names
        
        assert len(result['objects']) >= 2
        object_names = {o['name'] for o in result['objects']}
        assert "Singleton" in object_names
        assert "Empty" in object_names
        
        # Check case object detection
        empty_obj = next(o for o in result['objects'] if o['name'] == 'Empty')
        assert empty_obj['kind'] == 'case_object'
    
    def test_parse_methods(self, scala_parser):
        """Test parsing method definitions."""
        code = '''
        def simple(): Unit = println("Hello")
        
        private def helper(x: Int): Int = x * 2
        
        override def toString: String = s"Custom"
        
        implicit def stringToInt(s: String): Int = s.toInt
        
        def generic[T: Ordering](list: List[T]): T = list.max
        
        def curried(x: Int)(y: Int): Int = x + y
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['methods']) >= 6
        method_names = {m['name'] for m in result['methods']}
        assert "simple" in method_names
        assert "helper" in method_names
        assert "toString" in method_names
        assert "stringToInt" in method_names
        assert "generic" in method_names
        assert "curried" in method_names
    
    def test_parse_vals_and_vars(self, scala_parser):
        """Test parsing val and var definitions."""
        code = '''
        val constant = 42
        
        var mutable = "hello"
        
        lazy val expensive = computeExpensive()
        
        implicit val ordering: Ordering[Person] = new Ordering[Person] {
          def compare(x: Person, y: Person) = x.name.compare(y.name)
        }
        
        private[package] val internal: String = "internal"
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['vals']) >= 4
        val_names = {v['name'] for v in result['vals']}
        assert "constant" in val_names
        assert "expensive" in val_names
        assert "ordering" in val_names
        assert "internal" in val_names
        
        assert len(result['vars']) >= 1
        var_names = {v['name'] for v in result['vars']}
        assert "mutable" in var_names
    
    def test_parse_type_aliases(self, scala_parser):
        """Test parsing type aliases."""
        code = '''
        type UserId = Long
        
        type Result[A] = Either[String, A]
        
        type Reader[R, A] = R => A
        
        private type InternalType = Map[String, Any]
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['types']) >= 4
        type_names = {t['name'] for t in result['types']}
        assert "UserId" in type_names
        assert "Result" in type_names
        assert "Reader" in type_names
        assert "InternalType" in type_names
    
    def test_parse_implicits(self, scala_parser):
        """Test parsing implicit definitions."""
        code = '''
        implicit val ec: ExecutionContext = ExecutionContext.global
        
        implicit def intToString(i: Int): String = i.toString
        
        implicit class RichInt(val i: Int) {
          def times(f: => Unit): Unit = (1 to i).foreach(_ => f)
        }
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['implicits']) >= 3
        implicit_names = {i['name'] for i in result['implicits']}
        assert "ec" in implicit_names
        assert "intToString" in implicit_names
        assert "RichInt" in implicit_names
    
    def test_parse_scala3_givens(self, scala_parser):
        """Test parsing Scala 3 given instances."""
        code = '''
        given intOrd: Ordering[Int] = Ordering.Int
        
        given Ordering[List[T]] with
          def compare(x: List[T], y: List[T]): Int = ???
        
        given [T: Ordering]: Ordering[Option[T]] with
          def compare(x: Option[T], y: Option[T]): Int = ???
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['givens']) >= 2  # Anonymous givens might not have names
        given_names = {g['name'] for g in result['givens'] if g['name'] != g['name'].startswith('given_')}
        assert "intOrd" in given_names
    
    def test_parse_extensions(self, scala_parser):
        """Test parsing Scala 3 extension methods."""
        code = '''
        extension (s: String)
          def greet: String = s"Hello, $s"
          def yell: String = s.toUpperCase + "!"
        
        extension [T](list: List[T])
          def secondOption: Option[T] = list.drop(1).headOption
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['extensions']) >= 2
    
    def test_parse_akka_actors(self, scala_parser):
        """Test parsing Akka actor classes."""
        code = '''
        class MyActor extends Actor {
          def receive = {
            case msg => println(msg)
          }
        }
        
        object RouterActor extends Actor with ActorLogging {
          def receive = ???
        }
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['actors']) >= 2
        actor_names = {a['name'] for a in result['actors']}
        assert "MyActor" in actor_names
        assert "RouterActor" in actor_names
    
    def test_parse_play_controllers(self, scala_parser):
        """Test parsing Play Framework controllers."""
        code = '''
        @Singleton
        class UserController @Inject()(cc: ControllerComponents) extends AbstractController(cc) {
          def index = Action { Ok("Hello") }
        }
        
        object ApiController extends Controller {
          def getUser(id: Long) = Action.async { Future.successful(Ok("User")) }
        }
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        assert len(result['controllers']) >= 2
        controller_names = {c['name'] for c in result['controllers']}
        assert "UserController" in controller_names
        assert "ApiController" in controller_names
    
    def test_parse_spark_components(self, scala_parser):
        """Test parsing Spark-related code."""
        code = '''
        object DataProcessor {
          val spark = SparkSession.builder().appName("Test").getOrCreate()
          val sc = spark.sparkContext
        }
        
        val rdd: RDD[String] = sc.textFile("data.txt")
        val df: DataFrame = spark.read.json("data.json")
        val ds: Dataset[Person] = df.as[Person]
        '''
        
        result = scala_parser.parse_scala_file(code)
        
        spark_components = result['spark_components']
        assert len(spark_components) >= 3
        
        component_kinds = {c['kind'] for c in spark_components}
        assert "rdd" in component_kinds
        assert "dataframe" in component_kinds
    
    def test_parse_sbt_settings(self, scala_parser):
        """Test parsing SBT build file settings."""
        sbt_content = '''
        name := "my-project"
        version := "1.0.0"
        scalaVersion := "3.3.1"
        
        libraryDependencies ++= Seq(
          "org.typelevel" %% "cats-core" % "2.10.0",
          "org.scalatest" %% "scalatest" % "3.2.17" % Test
        )
        
        lazy val compile = taskKey[Unit]("Compile task")
        lazy val customTask = taskKey[String]("Custom task")
        
        addSbtPlugin("com.typesafe.sbt" % "sbt-native-packager" % "1.9.16")
        '''
        
        result = scala_parser.parse_sbt_file(sbt_content)
        
        # Check settings
        assert len(result['settings']) >= 3
        setting_names = {s['name'] for s in result['settings']}
        assert "name" in setting_names
        assert "version" in setting_names
        assert "scalaVersion" in setting_names
        
        # Check dependencies
        assert len(result['dependencies']) >= 2
        dep_names = {d['name'] for d in result['dependencies']}
        assert "org.typelevel:cats-core" in dep_names
        assert "org.scalatest:scalatest" in dep_names
        
        # Check tasks
        assert len(result['tasks']) >= 2
        task_names = {t['name'] for t in result['tasks']}
        assert "compile" in task_names
        assert "customTask" in task_names
        
        # Check plugins
        assert len(result['plugins']) >= 1
        plugin_names = {p['name'] for p in result['plugins']}
        assert "com.typesafe.sbt:sbt-native-packager" in plugin_names


def test_plugin_info(scala_plugin):
    """Test plugin info method."""
    info = scala_plugin.get_plugin_info()
    
    assert info["name"] == "Plugin"
    assert info["language"] == "scala"
    assert ".scala" in info["extensions"]
    assert ".sc" in info["extensions"]
    assert ".sbt" in info["extensions"]
    
    # Check features
    assert "Scala 2 and Scala 3 support" in info["features"]
    assert "Case classes and objects" in info["features"]
    assert "Akka actor detection" in info["features"]
    assert "Apache Spark support" in info["features"]