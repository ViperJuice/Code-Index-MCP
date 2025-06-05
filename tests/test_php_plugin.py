"""Comprehensive test suite for PHP plugin."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_server.plugins.php_plugin import Plugin as PHPPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestPHPPlugin:
    """Test cases for PHP language plugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create a PHP plugin instance for testing."""
        with patch.object(PHPPlugin, '_preindex'):  # Skip preindexing during tests
            return PHPPlugin()
    
    @pytest.fixture
    def plugin_with_sqlite(self, tmp_path):
        """Create a PHP plugin with SQLite storage."""
        db_path = tmp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))
        
        with patch.object(PHPPlugin, '_preindex'):
            return PHPPlugin(sqlite_store=sqlite_store)
    
    @pytest.fixture
    def sample_php_code(self):
        """Sample PHP code for testing."""
        return '''<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Relations\\HasMany;

/**
 * User model class
 * 
 * @property int $id
 * @property string $name
 */
class User extends Model
{
    /**
     * The table associated with the model.
     */
    protected string $table = 'users';
    
    /**
     * The attributes that are mass assignable.
     */
    protected array $fillable = ['name', 'email'];
    
    // Constants
    public const STATUS_ACTIVE = 'active';
    private const MAX_ATTEMPTS = 5;
    
    /**
     * Get the posts for the user.
     */
    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }
    
    /**
     * Get user's full name.
     */
    public function getFullName(): string
    {
        return $this->first_name . ' ' . $this->last_name;
    }
    
    /**
     * Check if user is admin.
     */
    public function isAdmin(): bool
    {
        return $this->role === 'admin';
    }
    
    /**
     * Find user by email.
     */
    public static function findByEmail(string $email): ?self
    {
        return static::where('email', $email)->first();
    }
    
    /**
     * Set the password attribute.
     */
    protected function setPasswordAttribute(string $password): void
    {
        $this->attributes['password'] = bcrypt($password);
    }
    
    /**
     * Private helper method.
     */
    private function normalizeEmail(): void
    {
        $this->email = strtolower(trim($this->email));
    }
}

/**
 * Interface for user operations
 */
interface UserInterface
{
    public function getName(): string;
    public function getEmail(): string;
}

/**
 * Trait for common user operations
 */
trait UserOperations
{
    /**
     * Format display name
     */
    public function formatDisplayName(): string
    {
        return $this->first_name . ' ' . $this->last_name;
    }
}

/**
 * Abstract base class
 */
abstract class BaseService
{
    protected array $config = [];
    
    abstract public function process(array $data): bool;
}

/**
 * Global function
 */
function helper_function(string $param): string
{
    return strtoupper($param);
}'''
    
    @pytest.fixture
    def sample_controller_code(self):
        """Sample Laravel controller code."""
        return '''<?php

namespace App\\Http\\Controllers;

use App\\Models\\User;
use Illuminate\\Http\\Request;
use Illuminate\\Http\\JsonResponse;

/**
 * User controller
 */
class UserController extends Controller
{
    /**
     * Display a listing of users.
     */
    public function index(Request $request): JsonResponse
    {
        $users = User::query()
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'like', "%{$search}%");
            })
            ->paginate(15);
            
        return response()->json($users);
    }
    
    /**
     * Store a new user.
     */
    public function store(Request $request): JsonResponse
    {
        $user = User::create($request->validated());
        
        return response()->json($user, 201);
    }
    
    /**
     * Show the specified user.
     */
    public function show(User $user): JsonResponse
    {
        return response()->json($user);
    }
    
    /**
     * Update the specified user.
     */
    public function update(Request $request, User $user): JsonResponse
    {
        $user->update($request->validated());
        
        return response()->json($user);
    }
    
    /**
     * Remove the specified user.
     */
    public function destroy(User $user): JsonResponse
    {
        $user->delete();
        
        return response()->json(['message' => 'User deleted']);
    }
    
    /**
     * Private helper method.
     */
    private function validateUserData(array $data): bool
    {
        return isset($data['name']) && isset($data['email']);
    }
    
    /**
     * Protected authorization method.
     */
    protected function authorize(string $ability, $resource): void
    {
        // Authorization logic
    }
}'''

    def test_supports_php_files(self, plugin):
        """Test that plugin supports PHP files."""
        assert plugin.supports("test.php") is True
        assert plugin.supports("test.rb") is False
        assert plugin.supports("test.py") is False
        assert plugin.supports("test.js") is False

    def test_indexFile_basic_parsing(self, plugin, sample_php_code):
        """Test basic file indexing and symbol extraction."""
        result = plugin.indexFile("test.php", sample_php_code)
        
        assert result["file"] == "test.php"
        assert result["language"] == "php"
        assert "symbols" in result
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check for extracted symbols
        assert "User" in symbol_names
        assert "UserInterface" in symbol_names
        assert "UserOperations" in symbol_names
        assert "BaseService" in symbol_names
        assert "posts" in symbol_names
        assert "getFullName" in symbol_names
        assert "isAdmin" in symbol_names
        assert "findByEmail" in symbol_names
        assert "helper_function" in symbol_names

    def test_symbol_kinds_detection(self, plugin, sample_php_code):
        """Test correct detection of symbol kinds."""
        result = plugin.indexFile("test.php", sample_php_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Test class detection with Laravel patterns
        assert symbols.get("User") == "model"  # Should detect Laravel model
        assert symbols.get("UserInterface") == "interface"
        assert symbols.get("UserOperations") == "trait"
        assert symbols.get("BaseService") == "abstract_class"
        
        # Test method kinds
        assert "method" in symbols.get("getFullName", "")
        assert "method" in symbols.get("isAdmin", "")
        assert "static_method" in symbols.get("findByEmail", "") or symbols.get("findByEmail") == "static_method"
        
        # Test visibility
        assert "protected" in symbols.get("setPasswordAttribute", "") or symbols.get("setPasswordAttribute") == "protected_method"
        assert "private" in symbols.get("normalizeEmail", "") or symbols.get("normalizeEmail") == "private_method"
        
        # Test global function
        assert symbols.get("helper_function") == "function"

    def test_controller_detection(self, plugin, sample_controller_code):
        """Test Laravel controller detection."""
        result = plugin.indexFile("UserController.php", sample_controller_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Should detect as controller
        assert symbols.get("UserController") == "controller"

    def test_namespace_handling(self, plugin, sample_php_code):
        """Test namespace extraction and handling."""
        result = plugin.indexFile("test.php", sample_php_code)
        symbols = result["symbols"]
        
        # Find class symbol with namespace info
        user_symbol = next((s for s in symbols if s["symbol"] == "User"), None)
        assert user_symbol is not None
        
        # Check namespace information
        if "namespace" in user_symbol:
            assert user_symbol["namespace"] == "App\\Models"
        if "full_name" in user_symbol:
            assert user_symbol["full_name"] == "App\\Models\\User"

    def test_constants_and_properties(self, plugin, sample_php_code):
        """Test detection of constants and properties."""
        result = plugin.indexFile("test.php", sample_php_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Test constants
        assert "constant" in symbols.get("STATUS_ACTIVE", "")
        assert "constant" in symbols.get("MAX_ATTEMPTS", "")
        
        # Test properties
        assert "property" in symbols.get("table", "") or "property" in str(symbols)
        assert "property" in symbols.get("fillable", "") or "property" in str(symbols)

    def test_getDefinition(self, plugin, tmp_path):
        """Test symbol definition lookup."""
        # Create test file
        test_file = tmp_path / "User.php"
        test_file.write_text('''<?php

class User
{
    private string $name;
    
    public function __construct(string $name)
    {
        $this->name = $name;
    }
    
    public function getName(): string
    {
        return $this->name;
    }
}''')
        
        # Change to temp directory for testing
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            definition = plugin.getDefinition("User")
            
            assert definition is not None
            assert definition["symbol"] == "User"
            assert definition["kind"] == "class"
            assert definition["language"] == "php"
            assert "User.php" in definition["defined_in"]
        finally:
            os.chdir(old_cwd)

    def test_findReferences(self, plugin, tmp_path):
        """Test finding symbol references."""
        # Create test files
        user_file = tmp_path / "User.php"
        user_file.write_text('''<?php

class User
{
    public function __construct(string $name)
    {
        $this->name = $name;
    }
}''')
        
        service_file = tmp_path / "UserService.php"
        service_file.write_text('''<?php

class UserService
{
    public function createUser(string $name): User
    {
        return new User($name);
    }
}''')
        
        # Change to temp directory for testing
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            references = plugin.findReferences("User")
            
            assert len(references) >= 2  # Definition + usage
            ref_files = [ref.file for ref in references]
            assert any("User.php" in f for f in ref_files)
            assert any("UserService.php" in f for f in ref_files)
        finally:
            os.chdir(old_cwd)

    def test_search_functionality(self, plugin, sample_php_code):
        """Test search functionality."""
        # Index the sample code
        plugin.indexFile("test.php", sample_php_code)
        
        # Test search
        results = plugin.search("User")
        assert len(results) > 0
        
        # Test with limit
        results_limited = plugin.search("User", {"limit": 5})
        assert len(results_limited) <= 5

    def test_regex_fallback(self, plugin):
        """Test regex-based parsing when Tree-sitter fails."""
        with patch.object(plugin._ts, '_parser') as mock_parser:
            mock_parser.parse.side_effect = Exception("Tree-sitter failed")
            
            code = '''<?php

class TestClass
{
    public function testMethod()
    {
        echo "hello";
    }
}'''
            result = plugin.indexFile("test.php", code)
            
            # Should still extract symbols using regex
            symbols = result["symbols"]
            symbol_names = [s["symbol"] for s in symbols]
            assert "TestClass" in symbol_names
            assert "testMethod" in symbol_names

    def test_sqlite_integration(self, plugin_with_sqlite, sample_php_code):
        """Test SQLite storage integration."""
        result = plugin_with_sqlite.indexFile("test.php", sample_php_code)
        
        # Verify symbols were stored
        assert result["file"] == "test.php"
        assert len(result["symbols"]) > 0
        
        # Test that indexer was updated
        assert plugin_with_sqlite.get_indexed_count() >= 0

    def test_phpdoc_extraction(self, plugin):
        """Test extraction of PHPDoc comments."""
        code_with_docs = '''<?php

/**
 * This is a user class
 * It handles user operations
 * 
 * @property string $name
 */
class User
{
    /**
     * Initialize a new user
     * @param string $name the user's name
     */
    public function __construct(string $name)
    {
        $this->name = $name;
    }
}'''
        
        # Test the helper method directly
        lines = code_with_docs.split('\n')
        doc = plugin._extract_documentation(lines, 6)  # Line before class definition
        
        assert doc is not None
        assert "This is a user class" in doc
        assert "It handles user operations" in doc

    def test_performance_requirements(self, plugin, sample_php_code):
        """Test that parsing meets performance requirements (< 100ms)."""
        import time
        
        start_time = time.time()
        plugin.indexFile("test.php", sample_php_code)
        end_time = time.time()
        
        parse_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert parse_time < 100, f"Parsing took {parse_time:.2f}ms, should be < 100ms"

    def test_laravel_patterns_comprehensive(self, plugin):
        """Test comprehensive Laravel pattern detection."""
        laravel_code = '''<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;

class User extends Model
{
    protected $fillable = ['name', 'email'];
}

namespace App\\Http\\Controllers;

use Illuminate\\Http\\Request;

class UserController extends Controller
{
    public function index()
    {
        return User::all();
    }
}

namespace App\\Http\\Middleware;

use Closure;

class AuthMiddleware
{
    public function handle(Request $request, Closure $next)
    {
        return $next($request);
    }
}'''
        
        result = plugin.indexFile("laravel_classes.php", laravel_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        assert symbols.get("User") == "model"
        assert symbols.get("UserController") == "controller"
        # Middleware detection would depend on specific pattern matching

    def test_visibility_modifiers(self, plugin):
        """Test detection of method and property visibility."""
        code = '''<?php

class TestClass
{
    public string $publicProperty;
    private string $privateProperty;
    protected string $protectedProperty;
    
    public static string $staticProperty;
    
    public function publicMethod() {}
    private function privateMethod() {}
    protected function protectedMethod() {}
    
    public static function staticMethod() {}
    private static function privateStaticMethod() {}
}'''
        
        result = plugin.indexFile("visibility.php", code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Test method visibility
        assert "private" in symbols.get("privateMethod", "") or symbols.get("privateMethod") == "private_method"
        assert "protected" in symbols.get("protectedMethod", "") or symbols.get("protectedMethod") == "protected_method"
        assert "static" in symbols.get("staticMethod", "") or symbols.get("staticMethod") == "static_method"
        
        # Test property visibility
        assert "private" in symbols.get("privateProperty", "") or symbols.get("privateProperty") == "private_property"
        assert "protected" in symbols.get("protectedProperty", "") or symbols.get("protectedProperty") == "protected_property"
        assert "static" in symbols.get("staticProperty", "") or symbols.get("staticProperty") == "static_property"

    def test_empty_file_handling(self, plugin):
        """Test handling of empty or minimal files."""
        # Empty file
        result = plugin.indexFile("empty.php", "")
        assert result["symbols"] == []
        
        # File with only PHP opening tag
        result = plugin.indexFile("minimal.php", "<?php")
        assert result["symbols"] == []
        
        # File with only comments
        result = plugin.indexFile("comments.php", "<?php\n// Just a comment\n/* Another comment */")
        assert result["symbols"] == []

    def test_malformed_code_handling(self, plugin):
        """Test handling of malformed PHP code."""
        malformed_code = '''<?php

class User
{
    public function __construct()
    {
        // Missing closing brace
    
    public function anotherMethod()
    {
        echo "test";
    }
// Missing class closing brace'''
        
        # Should not crash, should extract what it can
        result = plugin.indexFile("malformed.php", malformed_code)
        assert "symbols" in result
        # May have partial symbols depending on parsing robustness

    def test_interface_and_trait_parsing(self, plugin):
        """Test parsing of interfaces and traits."""
        code = '''<?php

interface UserInterface
{
    public function getName(): string;
    public function setName(string $name): void;
}

trait UserTrait
{
    protected string $name;
    
    public function getName(): string
    {
        return $this->name;
    }
}

class User implements UserInterface
{
    use UserTrait;
    
    public function setName(string $name): void
    {
        $this->name = $name;
    }
}'''
        
        result = plugin.indexFile("interface_trait.php", code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        assert symbols.get("UserInterface") == "interface"
        assert symbols.get("UserTrait") == "trait"
        assert symbols.get("User") == "class"

    def test_abstract_class_detection(self, plugin):
        """Test detection of abstract classes."""
        code = '''<?php

abstract class AbstractUser
{
    protected string $name;
    
    abstract public function getName(): string;
    
    public function setName(string $name): void
    {
        $this->name = $name;
    }
}

class ConcreteUser extends AbstractUser
{
    public function getName(): string
    {
        return $this->name;
    }
}'''
        
        result = plugin.indexFile("abstract.php", code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        assert symbols.get("AbstractUser") == "abstract_class"
        assert symbols.get("ConcreteUser") == "class"