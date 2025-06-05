package com.example.spark

import org.apache.spark.sql.{SparkSession, DataFrame, Dataset, Row}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.ml.feature.{VectorAssembler, StandardScaler}
import org.apache.spark.ml.classification.LogisticRegression
import org.apache.spark.ml.Pipeline
import org.apache.spark.rdd.RDD
import scala.concurrent.duration._

// Domain models
case class Transaction(
  id: String,
  userId: String,
  amount: Double,
  category: String,
  timestamp: Long,
  merchantId: String,
  location: String
)

case class UserProfile(
  userId: String,
  age: Int,
  income: Double,
  creditScore: Int,
  accountAge: Int
)

case class AggregatedMetrics(
  userId: String,
  totalTransactions: Long,
  totalAmount: Double,
  avgAmount: Double,
  categoryCount: Long,
  merchantCount: Long,
  riskScore: Double
)

// Main Spark application
object FraudDetectionJob {
  
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("FraudDetectionPipeline")
      .config("spark.sql.adaptive.enabled", "true")
      .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
      .getOrCreate()
    
    import spark.implicits._
    
    // Read data
    val transactions = loadTransactions(spark, args(0))
    val userProfiles = loadUserProfiles(spark, args(1))
    
    // Process and analyze
    val enrichedData = enrichTransactions(transactions, userProfiles)
    val features = extractFeatures(enrichedData)
    val predictions = detectFraud(features)
    
    // Save results
    saveResults(predictions, args(2))
    
    spark.stop()
  }
  
  def loadTransactions(spark: SparkSession, path: String): Dataset[Transaction] = {
    import spark.implicits._
    
    spark.read
      .option("header", "true")
      .option("inferSchema", "true")
      .csv(path)
      .as[Transaction]
      .filter($"amount" > 0)
      .cache()
  }
  
  def loadUserProfiles(spark: SparkSession, path: String): Dataset[UserProfile] = {
    import spark.implicits._
    
    spark.read
      .parquet(path)
      .as[UserProfile]
      .cache()
  }
  
  def enrichTransactions(
    transactions: Dataset[Transaction],
    profiles: Dataset[UserProfile]
  ): DataFrame = {
    import transactions.sparkSession.implicits._
    
    // Join transactions with user profiles
    val enriched = transactions
      .join(profiles, Seq("userId"), "left")
      .withColumn("hour", hour(from_unixtime($"timestamp")))
      .withColumn("dayOfWeek", dayofweek(from_unixtime($"timestamp")))
      .withColumn("isWeekend", when($"dayOfWeek".isin(1, 7), 1).otherwise(0))
    
    // Add time-based features
    enriched
      .withColumn("timeSinceLastTx", 
        $"timestamp" - lag("timestamp", 1).over(
          Window.partitionBy("userId").orderBy("timestamp")
        )
      )
      .withColumn("amountDeviation",
        abs($"amount" - avg("amount").over(
          Window.partitionBy("userId").rowsBetween(-10, -1)
        ))
      )
  }
  
  def extractFeatures(data: DataFrame): DataFrame = {
    import data.sparkSession.implicits._
    
    // Aggregate user behavior
    val userAggregates = data
      .groupBy("userId")
      .agg(
        count("id").as("txCount"),
        sum("amount").as("totalAmount"),
        avg("amount").as("avgAmount"),
        stddev("amount").as("stdAmount"),
        countDistinct("category").as("uniqueCategories"),
        countDistinct("merchantId").as("uniqueMerchants"),
        max("amount").as("maxAmount"),
        min("amount").as("minAmount")
      )
    
    // Category spending patterns
    val categoryPatterns = data
      .groupBy("userId", "category")
      .agg(
        count("*").as("categoryCount"),
        sum("amount").as("categoryAmount")
      )
      .groupBy("userId")
      .pivot("category")
      .agg(first("categoryAmount"))
      .na.fill(0)
    
    // Time-based patterns
    val timePatterns = data
      .groupBy("userId")
      .agg(
        sum(when($"hour" >= 0 && $"hour" < 6, 1).otherwise(0)).as("nightTransactions"),
        sum(when($"isWeekend" === 1, 1).otherwise(0)).as("weekendTransactions"),
        avg("timeSinceLastTx").as("avgTimeBetweenTx")
      )
    
    // Combine all features
    data
      .join(userAggregates, Seq("userId"))
      .join(categoryPatterns, Seq("userId"))
      .join(timePatterns, Seq("userId"))
      .select(
        $"userId",
        $"id",
        $"amount",
        $"age",
        $"income",
        $"creditScore",
        $"txCount",
        $"avgAmount",
        $"stdAmount",
        $"uniqueCategories",
        $"uniqueMerchants",
        $"nightTransactions",
        $"weekendTransactions",
        $"avgTimeBetweenTx"
      )
  }
  
  def detectFraud(features: DataFrame): DataFrame = {
    import features.sparkSession.implicits._
    
    // Prepare feature vector
    val featureCols = Array(
      "amount", "age", "income", "creditScore",
      "txCount", "avgAmount", "stdAmount",
      "uniqueCategories", "uniqueMerchants",
      "nightTransactions", "weekendTransactions"
    )
    
    val assembler = new VectorAssembler()
      .setInputCols(featureCols)
      .setOutputCol("rawFeatures")
    
    val scaler = new StandardScaler()
      .setInputCol("rawFeatures")
      .setOutputCol("features")
    
    // Rule-based fraud detection
    val ruleBasedFlags = features
      .withColumn("highAmountFlag", when($"amount" > $"avgAmount" * 3, 1).otherwise(0))
      .withColumn("frequencyFlag", when($"avgTimeBetweenTx" < 300, 1).otherwise(0))
      .withColumn("nightFlag", when($"hour" >= 0 && $"hour" < 6, 1).otherwise(0))
      .withColumn("riskScore", 
        $"highAmountFlag" * 0.4 + 
        $"frequencyFlag" * 0.3 + 
        $"nightFlag" * 0.3
      )
    
    // ML-based detection (if labeled data available)
    // val lr = new LogisticRegression()
    //   .setFeaturesCol("features")
    //   .setLabelCol("label")
    //   .setMaxIter(100)
    
    // val pipeline = new Pipeline()
    //   .setStages(Array(assembler, scaler, lr))
    
    // Return predictions with risk scores
    ruleBasedFlags
      .withColumn("isFraud", when($"riskScore" > 0.7, true).otherwise(false))
      .select(
        $"userId",
        $"id".as("transactionId"),
        $"amount",
        $"riskScore",
        $"isFraud",
        $"highAmountFlag",
        $"frequencyFlag",
        $"nightFlag"
      )
  }
  
  def saveResults(predictions: DataFrame, outputPath: String): Unit = {
    // Save detailed results
    predictions
      .coalesce(10)
      .write
      .mode("overwrite")
      .partitionBy("isFraud")
      .parquet(s"$outputPath/predictions")
    
    // Save summary statistics
    val summary = predictions
      .groupBy("isFraud")
      .agg(
        count("*").as("count"),
        avg("riskScore").as("avgRiskScore"),
        sum("amount").as("totalAmount")
      )
    
    summary
      .coalesce(1)
      .write
      .mode("overwrite")
      .json(s"$outputPath/summary")
  }
}

