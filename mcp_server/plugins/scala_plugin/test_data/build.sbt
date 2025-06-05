// Project metadata
name := "scala-plugin-test"
version := "1.0.0"
scalaVersion := "3.3.1"

// Cross-building for Scala 2.13
crossScalaVersions := Seq("2.13.12", "3.3.1")

// Organization
organization := "com.example"
organizationName := "Example Corp"
organizationHomepage := Some(url("https://example.com"))

// Scala compiler options
scalacOptions ++= Seq(
  "-deprecation",
  "-encoding", "UTF-8",
  "-feature",
  "-language:existentials",
  "-language:higherKinds",
  "-language:implicitConversions",
  "-unchecked",
  "-Xfatal-warnings",
  "-Xlint",
  "-Ywarn-dead-code",
  "-Ywarn-numeric-widen",
  "-Ywarn-value-discard"
)

// Scala 3 specific options
scalacOptions ++= {
  if (scalaVersion.value.startsWith("3.")) Seq(
    "-Ykind-projector",
    "-Xmax-inlines", "64"
  ) else Seq.empty
}

// Dependencies
val akkaVersion = "2.8.5"
val playVersion = "2.9.0"
val sparkVersion = "3.5.0"
val scalaTestVersion = "3.2.17"

libraryDependencies ++= Seq(
  // Akka
  "com.typesafe.akka" %% "akka-actor" % akkaVersion,
  "com.typesafe.akka" %% "akka-stream" % akkaVersion,
  "com.typesafe.akka" %% "akka-testkit" % akkaVersion % Test,
  
  // Play Framework
  "com.typesafe.play" %% "play" % playVersion,
  "com.typesafe.play" %% "play-json" % "2.10.0",
  "com.typesafe.play" %% "play-ws" % playVersion,
  
  // Apache Spark
  "org.apache.spark" %% "spark-core" % sparkVersion % Provided,
  "org.apache.spark" %% "spark-sql" % sparkVersion % Provided,
  "org.apache.spark" %% "spark-mllib" % sparkVersion % Provided,
  "org.apache.spark" %% "spark-streaming" % sparkVersion % Provided,
  
  // Cats and Cats Effect
  "org.typelevel" %% "cats-core" % "2.10.0",
  "org.typelevel" %% "cats-effect" % "3.5.2",
  
  // HTTP4s
  "org.http4s" %% "http4s-blaze-server" % "0.23.15",
  "org.http4s" %% "http4s-circe" % "0.23.15",
  "org.http4s" %% "http4s-dsl" % "0.23.15",
  
  // Database
  "org.postgresql" % "postgresql" % "42.6.0",
  "com.typesafe.slick" %% "slick" % "3.4.1",
  "com.typesafe.slick" %% "slick-hikaricp" % "3.4.1",
  
  // JSON
  "io.circe" %% "circe-core" % "0.14.6",
  "io.circe" %% "circe-generic" % "0.14.6",
  "io.circe" %% "circe-parser" % "0.14.6",
  
  // Testing
  "org.scalatest" %% "scalatest" % scalaTestVersion % Test,
  "org.scalamock" %% "scalamock" % "5.2.0" % Test,
  "org.scalacheck" %% "scalacheck" % "1.17.0" % Test
)

// Resolver for additional repositories
resolvers ++= Seq(
  "Typesafe Repository" at "https://repo.typesafe.com/typesafe/releases/",
  "Sonatype OSS Snapshots" at "https://oss.sonatype.org/content/repositories/snapshots",
  Resolver.sonatypeRepo("releases")
)

// Assembly plugin settings
assembly / assemblyMergeStrategy := {
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case "reference.conf" => MergeStrategy.concat
  case x => MergeStrategy.first
}

// Custom tasks
lazy val generateDocs = taskKey[Unit]("Generate project documentation")
generateDocs := {
  println("Generating documentation...")
  // Documentation generation logic
}

lazy val runMigrations = taskKey[Unit]("Run database migrations")
runMigrations := {
  println("Running migrations...")
  // Migration logic
}

// Test settings
Test / parallelExecution := false
Test / testOptions += Tests.Argument("-oD")

// Coverage settings
coverageEnabled := true
coverageMinimumStmtTotal := 80
coverageFailOnMinimum := true

// Publishing settings
publishTo := {
  val nexus = "https://nexus.example.com/"
  if (isSnapshot.value)
    Some("snapshots" at nexus + "content/repositories/snapshots")
  else
    Some("releases" at nexus + "content/repositories/releases")
}

publishMavenStyle := true
publishArtifact in Test := false

// Docker settings
enablePlugins(DockerPlugin)
Docker / packageName := "scala-example"
Docker / version := version.value
Docker / maintainer := "dev@example.com"

// JVM options
javaOptions ++= Seq(
  "-Xmx2g",
  "-XX:+UseG1GC",
  "-XX:MaxGCPauseMillis=200"
)

// Project structure
lazy val root = (project in file("."))
  .aggregate(core, api, spark)
  .settings(
    publish := {},
    publishLocal := {}
  )

lazy val core = (project in file("core"))
  .settings(
    name := "core",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.10.0"
    )
  )

lazy val api = (project in file("api"))
  .dependsOn(core)
  .settings(
    name := "api",
    libraryDependencies ++= Seq(
      "com.typesafe.play" %% "play" % playVersion
    )
  )

lazy val spark = (project in file("spark"))
  .dependsOn(core)
  .settings(
    name := "spark-jobs",
    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-core" % sparkVersion % Provided
    )
  )

// SBT plugins
addSbtPlugin("com.typesafe.sbt" % "sbt-native-packager" % "1.9.16")
addSbtPlugin("org.scoverage" % "sbt-scoverage" % "2.0.9")
addSbtPlugin("com.eed3si9n" % "sbt-assembly" % "2.1.3")
addSbtPlugin("ch.epfl.scala" % "sbt-scalafix" % "0.11.1")
addSbtPlugin("org.scalameta" % "sbt-scalafmt" % "2.5.2")