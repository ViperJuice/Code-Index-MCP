# JVM Plugin - AI Agent Configuration

> **AI Agents:** This file contains JVM plugin-specific instructions. Always check root `AGENTS.md` first.

## Essential Commands

```bash
# Test JVM plugin functionality
pytest tests/test_jvm_plugin.py -v

# Debug Java parsing
python -m mcp_server.plugins.jvm_plugin.plugin debug Sample.java

# Debug Kotlin parsing  
python -m mcp_server.plugins.jvm_plugin.plugin debug Sample.kt

# Verify build file parsing
python -m mcp_server.plugins.jvm_plugin.plugin analyze pom.xml
```

## Code Style Preferences

### Java Patterns
```java
// Preferred: Clear class structure
public class UserService {
    private final UserRepository repository;
    
    @Autowired
    public UserService(UserRepository repository) {
        this.repository = repository;
    }
    
    @Transactional
    public User findById(Long id) {
        return repository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
    }
}
```

### Kotlin Patterns
```kotlin
// Preferred: Idiomatic Kotlin
class UserService @Autowired constructor(
    private val repository: UserRepository
) {
    @Transactional
    fun findById(id: Long): User = 
        repository.findById(id) ?: throw UserNotFoundException(id)
}
```

## Parser Implementation Details

### Symbol Extraction
- **Classes**: Public, private, abstract, interface
- **Methods**: All visibility levels, annotations preserved
- **Fields**: Constants, properties, injected dependencies
- **Annotations**: Spring, JPA, custom annotations
- **Generics**: Type parameters and bounds
- **Build Files**: Maven (pom.xml), Gradle (build.gradle/kts)

### Framework Detection
1. **Spring Framework**
   - `@SpringBootApplication`, `@RestController`, `@Service`
   - Bean definitions and dependency injection
   
2. **JPA/Hibernate**
   - `@Entity`, `@Repository`, `@Query`
   - Relationship mappings

3. **Android**
   - Activities, Fragments, ViewModels
   - Resource references

### Performance Targets
- Parse time: <5ms per file (currently achieving ~3ms)
- Memory usage: <50MB for 10k files
- Supports: Java 8+, Kotlin 1.0+

## Common Issues

### Annotation Processing
```python
# If annotations aren't detected, check:
# 1. Regex patterns in JAVA_ANNOTATION_PATTERN
# 2. Import statements are being tracked
# 3. Multi-line annotations are handled
```

### Generic Type Parsing
```python
# Complex generics may need special handling:
# Map<String, List<? extends BaseClass>>
# Ensure GENERIC_PATTERN captures nested types
```

## Testing Checklist

- [ ] Java class parsing (simple and complex)
- [ ] Kotlin class parsing (data classes, sealed classes)
- [ ] Interface and abstract class detection
- [ ] Annotation extraction
- [ ] Generic type handling
- [ ] Build file parsing (Maven/Gradle)
- [ ] Spring framework patterns
- [ ] Android patterns (if applicable)

## Integration Notes

The JVM plugin integrates with:
- **Build Systems**: Extracts dependencies from pom.xml/build.gradle
- **IDE Features**: Supports go-to-definition, find references
- **Framework Analysis**: Detects Spring, JPA, Android patterns

## Future Enhancements

1. **Advanced Type Resolution**
   - Full generic type inference
   - Lambda expression parsing
   - Method reference detection

2. **Build System Integration**
   - Dependency tree analysis
   - Multi-module project support
   - Gradle Kotlin DSL support

3. **Framework-Specific Features**
   - Spring Boot configuration analysis
   - JPA query validation
   - Android resource linking

## Performance Optimization

For large Java/Kotlin codebases:
```bash
# Enable parallel parsing
export JVM_PARSER_THREADS=4

# Increase cache size for build files
export BUILD_FILE_CACHE_SIZE=1000

# Skip test files if needed
export SKIP_TEST_FILES=true
```

---
*Plugin maintained by Phase 5 Track 1 Team*