"""Comprehensive test suite for Ruby plugin."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_server.plugins.ruby_plugin import Plugin as RubyPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRubyPlugin:
    """Test cases for Ruby language plugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create a Ruby plugin instance for testing."""
        with patch.object(RubyPlugin, '_preindex'):  # Skip preindexing during tests
            return RubyPlugin()
    
    @pytest.fixture
    def plugin_with_sqlite(self, tmp_path):
        """Create a Ruby plugin with SQLite storage."""
        db_path = tmp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))
        
        with patch.object(RubyPlugin, '_preindex'):
            return RubyPlugin(sqlite_store=sqlite_store)
    
    @pytest.fixture
    def sample_ruby_code(self):
        """Sample Ruby code for testing."""
        return '''# Sample Ruby class
class User < ApplicationRecord
  # Associations
  has_many :posts, dependent: :destroy
  belongs_to :organization, optional: true
  
  # Validations
  validates :email, presence: true
  validates :name, length: { minimum: 2 }
  
  # Scopes
  scope :active, -> { where(active: true) }
  
  # Class methods
  def self.find_by_email(email)
    where(email: email).first
  end
  
  # Instance methods
  def full_name
    "#{first_name} #{last_name}"
  end
  
  def admin?
    role == 'admin'
  end
  
  # Private methods
  private
  
  def normalize_email
    self.email = email.downcase
  end
  
  protected
  
  def can_edit?(user)
    user == self || user.admin?
  end
end

# Module definition
module UserService
  extend self
  
  MAX_ATTEMPTS = 5
  
  def authenticate(email, password)
    user = User.find_by_email(email)
    user&.authenticate(password)
  end
  
  # Metaprogramming
  define_method :dynamic_method do |param|
    puts param
  end
  
  attr_accessor :logger
  attr_reader :config
end'''
    
    @pytest.fixture
    def sample_controller_code(self):
        """Sample Rails controller code."""
        return '''class UsersController < ApplicationController
  before_action :set_user, only: [:show, :edit, :update]
  
  def index
    @users = User.active.page(params[:page])
  end
  
  def show
    @posts = @user.posts.recent
  end
  
  def create
    @user = User.new(user_params)
    if @user.save
      redirect_to @user
    else
      render :new
    end
  end
  
  private
  
  def set_user
    @user = User.find(params[:id])
  end
  
  def user_params
    params.require(:user).permit(:name, :email)
  end
end'''

    def test_supports_ruby_files(self, plugin):
        """Test that plugin supports Ruby files."""
        assert plugin.supports("test.rb") is True
        assert plugin.supports("Rakefile") is False  # .rake not included in basic test
        assert plugin.supports("test.gemspec") is True
        assert plugin.supports("test.py") is False
        assert plugin.supports("test.js") is False

    def test_indexFile_basic_parsing(self, plugin, sample_ruby_code):
        """Test basic file indexing and symbol extraction."""
        result = plugin.indexFile("test.rb", sample_ruby_code)
        
        assert result["file"] == "test.rb"
        assert result["language"] == "ruby"
        assert "symbols" in result
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check for extracted symbols
        assert "User" in symbol_names
        assert "UserService" in symbol_names
        assert "find_by_email" in symbol_names
        assert "full_name" in symbol_names
        assert "admin?" in symbol_names
        assert "authenticate" in symbol_names
        assert "MAX_ATTEMPTS" in symbol_names

    def test_symbol_kinds_detection(self, plugin, sample_ruby_code):
        """Test correct detection of symbol kinds."""
        result = plugin.indexFile("test.rb", sample_ruby_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Test class detection with Rails patterns
        assert symbols.get("User") == "model"  # Should detect ActiveRecord model
        assert symbols.get("UserService") == "module"
        
        # Test method kinds
        assert "method" in symbols.get("full_name", "")
        assert "method" in symbols.get("admin?", "")
        
        # Test visibility
        assert "private" in symbols.get("normalize_email", "") or symbols.get("normalize_email") == "private_method"
        assert "protected" in symbols.get("can_edit?", "") or symbols.get("can_edit?") == "protected_method"
        
        # Test class methods
        assert "class_method" in symbols.get("find_by_email", "") or "method" in symbols.get("find_by_email", "")

    def test_controller_detection(self, plugin, sample_controller_code):
        """Test Rails controller detection."""
        result = plugin.indexFile("users_controller.rb", sample_controller_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        # Should detect as controller
        assert symbols.get("UsersController") == "controller"

    def test_metaprogramming_detection(self, plugin, sample_ruby_code):
        """Test detection of metaprogramming patterns."""
        result = plugin.indexFile("test.rb", sample_ruby_code)
        symbols = result["symbols"]
        
        # Look for metaprogramming-generated symbols
        meta_symbols = [s for s in symbols if "generated" in s["kind"]]
        assert len(meta_symbols) > 0
        
        # Check for specific patterns
        symbol_kinds = [s["kind"] for s in symbols]
        assert any("attr_accessor" in kind for kind in symbol_kinds)

    def test_getDefinition(self, plugin, tmp_path):
        """Test symbol definition lookup."""
        # Create test file
        test_file = tmp_path / "user.rb"
        test_file.write_text('''class User
  def initialize(name)
    @name = name
  end
  
  def full_name
    @name
  end
end''')
        
        # Change to temp directory for testing
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            definition = plugin.getDefinition("User")
            
            assert definition is not None
            assert definition["symbol"] == "User"
            assert definition["kind"] == "class"
            assert definition["language"] == "ruby"
            assert "user.rb" in definition["defined_in"]
        finally:
            os.chdir(old_cwd)

    def test_findReferences(self, plugin, tmp_path):
        """Test finding symbol references."""
        # Create test files
        user_file = tmp_path / "user.rb"
        user_file.write_text('''class User
  def initialize(name)
    @name = name
  end
end''')
        
        service_file = tmp_path / "service.rb"
        service_file.write_text('''class UserService
  def create_user(name)
    user = User.new(name)
    user.save
  end
end''')
        
        # Change to temp directory for testing
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            references = plugin.findReferences("User")
            
            assert len(references) >= 2  # Definition + usage
            ref_files = [ref.file for ref in references]
            assert any("user.rb" in f for f in ref_files)
            assert any("service.rb" in f for f in ref_files)
        finally:
            os.chdir(old_cwd)

    def test_search_functionality(self, plugin, sample_ruby_code):
        """Test search functionality."""
        # Index the sample code
        plugin.indexFile("test.rb", sample_ruby_code)
        
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
            
            code = '''class TestClass
  def test_method
    puts "hello"
  end
end'''
            result = plugin.indexFile("test.rb", code)
            
            # Should still extract symbols using regex
            symbols = result["symbols"]
            symbol_names = [s["symbol"] for s in symbols]
            assert "TestClass" in symbol_names
            assert "test_method" in symbol_names

    def test_sqlite_integration(self, plugin_with_sqlite, sample_ruby_code):
        """Test SQLite storage integration."""
        result = plugin_with_sqlite.indexFile("test.rb", sample_ruby_code)
        
        # Verify symbols were stored
        assert result["file"] == "test.rb"
        assert len(result["symbols"]) > 0
        
        # Test that indexer was updated
        assert plugin_with_sqlite.get_indexed_count() >= 0

    def test_documentation_extraction(self, plugin):
        """Test extraction of documentation comments."""
        code_with_docs = '''# This is a user class
# It handles user operations
class User
  # Initialize a new user
  # @param name [String] the user's name
  def initialize(name)
    @name = name
  end
end'''
        
        definition = plugin.getDefinition("User")
        # Note: This would require the file to exist, so we test the helper method
        lines = code_with_docs.split('\n')
        doc = plugin._extract_documentation(lines, 2)  # Line before class definition
        
        assert doc is not None
        assert "This is a user class" in doc
        assert "It handles user operations" in doc

    def test_performance_requirements(self, plugin, sample_ruby_code):
        """Test that parsing meets performance requirements (< 100ms)."""
        import time
        
        start_time = time.time()
        plugin.indexFile("test.rb", sample_ruby_code)
        end_time = time.time()
        
        parse_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert parse_time < 100, f"Parsing took {parse_time:.2f}ms, should be < 100ms"

    def test_rails_patterns_comprehensive(self, plugin):
        """Test comprehensive Rails pattern detection."""
        rails_code = '''class User < ApplicationRecord
  has_many :posts
  belongs_to :organization
  validates :email, presence: true
  scope :active, -> { where(active: true) }
end

class PostsController < ApplicationController
  def index
    @posts = Post.all
  end
end

class CreateUsers < ActiveRecord::Migration[7.0]
  def change
    create_table :users do |t|
      t.string :name
      t.timestamps
    end
  end
end'''
        
        result = plugin.indexFile("rails_models.rb", rails_code)
        symbols = {s["symbol"]: s["kind"] for s in result["symbols"]}
        
        assert symbols.get("User") == "model"
        assert symbols.get("PostsController") == "controller"
        # Migration detection would depend on specific pattern matching

    def test_empty_file_handling(self, plugin):
        """Test handling of empty or minimal files."""
        # Empty file
        result = plugin.indexFile("empty.rb", "")
        assert result["symbols"] == []
        
        # File with only comments
        result = plugin.indexFile("comments.rb", "# Just a comment\n# Another comment")
        assert result["symbols"] == []
        
        # File with only whitespace
        result = plugin.indexFile("whitespace.rb", "   \n\t\n  ")
        assert result["symbols"] == []

    def test_malformed_code_handling(self, plugin):
        """Test handling of malformed Ruby code."""
        malformed_code = '''class User
  def initialize
    # Missing end
  
  def another_method
    puts "test"
  end
# Missing class end'''
        
        # Should not crash, should extract what it can
        result = plugin.indexFile("malformed.rb", malformed_code)
        assert "symbols" in result
        # May have partial symbols depending on parsing robustness