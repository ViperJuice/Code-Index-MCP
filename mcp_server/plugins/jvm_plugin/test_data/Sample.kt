package com.example.test

import kotlinx.coroutines.*
import kotlin.collections.mutableListOf

/**
 * Sample Kotlin class for testing JVM plugin.
 */
@Service
@Component("kotlinSample")
data class KotlinSample<T : Comparable<T>>(
    val name: String,
    var items: MutableList<T> = mutableListOf()
) : Runnable {
    
    companion object {
        const val CONSTANT = "Kotlin Hello World"
        
        @JvmStatic
        fun <T : Comparable<T>> create(name: String): KotlinSample<T> {
            return KotlinSample(name)
        }
    }
    
    private var _running: Boolean = false
    val isRunning: Boolean get() = _running
    
    lateinit var callback: (String) -> Unit
    
    override fun run() {
        _running = true
        println("Running Kotlin sample process...")
    }
    
    suspend fun processAsync(data: String): String = withContext(Dispatchers.IO) {
        delay(100)
        "Processed: $data"
    }
    
    inline fun <reified R> genericMethod(crossinline action: () -> R): R {
        return action()
    }
    
    operator fun plus(other: KotlinSample<T>): KotlinSample<T> {
        val combined = KotlinSample<T>(this.name + " + " + other.name)
        combined.items.addAll(this.items)
        combined.items.addAll(other.items)
        return combined
    }
    
    infix fun mergeWith(other: KotlinSample<T>): KotlinSample<T> = this + other
}

/**
 * Extension functions for String.
 */
fun String.isPalindrome(): Boolean {
    val clean = this.lowercase().replace(Regex("[^a-z0-9]"), "")
    return clean == clean.reversed()
}

fun <T> List<T>.safeGet(index: Int): T? = 
    if (index in 0 until size) this[index] else null

/**
 * Sealed class hierarchy.
 */
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val exception: Throwable) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

/**
 * Object singleton.
 */
object DatabaseManager {
    private val connections = mutableMapOf<String, Any>()
    
    fun getConnection(name: String): Any? = connections[name]
    
    fun addConnection(name: String, connection: Any) {
        connections[name] = connection
    }
}

/**
 * Interface with default implementations.
 */
interface Repository<T> {
    suspend fun findAll(): List<T>
    suspend fun findById(id: String): T?
    suspend fun save(entity: T): T
    
    fun validate(entity: T): Boolean = true
}

/**
 * Abstract class.
 */
abstract class BaseService<T> : Repository<T> {
    protected abstract val dao: Repository<T>
    
    override suspend fun findAll(): List<T> = dao.findAll()
    
    override suspend fun findById(id: String): T? = dao.findById(id)
    
    override suspend fun save(entity: T): T {
        require(validate(entity)) { "Invalid entity" }
        return dao.save(entity)
    }
}

/**
 * Enum class with properties.
 */
enum class HttpStatus(val code: Int, val message: String) {
    OK(200, "OK"),
    NOT_FOUND(404, "Not Found"),
    SERVER_ERROR(500, "Internal Server Error");
    
    companion object {
        fun fromCode(code: Int): HttpStatus? = values().find { it.code == code }
    }
}

/**
 * Annotation class.
 */
@Target(AnnotationTarget.CLASS, AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class ApiEndpoint(
    val path: String,
    val method: String = "GET",
    val description: String = ""
)