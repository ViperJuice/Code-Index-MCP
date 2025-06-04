# PHP Plugin - AI Agent Configuration

> **AI Agents:** This file contains PHP plugin-specific instructions. Always check root `AGENTS.md` first.

## Essential Commands

```bash
# Test PHP plugin functionality
pytest tests/test_php_plugin.py -v

# Debug PHP parsing
python -m mcp_server.plugins.php_plugin.plugin debug UserController.php

# Analyze Laravel project
python -m mcp_server.plugins.php_plugin.plugin analyze app/

# Check Composer dependencies
python -m mcp_server.plugins.php_plugin.plugin deps composer.json
```

## Code Style Preferences

### Modern PHP Patterns
```php
<?php
declare(strict_types=1);

namespace App\Services;

use App\Models\User;
use App\Contracts\UserServiceInterface;
use Illuminate\Support\Facades\DB;

final class UserService implements UserServiceInterface
{
    public function __construct(
        private readonly UserRepository $repository,
        private readonly CacheService $cache
    ) {}
    
    public function findById(int $id): ?User
    {
        return $this->cache->remember(
            "user.{$id}",
            fn() => $this->repository->find($id)
        );
    }
}
```

## Parser Implementation Details

### Symbol Extraction
- **Classes**: Regular, abstract, final, anonymous
- **Interfaces**: With extends support
- **Traits**: Including trait usage
- **Methods**: All visibility levels, static, abstract
- **Properties**: Typed properties, visibility modifiers
- **Constants**: Class and global constants
- **Functions**: Global functions and closures
- **Namespaces**: Full namespace tracking

### Framework Detection

1. **Laravel**
   - Eloquent models (`extends Model`)
   - Controllers (`extends Controller`)
   - Middleware patterns
   - Service providers
   
2. **Symfony**
   - Controllers with annotations/attributes
   - Entity classes
   - Service definitions

3. **WordPress**
   - Hook/filter registration
   - Plugin structure

### PSR Standards
- PSR-4 autoloading awareness
- PSR-12 coding style support
- PSR-7 HTTP message interfaces

### Performance Metrics
- Parse time: <1ms per file (achieving ~0.37ms)
- Memory efficient: <30MB for 10k files
- PHP version support: 7.4+

## Common Issues

### Namespace Resolution
```python
# For proper namespace handling:
# 1. Track 'use' statements
# 2. Build fully qualified names
# 3. Handle group use declarations
```

### Trait Analysis
```python
# Traits require special handling:
# 1. Track trait usage in classes
# 2. Consider trait precedence
# 3. Handle trait aliases
```

### Anonymous Classes
```php
// Parser handles inline classes:
$handler = new class implements HandlerInterface {
    public function handle($request) {}
};
```

## Testing Checklist

- [x] Basic class/interface/trait parsing
- [x] Method extraction with visibility
- [x] Property and constant detection
- [x] Namespace and use statement tracking
- [x] Laravel pattern recognition
- [x] PHPDoc comment extraction
- [x] Abstract and final modifiers
- [x] Static method detection

## Integration Notes

The PHP plugin integrates with:
- **Composer**: Reads composer.json for dependencies
- **Autoloading**: PSR-4 namespace resolution
- **Frameworks**: Laravel, Symfony pattern detection
- **Documentation**: PHPDoc parsing for intellisense

## Framework-Specific Features

### Laravel Projects
```bash
# Optimized parsing for Laravel structure
export PHP_FRAMEWORK=laravel

# Common Laravel paths
# app/Models/
# app/Http/Controllers/
# app/Services/
```

### Symfony Projects
```bash
# Symfony-specific patterns
export PHP_FRAMEWORK=symfony

# Common Symfony paths
# src/Controller/
# src/Entity/
# src/Service/
```

## Performance Optimization

For large PHP codebases:
```bash
# Skip vendor directory
export PHP_SKIP_VENDOR=true

# Enable caching for parsed files
export PHP_PARSER_CACHE=true

# Parallel parsing for frameworks
export PHP_PARALLEL_PARSE=true
```

## Code Quality Patterns

### Detected Anti-patterns
- God classes (>500 lines)
- Deep inheritance (>3 levels)
- Circular dependencies

### Best Practices Encouraged
- Dependency injection
- Interface-based design
- Single responsibility
- Type declarations

## Future Enhancements

1. **Advanced Type Analysis**
   - Union and intersection types
   - Generic annotations via PHPDoc
   - Static analysis integration

2. **Framework Deep Integration**
   - Laravel route analysis
   - Symfony service container
   - Doctrine mapping analysis

3. **Modern PHP Features**
   - Enums (PHP 8.1+)
   - Readonly properties
   - Constructor property promotion

---
*Plugin completed by Developer 4 - Production Ready*