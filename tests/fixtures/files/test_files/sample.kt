package com.example.app

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

/**
 * Sample Kotlin file demonstrating various language features
 */
data class Person(
    val id: Long,
    val name: String?,
    val email: String
) {
    companion object {
        @JvmStatic
        fun createPerson(name: String): Person {
            return Person(0L, name, "default@example.com")
        }
    }
}

sealed class NetworkResult<out T> {
    data class Success<T>(val data: T) : NetworkResult<T>()
    data class Error(val exception: Throwable) : NetworkResult<Nothing>()
    object Loading : NetworkResult<Nothing>()
}

class PersonRepository {
    private val _persons = MutableStateFlow<List<Person>>(emptyList())
    val persons: StateFlow<List<Person>> = _persons.asStateFlow()
    
    suspend fun fetchPerson(id: Long): NetworkResult<Person?> = withContext(Dispatchers.IO) {
        delay(500) // Simulate network delay
        
        try {
            val person = _persons.value.find { it.id == id }
            NetworkResult.Success(person)
        } catch (e: Exception) {
            NetworkResult.Error(e)
        }
    }
    
    suspend fun savePersons(persons: List<Person>) {
        _persons.value = persons
    }
}

// Extension functions
fun Person.isValid(): Boolean {
    return name?.isNotEmpty() == true && email.isNotEmpty()
}

fun String?.orDefault(default: String = "Unknown"): String {
    return this ?: default
}

// Scope functions and null safety
class PersonService(private val repository: PersonRepository) {
    
    suspend fun getPersonDetails(id: Long): String? {
        return repository.fetchPerson(id).let { result ->
            when (result) {
                is NetworkResult.Success -> {
                    result.data?.let { person ->
                        "Name: ${person.name.orDefault()}, Email: ${person.email}"
                    }
                }
                is NetworkResult.Error -> {
                    "Error: ${result.exception.message}"
                }
                is NetworkResult.Loading -> {
                    "Loading..."
                }
            }
        }
    }
    
    // Null safety demonstration
    fun processPersonSafely(person: Person?) {
        // Safe call
        val name = person?.name
        
        // Elvis operator
        val displayName = name ?: "Anonymous"
        
        // Safe cast
        val personAsString = person as? String
        
        // Let scope function with null check
        person?.let { validPerson ->
            println("Processing: ${validPerson.name}")
            
            // Also scope function
            validPerson.also { p ->
                println("Email: ${p.email}")
            }
        }
        
        // Run scope function
        person?.run {
            if (isValid()) {
                println("Valid person: $name")
            }
        }
    }
    
    // Potentially risky operations
    fun riskyOperations(person: Person?) {
        // Not-null assertion (risky!)
        val length = person!!.name!!.length
        
        // Unsafe cast
        val stringPerson = person as String
    }
}

// Coroutines and Flow
class PersonFlow {
    private val repository = PersonRepository()
    
    fun getPersonStream(): Flow<List<Person>> = flow {
        while (true) {
            emit(repository.persons.value)
            delay(1000)
        }
    }.flowOn(Dispatchers.IO)
    
    suspend fun processPersonsBatch(): List<Person> = coroutineScope {
        val personIds = listOf(1L, 2L, 3L, 4L, 5L)
        
        personIds.map { id ->
            async(Dispatchers.IO) {
                when (val result = repository.fetchPerson(id)) {
                    is NetworkResult.Success -> result.data
                    else -> null
                }
            }
        }.awaitAll().filterNotNull()
    }
}

// Java interoperability examples
object JavaInterop {
    
    @JvmStatic
    @JvmOverloads
    fun createPersonFromJava(name: String, email: String = "default@example.com"): Person {
        return Person(0L, name, email)
    }
    
    // Java collections vs Kotlin collections
    fun demonstrateCollections() {
        // Java collections
        val javaList = ArrayList<Person>()
        val javaMap = HashMap<Long, Person>()
        val javaSet = HashSet<Person>()
        
        // Kotlin collections
        val kotlinList = listOf<Person>()
        val kotlinMap = mapOf<Long, Person>()
        val kotlinSet = setOf<Person>()
        
        // Mixed usage
        javaList.addAll(kotlinList)
    }
    
    @Throws(IllegalArgumentException::class)
    fun validatePerson(person: Person) {
        requireNotNull(person.name) { "Name cannot be null" }
        require(person.email.isNotEmpty()) { "Email cannot be empty" }
    }
}

// Advanced Kotlin features
inline fun <T> measureTime(block: () -> T): Pair<T, Long> {
    val start = System.currentTimeMillis()
    val result = block()
    val time = System.currentTimeMillis() - start
    return result to time
}

inline class PersonId(val value: Long)

@JvmInline
value class Email(val value: String) {
    init {
        require(value.contains("@")) { "Invalid email format" }
    }
}