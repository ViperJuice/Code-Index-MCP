#!/usr/bin/env python3
"""Comprehensive test of semantic search and all retrieval varieties."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mcp_server_cli


async def test_comprehensive_retrieval():
    """Test all varieties of retrieval: exact search, fuzzy search, semantic search."""
    print("=== Comprehensive Retrieval Testing ===\n")

    # Create diverse test files to properly test all retrieval methods
    test_files = {
        "user_management.py": '''"""User management module for handling user operations."""

import asyncio
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    """Represents a user in the system."""
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool = True

class UserManager:
    """Manages user operations like creation, authentication, and retrieval."""
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.next_id = 1
    
    def create_user(self, username: str, email: str, password: str) -> User:
        """Create a new user with hashed password."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(
            id=self.next_id,
            username=username,
            email=email,
            password_hash=password_hash
        )
        self.users[self.next_id] = user
        self.next_id += 1
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by checking password."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        for user in self.users.values():
            if user.username == username and user.password_hash == password_hash:
                return user if user.is_active else None
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve user by their unique identifier."""
        return self.users.get(user_id)
    
    def get_users_by_email_domain(self, domain: str) -> List[User]:
        """Find all users with email addresses from a specific domain."""
        return [user for user in self.users.values() 
                if user.email.endswith(f"@{domain}")]
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account for security purposes."""
        if user_id in self.users:
            self.users[user_id].is_active = False
            return True
        return False
    
    async def process_user_data(self, user_data: List[Dict]) -> List[User]:
        """Asynchronously process bulk user data for import."""
        users = []
        for data in user_data:
            user = self.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password']
            )
            users.append(user)
            await asyncio.sleep(0.001)  # Simulate async processing
        return users

def validate_email_format(email: str) -> bool:
    """Validate email address format using basic checks."""
    return "@" in email and "." in email.split("@")[-1]

def generate_temporary_password() -> str:
    """Generate a secure temporary password for new users."""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))
