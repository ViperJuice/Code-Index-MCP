# Ruby Plugin - AI Agent Configuration

> **AI Agents:** This file contains Ruby plugin-specific instructions. Always check root `AGENTS.md` first.

## Essential Commands

```bash
# Test Ruby plugin functionality
pytest tests/test_ruby_plugin.py -v

# Debug Ruby parsing
python -m mcp_server.plugins.ruby_plugin.plugin debug user.rb

# Analyze Rails project
python -m mcp_server.plugins.ruby_plugin.plugin analyze app/

# Check Gemfile dependencies
python -m mcp_server.plugins.ruby_plugin.plugin deps Gemfile
```

## Code Style Preferences

### Modern Ruby Patterns
```ruby
# Preferred: Clear, idiomatic Ruby
class UserService
  include ActiveSupport::Concern
  
  attr_reader :repository, :cache
  
  def initialize(repository: UserRepository.new, cache: Rails.cache)
    @repository = repository
    @cache = cache
  end
  
  def find_user(id)
    cache.fetch("user:#{id}", expires_in: 1.hour) do
      repository.find(id)
    end
  end
  
  private
  
  def validate_user(user)
    raise ArgumentError, "Invalid user" unless user.valid?
  end
end
```

## Parser Implementation Details

### Symbol Extraction
- **Classes**: Regular, singleton, embedded modules
- **Modules**: Including mixins and concerns
- **Methods**: Instance, class, private/protected
- **Constants**: Module and class constants
- **Variables**: Instance, class, global
- **Metaprogramming**: Dynamic method generation
- **DSL Methods**: Rails-specific patterns

### Rails Framework Detection

1. **ActiveRecord Models**
   - `< ApplicationRecord` inheritance
   - Associations: `has_many`, `belongs_to`, `has_one`
   - Validations: `validates`, `validate`
   - Scopes and callbacks

2. **Controllers**
   - `< ApplicationController` inheritance
   - Action methods
   - Before/after filters

3. **Metaprogramming Patterns**
   - `define_method` declarations
   - `method_missing` handlers
   - `attr_accessor`, `attr_reader`, `attr_writer`
   - `delegate` and `alias_method`

### Performance Metrics
- Parse time: <1ms per file (achieving ~0.36ms)
- Memory efficient: Regex-based parsing
- Ruby version support: 2.5+

## Common Issues

### Metaprogramming Detection
```ruby
# Parser handles these patterns:
define_method :dynamic_method do |arg|
  # method body
end

class_eval do
  attr_accessor :generated_attribute
end
```

### DSL Method Recognition
```ruby
# Rails DSL methods are tracked:
scope :active, -> { where(active: true) }
validates :email, presence: true, uniqueness: true
has_many :posts, dependent: :destroy
```

### String Interpolation in Symbols
```ruby
# Parser handles dynamic symbols:
define_method :"#{prefix}_method" do
  # implementation
end
```

## Testing Checklist

- [x] Basic class/module parsing
- [x] Method extraction with visibility
- [x] Constant detection
- [x] Rails model patterns
- [x] Metaprogramming constructs
- [x] DSL method recognition
- [x] Special method names (?, !)
- [x] Block and lambda detection

## Integration Notes

The Ruby plugin integrates with:
- **Bundler**: Reads Gemfile for dependencies
- **Rails**: Detects Rails patterns and structure
- **RSpec**: Test file recognition
- **YARD**: Documentation comment support

## Framework-Specific Features

### Rails Projects
```bash
# Optimized for Rails conventions
export RUBY_FRAMEWORK=rails

# Common Rails paths
# app/models/
# app/controllers/
# app/services/
# lib/
```

### Plain Ruby Projects
```bash
# For non-Rails Ruby
export RUBY_FRAMEWORK=none

# Common Ruby paths
# lib/
# spec/
# test/
```

## Performance Optimization

For large Ruby codebases:
```bash
# Skip vendored gems
export RUBY_SKIP_VENDOR=true

# Enable metaprogramming cache
export RUBY_META_CACHE=true

# Parallel file processing
export RUBY_PARALLEL_PARSE=true
```

## Metaprogramming Patterns

### Detected Patterns
- Dynamic method definition
- Method missing handlers
- Class and module eval
- Singleton method definition

### Code Generation Tracking
The parser tracks generated methods from:
- `attr_*` declarations
- `delegate` statements
- `define_method` calls
- Rails associations and validations

## Best Practices Detection

### Encouraged Patterns
- Composition over inheritance
- Duck typing interfaces
- Functional approaches
- Clear method naming

### Anti-patterns Detected
- Deep inheritance chains
- Monkey patching
- Global variable usage
- Complex metaprogramming

## Future Enhancements

1. **Advanced Rails Support**
   - Route analysis
   - Migration tracking
   - ActiveJob parsing
   - Mailer detection

2. **Metaprogramming Analysis**
   - Full eval tracking
   - Dynamic constant resolution
   - Method chain analysis

3. **Modern Ruby Features**
   - Pattern matching (Ruby 3.0+)
   - Endless method syntax
   - Numbered parameters

---
*Plugin completed by Developer 4 - Production Ready*