// Streaming job
object FraudDetectionStreaming {
  
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("FraudDetectionStreaming")
      .config("spark.sql.streaming.checkpointLocation", args(1))
      .getOrCreate()
    
    import spark.implicits._
    
    // Read streaming data from Kafka
    val transactions = spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", args(0))
      .option("subscribe", "transactions")
      .option("startingOffsets", "latest")
      .load()
      .select(
        from_json($"value".cast("string"), transactionSchema).as("data")
      )
      .select("data.*")
      .as[Transaction]
    
    // Apply windowed aggregations
    val windowedStats = transactions
      .withWatermark("timestamp", "10 minutes")
      .groupBy(
        window($"timestamp", "5 minutes", "1 minute"),
        $"userId"
      )
      .agg(
        count("*").as("txCount"),
        sum("amount").as("totalAmount"),
        avg("amount").as("avgAmount")
      )
    
    // Detect anomalies in real-time
    val anomalies = windowedStats
      .filter($"txCount" > 10 || $"avgAmount" > 1000)
      .select(
        $"window.start".as("windowStart"),
        $"window.end".as("windowEnd"),
        $"userId",
        $"txCount",
        $"totalAmount",
        $"avgAmount"
      )
    
    // Write results to multiple sinks
    val query = anomalies.writeStream
      .outputMode("append")
      .format("console")
      .trigger(Trigger.ProcessingTime("10 seconds"))
      .start()
    
    query.awaitTermination()
  }
  
  def transactionSchema: StructType = StructType(Seq(
    StructField("id", StringType, nullable = false),
    StructField("userId", StringType, nullable = false),
    StructField("amount", DoubleType, nullable = false),
    StructField("category", StringType, nullable = true),
    StructField("timestamp", LongType, nullable = false),
    StructField("merchantId", StringType, nullable = true),
    StructField("location", StringType, nullable = true)
  ))
}

// Custom aggregation function
class RiskScoreAggregator extends Aggregator[Transaction, RiskBuffer, Double] {
  
  def zero: RiskBuffer = RiskBuffer(0.0, 0L, 0.0, Set.empty)
  
  def reduce(buffer: RiskBuffer, transaction: Transaction): RiskBuffer = {
    buffer.copy(
      totalAmount = buffer.totalAmount + transaction.amount,
      count = buffer.count + 1,
      maxAmount = math.max(buffer.maxAmount, transaction.amount),
      merchants = buffer.merchants + transaction.merchantId
    )
  }
  
  def merge(b1: RiskBuffer, b2: RiskBuffer): RiskBuffer = {
    RiskBuffer(
      totalAmount = b1.totalAmount + b2.totalAmount,
      count = b1.count + b2.count,
      maxAmount = math.max(b1.maxAmount, b2.maxAmount),
      merchants = b1.merchants ++ b2.merchants
    )
  }
  
  def finish(buffer: RiskBuffer): Double = {
    val avgAmount = buffer.totalAmount / buffer.count
    val merchantDiversity = buffer.merchants.size.toDouble / buffer.count
    
    // Calculate risk score based on multiple factors
    val amountRisk = if (buffer.maxAmount > avgAmount * 5) 0.5 else 0.0
    val frequencyRisk = if (buffer.count > 20) 0.3 else 0.0
    val diversityRisk = if (merchantDiversity < 0.2) 0.2 else 0.0
    
    amountRisk + frequencyRisk + diversityRisk
  }
  
  def bufferEncoder: Encoder[RiskBuffer] = Encoders.product
  def outputEncoder: Encoder[Double] = Encoders.scalaDouble
}

case class RiskBuffer(
  totalAmount: Double,
  count: Long,
  maxAmount: Double,
  merchants: Set[String]
)