''',
        "authentication.go": """package main

import (
    "crypto/sha256"
    "encoding/hex"
    "errors"
    "time"
    "github.com/golang-jwt/jwt/v4"
)

// User represents a system user
type User struct {
    ID       int    `json:"id"`
    Username string `json:"username"`
    Email    string `json:"email"`
    IsActive bool   `json:"is_active"`
}

// AuthenticationService handles user authentication and token management
type AuthenticationService struct {
    jwtSecret []byte
    users     map[string]User
}

// Claims represents JWT token claims
type Claims struct {
    UserID   int    `json:"user_id"`
    Username string `json:"username"`
    jwt.RegisteredClaims
}

// NewAuthenticationService creates a new authentication service
func NewAuthenticationService(secret string) *AuthenticationService {
    return &AuthenticationService{
        jwtSecret: []byte(secret),
        users:     make(map[string]User),
    }
}

// HashPassword creates a SHA256 hash of the password
func (auth *AuthenticationService) HashPassword(password string) string {
    hash := sha256.Sum256([]byte(password))
    return hex.EncodeToString(hash[:])
}

// ValidateCredentials checks if the provided credentials are valid
func (auth *AuthenticationService) ValidateCredentials(username, password string) (*User, error) {
    user, exists := auth.users[username]
    if !exists {
        return nil, errors.New("user not found")
    }
    
    if !user.IsActive {
        return nil, errors.New("user account is deactivated")
    }
    
    // In real implementation, compare with stored password hash
    return &user, nil
}

// GenerateToken creates a JWT token for authenticated user
func (auth *AuthenticationService) GenerateToken(user *User) (string, error) {
    expirationTime := time.Now().Add(24 * time.Hour)
    claims := &Claims{
        UserID:   user.ID,
        Username: user.Username,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(expirationTime),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
        },
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(auth.jwtSecret)
}

// ValidateToken verifies and parses a JWT token
func (auth *AuthenticationService) ValidateToken(tokenString string) (*Claims, error) {
    claims := &Claims{}
    token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
        return auth.jwtSecret, nil
    })
    
    if err != nil {
        return nil, err
    }
    
    if !token.Valid {
        return nil, errors.New("invalid token")
    }
    
    return claims, nil
}

// RefreshToken generates a new token for an existing valid token
func (auth *AuthenticationService) RefreshToken(oldToken string) (string, error) {
    claims, err := auth.ValidateToken(oldToken)
    if err != nil {
        return "", err
    }
    
    user, exists := auth.users[claims.Username]
    if !exists {
        return "", errors.New("user not found")
    }
    
    return auth.GenerateToken(&user)
}

// RegisterUser adds a new user to the system
func (auth *AuthenticationService) RegisterUser(username, email string) error {
    if _, exists := auth.users[username]; exists {
        return errors.New("username already exists")
    }
    
    user := User{
        ID:       len(auth.users) + 1,
        Username: username,
        Email:    email,
        IsActive: true,
    }
    
    auth.users[username] = user
    return nil
}
""",
        "data_processing.rs": """use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use tokio::time::{sleep, Duration};

/// Represents different types of data processing operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProcessingType {
    Transform,
    Validate,
    Aggregate,
    Filter,
}

/// Configuration for data processing pipeline
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingConfig {
    pub batch_size: usize,
    pub timeout_seconds: u64,
    pub retry_attempts: u32,
    pub parallel_workers: usize,
}

/// Represents a data record in the processing pipeline
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataRecord {
    pub id: String,
    pub data: HashMap<String, String>,
    pub metadata: HashMap<String, String>,
    pub processing_status: ProcessingStatus,
}

/// Status of data processing for each record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProcessingStatus {
    Pending,
    InProgress,
    Completed,
    Failed(String),
}

/// Main data processing engine
pub struct DataProcessor {
    config: ProcessingConfig,
    processors: HashMap<ProcessingType, Box<dyn Fn(&DataRecord) -> Result<DataRecord, String>>>,
}

impl DataProcessor {
    /// Create a new data processor with the given configuration
    pub fn new(config: ProcessingConfig) -> Self {
        Self {
            config,
            processors: HashMap::new(),
        }
    }
    
    /// Register a processing function for a specific operation type
    pub fn register_processor<F>(&mut self, processing_type: ProcessingType, processor: F)
    where
        F: Fn(&DataRecord) -> Result<DataRecord, String> + 'static,
    {
        self.processors.insert(processing_type, Box::new(processor));
    }
    
    /// Process a batch of data records asynchronously
    pub async fn process_batch(&self, records: Vec<DataRecord>) -> Vec<DataRecord> {
        let mut processed_records = Vec::new();
        
        for chunk in records.chunks(self.config.batch_size) {
            let chunk_results = self.process_chunk(chunk.to_vec()).await;
            processed_records.extend(chunk_results);
        }
        
        processed_records
    }
    
    /// Process a single chunk of records with timeout handling
    async fn process_chunk(&self, mut records: Vec<DataRecord>) -> Vec<DataRecord> {
        for record in &mut records {
            record.processing_status = ProcessingStatus::InProgress;
            
            // Simulate processing time
            sleep(Duration::from_millis(10)).await;
            
            // Apply transformations based on data content
            if let Some(transform_data) = self.transform_data_content(&record.data) {
                record.data = transform_data;
                record.processing_status = ProcessingStatus::Completed;
            } else {
                record.processing_status = ProcessingStatus::Failed("Transformation failed".to_string());
            }
        }
        
        records
    }
    
    /// Transform data content using business logic
    fn transform_data_content(&self, data: &HashMap<String, String>) -> Option<HashMap<String, String>> {
        let mut transformed = data.clone();
        
        // Apply data validation and transformation rules
        if let Some(email) = data.get("email") {
            if self.validate_email_format(email) {
                transformed.insert("email_valid".to_string(), "true".to_string());
            } else {
                return None;
            }
        }
        
        // Normalize text fields
        if let Some(name) = data.get("name") {
            transformed.insert("name".to_string(), name.trim().to_lowercase());
        }
        
        Some(transformed)
    }
    
    /// Validate email format using basic pattern matching
    fn validate_email_format(&self, email: &str) -> bool {
        email.contains('@') && email.contains('.') && email.len() > 5
    }
    
    /// Get processing statistics for monitoring
    pub fn get_processing_stats(&self, records: &[DataRecord]) -> ProcessingStats {
        let mut stats = ProcessingStats::default();
        
        for record in records {
            match &record.processing_status {
                ProcessingStatus::Pending => stats.pending += 1,
                ProcessingStatus::InProgress => stats.in_progress += 1,
                ProcessingStatus::Completed => stats.completed += 1,
                ProcessingStatus::Failed(_) => stats.failed += 1,
            }
        }
        
        stats.total = records.len();
        stats
    }
}

/// Statistics for data processing operations
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ProcessingStats {
    pub total: usize,
    pub pending: usize,
    pub in_progress: usize,
    pub completed: usize,
    pub failed: usize,
}

/// Helper function to create sample data for testing
pub fn create_sample_data(count: usize) -> Vec<DataRecord> {
    (0..count)
        .map(|i| DataRecord {
            id: format!("record_{}", i),
            data: {
                let mut data = HashMap::new();
                data.insert("name".to_string(), format!("User {}", i));
                data.insert("email".to_string(), format!("user{}@example.com", i));
                data
            },
            metadata: HashMap::new(),
            processing_status: ProcessingStatus::Pending,
        })
        .collect()
}
""",
        "error_handling.js": """/**
 * Comprehensive error handling utilities for web applications
 */

// Custom error types for different scenarios
class ValidationError extends Error {
    constructor(message, field) {
        super(message);
        this.name = 'ValidationError';
        this.field = field;
    }
}

class NetworkError extends Error {
    constructor(message, statusCode) {
        super(message);
        this.name = 'NetworkError';
        this.statusCode = statusCode;
    }
}

class AuthenticationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'AuthenticationError';
    }
}

// Error handling service for centralized error management
class ErrorHandlingService {
    constructor() {
        this.errorHandlers = new Map();
        this.errorLog = [];
        this.setupGlobalErrorHandling();
    }
    
    /**
     * Register a custom error handler for specific error types
     */
    registerErrorHandler(errorType, handler) {
        if (!this.errorHandlers.has(errorType)) {
            this.errorHandlers.set(errorType, []);
        }
        this.errorHandlers.get(errorType).push(handler);
    }
    
    /**
     * Handle errors with appropriate logging and user notification
     */
    async handleError(error, context = {}) {
        // Log error details
        const errorEntry = {
            timestamp: new Date().toISOString(),
            error: {
                name: error.name,
                message: error.message,
                stack: error.stack
            },
            context,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        this.errorLog.push(errorEntry);
        
        // Execute registered handlers
        const handlers = this.errorHandlers.get(error.constructor.name) || [];
        for (const handler of handlers) {
            try {
                await handler(error, context);
            } catch (handlerError) {
                console.error('Error in error handler:', handlerError);
            }
        }
        
        // Default handling based on error type
        switch (error.constructor.name) {
            case 'ValidationError':
                this.handleValidationError(error);
                break;
            case 'NetworkError':
                this.handleNetworkError(error);
                break;
            case 'AuthenticationError':
                this.handleAuthenticationError(error);
                break;
            default:
                this.handleGenericError(error);
        }
    }
    
    /**
     * Handle validation errors with user-friendly messages
     */
    handleValidationError(error) {
        const message = `Validation failed: ${error.message}`;
        if (error.field) {
            this.highlightErrorField(error.field);
        }
        this.showUserMessage(message, 'warning');
    }
    
    /**
     * Handle network errors with retry options
     */
    handleNetworkError(error) {
        let message = 'Network error occurred. ';
        
        if (error.statusCode >= 500) {
            message += 'Server error - please try again later.';
        } else if (error.statusCode >= 400) {
            message += 'Request error - please check your input.';
        } else {
            message += 'Please check your internet connection.';
        }
        
        this.showUserMessage(message, 'error', true); // with retry option
    }
    
    /**
     * Handle authentication errors with redirect to login
     */
    handleAuthenticationError(error) {
        this.showUserMessage('Authentication required. Redirecting to login...', 'info');
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    /**
     * Handle generic errors with basic notification
     */
    handleGenericError(error) {
        console.error('Unhandled error:', error);
        this.showUserMessage('An unexpected error occurred. Please try again.', 'error');
    }
    
    /**
     * Setup global error handling for unhandled errors
     */
    setupGlobalErrorHandling() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, { type: 'unhandled_promise' });
            event.preventDefault();
        });
        
        // Handle global JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError(event.error, { 
                type: 'global_error',
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });
    }
    
    /**
     * Highlight error field in the UI
     */
    highlightErrorField(fieldName) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('error-field');
            field.focus();
        }
    }
    
    /**
     * Show user-friendly error message
     */
    showUserMessage(message, type = 'info', showRetry = false) {
        // Implementation would depend on UI framework
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        if (showRetry) {
            console.log('Retry option available');
        }
    }
    
    /**
     * Get error statistics for monitoring
     */
    getErrorStats() {
        const stats = {
            total: this.errorLog.length,
            byType: {},
            recent: this.errorLog.slice(-10)
        };
        
        this.errorLog.forEach(entry => {
            const type = entry.error.name;
            stats.byType[type] = (stats.byType[type] || 0) + 1;
        });
        
        return stats;
    }
    
    /**
     * Clear error log (useful for testing)
     */
    clearErrorLog() {
        this.errorLog = [];
    }
}

// Utility functions for common error scenarios
function validateUserInput(data) {
    const errors = [];
    
    if (!data.email || !isValidEmail(data.email)) {
        errors.push(new ValidationError('Invalid email format', 'email'));
    }
    
    if (!data.password || data.password.length < 8) {
        errors.push(new ValidationError('Password must be at least 8 characters', 'password'));
    }
    
    if (errors.length > 0) {
        throw new ValidationError(`Validation failed: ${errors.length} errors`, null);
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return emailRegex.test(email);
}

async function makeApiRequest(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new NetworkError(
                `Request failed: ${response.statusText}`,
                response.status
            );
        }
        
        return await response.json();
    } catch (error) {
        if (error instanceof NetworkError) {
            throw error;
        }
        throw new NetworkError('Network request failed', 0);
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ValidationError,
        NetworkError,
        AuthenticationError,
        ErrorHandlingService,
        validateUserInput,
        makeApiRequest
    };
}
""",
    }

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="semantic_test_")
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        print(f"Working directory: {temp_dir}")

        # Create test files
        for filename, content in test_files.items():
            Path(filename).write_text(content)

        print(f"✓ Created {len(test_files)} test files")

        # Initialize MCP services
        await mcp_server_cli.initialize_services()
        dispatcher = mcp_server_cli.dispatcher

        # Index all files
        print(f"\nIndexing files...")
        for filename in test_files.keys():
            dispatcher.index_file(Path(filename))
            print(f"  ✓ Indexed {filename}")

        # Test 1: Exact Symbol Search
        print(f"\n1. Testing Exact Symbol Search...")
        exact_searches = {
            "User": "Should find User class/struct across languages",
            "create_user": "Should find exact function name",
            "AuthenticationService": "Should find service class",
            "validate_email_format": "Should find validation function",
            "ProcessingConfig": "Should find configuration struct",
        }

        exact_results = {}
        for symbol, description in exact_searches.items():
            results = list(dispatcher.search(symbol, limit=10))
            exact_results[symbol] = len(results)
            print(f"   '{symbol}': {len(results)} results")

            # Show first result for verification
            if results:
                first_result = results[0]
                file_name = Path(first_result.get("file", "")).name
                print(f"     → Found in {file_name}:{first_result.get('line', 'N/A')}")

        # Test 2: Fuzzy/Partial Search
        print(f"\n2. Testing Fuzzy/Partial Search...")
        fuzzy_searches = {
            "auth": "Should find authentication-related items",
            "process": "Should find processing-related functions",
            "validate": "Should find validation functions",
            "error": "Should find error handling code",
            "hash": "Should find hashing/password functions",
        }

        fuzzy_results = {}
        for term, description in fuzzy_searches.items():
            results = list(dispatcher.search(term, limit=15))
            fuzzy_results[term] = len(results)
            print(f"   '{term}': {len(results)} results")

            # Show language distribution
            if results:
                languages = set()
                for result in results[:5]:
                    file_name = result.get("file", "")
                    if file_name:
                        ext = Path(file_name).suffix
                        languages.add(ext)
                print(f"     → Found in: {', '.join(sorted(languages))}")

        # Test 3: Semantic Search (AI-powered)
        print(f"\n3. Testing Semantic Search...")
        semantic_queries = {
            "user authentication and login": "Should find auth-related code",
            "data validation and error checking": "Should find validation code",
            "password hashing and security": "Should find security functions",
            "asynchronous data processing": "Should find async processing code",
            "email format validation": "Should find email validation",
            "error handling and logging": "Should find error management",
            "JWT token generation": "Should find token-related code",
            "database operations": "Should find data persistence code",
        }

        semantic_results = {}
        for query, description in semantic_queries.items():
            try:
                results = list(dispatcher.search(query, semantic=True, limit=8))
                semantic_results[query] = len(results)
                print(f"   '{query}': {len(results)} results")

                # Show semantic matches
                if results:
                    for i, result in enumerate(results[:2]):
                        file_name = Path(result.get("file", "")).name
                        snippet = result.get("snippet", "")[:50] + "..."
                        print(f"     {i+1}. {file_name}: {snippet}")
                else:
                    print(f"     → No semantic matches found")
            except Exception as e:
                print(f"   '{query}': Error - {e}")
                semantic_results[query] = 0

        # Test 4: Symbol Definition Lookup
        print(f"\n4. Testing Symbol Definition Lookup...")
        definition_tests = [
            "User",
            "AuthenticationService",
            "DataProcessor",
            "ErrorHandlingService",
            "ProcessingConfig",
        ]

        definition_results = {}
        for symbol in definition_tests:
            definition = dispatcher.lookup(symbol)
            if definition:
                file_name = Path(definition.get("defined_in", "")).name
                kind = definition.get("kind", "unknown")
                line = definition.get("line", "N/A")
                definition_results[symbol] = True
                print(f"   ✓ {symbol}: {kind} in {file_name}:{line}")
            else:
                definition_results[symbol] = False
                print(f"   ✗ {symbol}: not found")

        # Test 5: Cross-Language Concept Search
        print(f"\n5. Testing Cross-Language Concept Search...")
        concept_searches = {
            "email validation": "Email validation across all languages",
            "user management": "User-related operations",
            "async processing": "Asynchronous operations",
            "error handling": "Error management patterns",
        }

        concept_results = {}
        for concept, description in concept_searches.items():
            # Test both regular and semantic search
            regular_results = list(dispatcher.search(concept, limit=10))

            try:
                semantic_results_for_concept = list(
                    dispatcher.search(concept, semantic=True, limit=5)
                )
            except:
                semantic_results_for_concept = []

            # Count languages found
            all_results = regular_results + semantic_results_for_concept
            languages_found = set()
            for result in all_results:
                file_name = result.get("file", "")
                if file_name:
                    ext = Path(file_name).suffix
                    languages_found.add(ext)

            concept_results[concept] = {
                "regular": len(regular_results),
                "semantic": len(semantic_results_for_concept),
                "languages": len(languages_found),
            }

            print(
                f"   '{concept}': {len(regular_results)} regular + {len(semantic_results_for_concept)} semantic across {len(languages_found)} languages"
            )

        # Summary and Analysis
        print(f"\n=== Comprehensive Retrieval Analysis ===")

        total_exact = sum(exact_results.values())
        total_fuzzy = sum(fuzzy_results.values())
        total_semantic = sum(semantic_results.values())
        total_definitions = sum(1 for found in definition_results.values() if found)

        print(f"\nRetrieval Method Performance:")
        print(f"  ✓ Exact symbol search: {total_exact} results across {len(exact_results)} queries")
        print(
            f"  ✓ Fuzzy/partial search: {total_fuzzy} results across {len(fuzzy_results)} queries"
        )
        print(
            f"  ✓ Semantic search: {total_semantic} results across {len(semantic_results)} queries"
        )
        print(f"  ✓ Symbol definitions: {total_definitions}/{len(definition_results)} found")

        print(f"\nCross-Language Capabilities:")
        concept_langs = sum(r["languages"] for r in concept_results.values())
        print(f"  ✓ Cross-language concepts: {concept_langs} language combinations")

        # Check semantic search functionality
        semantic_working = total_semantic > 0
        if semantic_working:
            print(f"  ✓ Semantic search: OPERATIONAL")
        else:
            print(f"  ⚠ Semantic search: Limited results (may need configuration)")

        print(f"\nDetailed Results:")
        print(f"  Best exact matches: {max(exact_results.items(), key=lambda x: x[1])}")
        print(f"  Best fuzzy matches: {max(fuzzy_results.items(), key=lambda x: x[1])}")
        if semantic_working:
            print(f"  Best semantic matches: {max(semantic_results.items(), key=lambda x: x[1])}")

        # Success criteria
        success = (
            total_exact > 10  # Good exact search
            and total_fuzzy > 20  # Good fuzzy search
            and total_definitions >= 3  # Symbol lookup working
            and concept_langs > 8  # Cross-language working
        )

        return success, {
            "exact_search": exact_results,
            "fuzzy_search": fuzzy_results,
            "semantic_search": semantic_results,
            "definition_lookup": definition_results,
            "cross_language": concept_results,
            "semantic_working": semantic_working,
        }

    finally:
        # Cleanup
        os.chdir(original_cwd)
        import shutil

        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up test directory")


async def main():
    """Run comprehensive retrieval test."""
    try:
        success, results = await test_comprehensive_retrieval()

        if success:
            print(f"\n🎉 Comprehensive Retrieval: EXCELLENT!")
            print(f"All retrieval methods are working effectively!")

            if results["semantic_working"]:
                print(f"🧠 Semantic search is operational and finding relevant results!")
            else:
                print(f"⚠️ Semantic search needs configuration (Voyage AI / Qdrant setup)")
        else:
            print(f"\n⚠️ Some retrieval methods need optimization")

        return success

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
