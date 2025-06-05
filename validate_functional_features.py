#!/usr/bin/env python3
"""Validate advanced functional programming language features detection."""

import sys
import os
from pathlib import Path

# Add the mcp_server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))

from mcp_server.plugins.haskell_plugin.plugin import Plugin as HaskellPlugin
from mcp_server.plugins.scala_plugin.plugin import Plugin as ScalaPlugin

def validate_functional_features():
    """Validate advanced functional programming features in both languages."""
    
    print("🧪 Advanced Functional Programming Features Validation")
    print("=" * 60)
    
    # Initialize plugins
    haskell_plugin = HaskellPlugin(sqlite_store=None)
    scala_plugin = ScalaPlugin(sqlite_store=None)
    
    # Test advanced Haskell features
    print("\n🎯 HASKELL ADVANCED FEATURES")
    print("-" * 40)
    
    # Find files with specific functional patterns
    haskell_test_files = [
        # Type-heavy functional code
        ("test_repos/pandoc-converter/src/Text/Pandoc/Readers/Markdown.hs", "Complex Parser"),
        ("test_repos/yesod-web/yesod-core/Yesod/Core/Handler.hs", "Monad Transformers"),
        ("test_repos/cabal-haskell/Cabal/src/Distribution/Simple/Configure.hs", "Configuration DSL"),
        ("test_repos/pandoc-converter/src/Text/Pandoc/Writers/HTML.hs", "Writer Monad"),
    ]
    
    haskell_results = {}
    for file_path, description in haskell_test_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            shard = haskell_plugin.indexFile(full_path, content)
            
            # Analyze advanced features
            features = analyze_haskell_features(shard, content)
            haskell_results[description] = features
            
            print(f"📄 {description}")
            print(f"   Type signatures: {features['type_signatures']}")
            print(f"   Higher-order functions: {features['higher_order_functions']}")
            print(f"   Type classes: {features['type_classes']}")
            print(f"   Monadic operations: {features['monadic_operations']}")
            print(f"   Pattern matching: {features['pattern_matching']}")
            print(f"   Language pragmas: {features['language_pragmas']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Test advanced Scala features
    print("\n🎯 SCALA ADVANCED FEATURES")
    print("-" * 40)
    
    scala_test_files = [
        # Framework-specific functional code
        ("test_repos/akka-framework/akka-actor/src/main/scala/akka/actor/Actor.scala", "Actor Model"),
        ("test_repos/apache-spark/sql/core/src/main/scala/org/apache/spark/sql/Dataset.scala", "Dataset API"),
        ("test_repos/play-framework/core/play/src/main/scala/play/api/mvc/Controller.scala", "MVC Framework"),
        ("test_repos/akka-framework/akka-stream/src/main/scala/akka/stream/scaladsl/Source.scala", "Streaming"),
    ]
    
    scala_results = {}
    for file_path, description in scala_test_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            shard = scala_plugin.indexFile(full_path, content)
            
            # Analyze advanced features
            features = analyze_scala_features(shard, content)
            scala_results[description] = features
            
            print(f"📄 {description}")
            print(f"   Case classes: {features['case_classes']}")
            print(f"   Traits: {features['traits']}")
            print(f"   Higher-order functions: {features['higher_order_functions']}")
            print(f"   Pattern matching: {features['pattern_matching']}")
            print(f"   Implicits: {features['implicits']}")
            print(f"   Type parameters: {features['type_parameters']}")
            print(f"   Actor patterns: {features['actor_patterns']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Build system integration testing
    print("\n🔧 BUILD SYSTEM INTEGRATION")
    print("-" * 40)
    
    build_files = [
        ("test_repos/cabal-haskell/cabal-install/cabal-install.cabal", "Cabal", haskell_plugin),
        ("test_repos/yesod-web/stack.yaml", "Stack", haskell_plugin),
        ("test_repos/pandoc-converter/pandoc.cabal", "Pandoc Cabal", haskell_plugin),
        ("test_repos/akka-framework/build.sbt", "Akka SBT", scala_plugin),
        ("test_repos/apache-spark/project/SparkBuild.scala", "Spark Build", scala_plugin),
        ("test_repos/play-framework/project/Dependencies.scala", "Play Dependencies", scala_plugin),
    ]
    
    build_results = {}
    for file_path, build_system, plugin in build_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"❌ Build file not found: {file_path}")
            continue
            
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            shard = plugin.indexFile(full_path, content)
            
            features = analyze_build_system(shard, build_system)
            build_results[build_system] = features
            
            print(f"🔨 {build_system} ({Path(file_path).name})")
            print(f"   Dependencies: {features['dependencies']}")
            print(f"   Build targets: {features['build_targets']}")
            print(f"   Configuration: {features['configuration']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Framework pattern detection
    print("\n🏗️ FRAMEWORK PATTERN DETECTION")
    print("-" * 40)
    
    framework_patterns = test_framework_patterns(haskell_plugin, scala_plugin)
    
    for framework, patterns in framework_patterns.items():
        print(f"🎨 {framework}")
        for pattern, count in patterns.items():
            if count > 0:
                print(f"   {pattern}: {count} instances")
        print()
    
    # Summary and validation results
    print("\n📊 VALIDATION SUMMARY")
    print("-" * 40)
    
    # Calculate overall scores
    haskell_score = calculate_haskell_score(haskell_results)
    scala_score = calculate_scala_score(scala_results)
    build_score = calculate_build_score(build_results)
    
    print(f"Haskell functional features detection: {haskell_score}%")
    print(f"Scala functional features detection: {scala_score}%")
    print(f"Build system integration: {build_score}%")
    
    overall_score = (haskell_score + scala_score + build_score) / 3
    print(f"Overall functional programming support: {overall_score:.1f}%")
    
    if overall_score >= 85:
        print("✅ Excellent functional programming support!")
    elif overall_score >= 70:
        print("✅ Good functional programming support!")
    elif overall_score >= 50:
        print("⚠️  Fair functional programming support")
    else:
        print("❌ Limited functional programming support")
    
    return {
        'haskell_results': haskell_results,
        'scala_results': scala_results,
        'build_results': build_results,
        'framework_patterns': framework_patterns,
        'scores': {
            'haskell': haskell_score,
            'scala': scala_score,
            'build': build_score,
            'overall': overall_score
        }
    }

def analyze_haskell_features(shard, content):
    """Analyze advanced Haskell features."""
    features = {
        'type_signatures': 0,
        'higher_order_functions': 0,
        'type_classes': 0,
        'monadic_operations': 0,
        'pattern_matching': 0,
        'language_pragmas': 0
    }
    
    for symbol in shard['symbols']:
        # Type signatures
        if symbol.get('signature') and '::' in symbol['signature']:
            features['type_signatures'] += 1
            # Higher-order functions (functions that take functions)
            if '->' in symbol['signature']:
                arrow_count = symbol['signature'].count('->')
                if arrow_count >= 2:
                    features['higher_order_functions'] += 1
        
        # Type classes
        if symbol.get('kind') == 'class':
            features['type_classes'] += 1
    
    # Analyze content for patterns
    content_lines = content.lower()
    
    # Monadic operations
    monadic_keywords = ['>>=' ,'return', '<-', 'do', 'liftm', 'mapM']
    for keyword in monadic_keywords:
        features['monadic_operations'] += content_lines.count(keyword)
    
    # Pattern matching
    features['pattern_matching'] = content_lines.count('case ') + content_lines.count('| ')
    
    # Language pragmas
    features['language_pragmas'] = content.count('{-# LANGUAGE')
    
    return features

def analyze_scala_features(shard, content):
    """Analyze advanced Scala features."""
    features = {
        'case_classes': 0,
        'traits': 0,
        'higher_order_functions': 0,
        'pattern_matching': 0,
        'implicits': 0,
        'type_parameters': 0,
        'actor_patterns': 0
    }
    
    for symbol in shard['symbols']:
        if symbol.get('kind') == 'case_class':
            features['case_classes'] += 1
        elif symbol.get('kind') == 'trait':
            features['traits'] += 1
        elif symbol.get('kind') == 'implicit':
            features['implicits'] += 1
        elif symbol.get('kind') == 'actor':
            features['actor_patterns'] += 1
        
        # Higher-order functions (methods with function parameters)
        if symbol.get('signature'):
            sig = symbol['signature']
            if '=>' in sig and '(' in sig:
                features['higher_order_functions'] += 1
            if '[' in sig and ']' in sig:
                features['type_parameters'] += 1
    
    # Analyze content for patterns
    content_lines = content.lower()
    features['pattern_matching'] = content_lines.count('match ') + content_lines.count('case ')
    
    return features

def analyze_build_system(shard, build_system):
    """Analyze build system features."""
    features = {
        'dependencies': 0,
        'build_targets': 0,
        'configuration': 0
    }
    
    for symbol in shard['symbols']:
        if symbol.get('kind') in ['dependency', 'plugin']:
            features['dependencies'] += 1
        elif symbol.get('kind') in ['library', 'executable', 'test-suite', 'benchmark']:
            features['build_targets'] += 1
        elif symbol.get('kind') in ['setting', 'package', 'resolver']:
            features['configuration'] += 1
    
    return features

def test_framework_patterns(haskell_plugin, scala_plugin):
    """Test framework-specific pattern detection."""
    patterns = {
        'Yesod Web Framework': {
            'handlers': 0,
            'widgets': 0,
            'forms': 0,
            'templates': 0
        },
        'Akka Framework': {
            'actors': 0,
            'behaviors': 0,
            'messages': 0,
            'supervisors': 0
        },
        'Apache Spark': {
            'rdds': 0,
            'dataframes': 0,
            'transformations': 0,
            'actions': 0
        },
        'Play Framework': {
            'controllers': 0,
            'actions': 0,
            'routes': 0,
            'templates': 0
        }
    }
    
    # This would require analyzing more files, but we can detect basic patterns
    # from the symbols we've already found
    
    return patterns

def calculate_haskell_score(results):
    """Calculate Haskell feature detection score."""
    if not results:
        return 0
    
    total_features = 0
    found_features = 0
    
    for result in results.values():
        for feature, count in result.items():
            total_features += 1
            if count > 0:
                found_features += 1
    
    return int((found_features / total_features) * 100) if total_features > 0 else 0

def calculate_scala_score(results):
    """Calculate Scala feature detection score."""
    if not results:
        return 0
    
    total_features = 0
    found_features = 0
    
    for result in results.values():
        for feature, count in result.items():
            total_features += 1
            if count > 0:
                found_features += 1
    
    return int((found_features / total_features) * 100) if total_features > 0 else 0

def calculate_build_score(results):
    """Calculate build system integration score."""
    if not results:
        return 0
    
    total_features = 0
    found_features = 0
    
    for result in results.values():
        for feature, count in result.items():
            total_features += 1
            if count > 0:
                found_features += 1
    
    return int((found_features / total_features) * 100) if total_features > 0 else 0

if __name__ == "__main__":
    validate_functional_features()