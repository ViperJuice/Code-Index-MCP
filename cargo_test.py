#!/usr/bin/env python3
"""
Test TOML plugin specifically on Cargo.toml files.
"""

import sys
from pathlib import Path

# Add the mcp_server to Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.toml_plugin.plugin import Plugin as TomlPlugin


def test_cargo_files():
    """Test TOML plugin on Cargo.toml files."""
    print("📦 Testing Cargo.toml Files")
    print("=" * 50)
    
    plugin = TomlPlugin()
    
    # Create a test Cargo.toml content
    cargo_content = '''# Example Cargo.toml from a real Rust project
[package]
name = "tokio"
version = "1.40.0"
edition = "2021"
authors = ["Tokio Contributors <team@tokio.rs>"]
license = "MIT"
readme = "README.md"
repository = "https://github.com/tokio-rs/tokio"
homepage = "https://tokio.rs"
description = "An event-driven, non-blocking I/O platform for writing asynchronous I/O backed applications."
categories = ["asynchronous", "network-programming"]
keywords = ["io", "async", "non-blocking", "futures"]

[features]
default = ["rt"]
full = ["fs", "io-util", "io-std", "net", "process", "rt", "rt-multi-thread", "signal", "sync", "time"]
fs = []
io-util = ["bytes"]
io-std = []
net = ["libc"]
process = ["bytes", "libc", "signal-hook-registry"]
rt = []
rt-multi-thread = ["rt"]
signal = ["libc", "signal-hook-registry", "windows-sys/Win32_System_Console"]
sync = []
time = []

[dependencies]
bytes = { version = "1.7.0", optional = true }
libc = { version = "0.2.162", optional = true }
mio = { version = "1.0.2", optional = true }
pin-project-lite = "0.2.11"

[target.'cfg(unix)'.dependencies]
signal-hook-registry = { version = "1.1.1", optional = true }

[target.'cfg(windows)'.dependencies]
windows-sys = { version = "0.52", optional = true }

[dev-dependencies]
tokio-test = { version = "0.4.0", path = "../tokio-test" }
tokio-stream = { version = "0.1", path = "../tokio-stream" }
futures = { version = "0.3.0", features = ["async-await"] }

[workspace]
members = [
    "tokio",
    "tokio-macros",
    "tokio-stream",
    "tokio-test",
    "tokio-util",
]

[[bin]]
name = "tokio-console"
required-features = ["rt", "net"]
'''
    
    print("Testing synthetic Cargo.toml content...")
    shard = plugin.indexFile("Cargo.toml", cargo_content)
    symbols = shard.get("symbols", [])
    
    print(f"Total symbols found: {len(symbols)}")
    
    # Group symbols by type
    symbol_types = {}
    for symbol in symbols:
        kind = symbol.get("kind", "unknown")
        symbol_types[kind] = symbol_types.get(kind, 0) + 1
    
    print(f"Symbol types: {symbol_types}")
    
    # Show package information
    print("\n📋 Package Information:")
    for symbol in symbols:
        if symbol.get("metadata", {}).get("cargo_field") in ["name", "version", "edition"]:
            print(f"  {symbol.get('symbol')}: {symbol.get('metadata', {}).get('value', 'N/A')}")
    
    # Show dependencies
    print("\n📦 Dependencies:")
    dep_count = 0
    for symbol in symbols:
        if symbol.get("metadata", {}).get("is_dependency"):
            dep_name = symbol.get("metadata", {}).get("dependency", "N/A")
            section = symbol.get("metadata", {}).get("section", "dependencies")
            print(f"  {dep_name} (in {section})")
            dep_count += 1
            if dep_count >= 10:  # Limit output
                break
    
    # Show features
    print("\n🔧 Features:")
    feature_count = 0
    for symbol in symbols:
        if symbol.get("metadata", {}).get("section") == "features":
            feature_name = symbol.get("metadata", {}).get("feature", "N/A")
            feature_deps = symbol.get("metadata", {}).get("dependencies", [])
            print(f"  {feature_name}: {feature_deps}")
            feature_count += 1
            if feature_count >= 5:  # Limit output
                break
    
    # Test search functionality
    print(f"\n🔍 Search Tests:")
    search_tests = ["tokio", "dependencies", "version", "features"]
    for query in search_tests:
        results = plugin.search(query)
        print(f"  Search '{query}': {len(results)} results")
    
    # Test getDefinition functionality
    print(f"\n📖 Definition Tests:")
    definition_tests = ["package.name", "dependencies.bytes", "features.default"]
    for symbol_name in definition_tests:
        definition = plugin.getDefinition(symbol_name)
        if definition:
            print(f"  Definition '{symbol_name}': found at line {definition.get('line', 'N/A')}")
        else:
            print(f"  Definition '{symbol_name}': not found")
    
    return {
        "total_symbols": len(symbols),
        "symbol_types": symbol_types,
        "symbols": symbols[:10]  # First 10 symbols for analysis
    }


def test_real_cargo_files():
    """Test real Cargo.toml files from repositories."""
    print("\n📦 Testing Real Cargo.toml Files")
    print("=" * 50)
    
    plugin = TomlPlugin()
    results = []
    
    # Find actual Cargo.toml files
    cargo_files = []
    
    # Look for specific known Cargo.toml files
    potential_files = [
        "test_repos/rust/serde/Cargo.toml",
        "test_repos/rust/tokio/Cargo.toml", 
        "test_repos/bat/Cargo.toml"
    ]
    
    for file_path in potential_files:
        path = Path(file_path)
        if path.exists():
            cargo_files.append(path)
    
    # Also glob for any Cargo.toml files
    for cargo_file in Path("test_repos").rglob("Cargo.toml"):
        if cargo_file not in cargo_files:
            cargo_files.append(cargo_file)
        if len(cargo_files) >= 5:  # Limit to 5 files
            break
    
    print(f"Found {len(cargo_files)} Cargo.toml files")
    
    for cargo_file in cargo_files:
        try:
            print(f"\n📄 Testing: {cargo_file}")
            content = cargo_file.read_text(encoding='utf-8')
            
            # Use just the filename to avoid path issues
            shard = plugin.indexFile("Cargo.toml", content)
            symbols = shard.get("symbols", [])
            
            print(f"  Symbols: {len(symbols)}")
            
            # Look for package info
            package_info = {}
            for symbol in symbols:
                metadata = symbol.get("metadata", {})
                if metadata.get("cargo_field") in ["name", "version", "edition"]:
                    package_info[metadata["cargo_field"]] = metadata.get("value", "N/A")
            
            if package_info:
                print(f"  Package: {package_info}")
            
            # Count dependencies
            deps = [s for s in symbols if s.get("metadata", {}).get("is_dependency")]
            print(f"  Dependencies: {len(deps)}")
            
            # Count features
            features = [s for s in symbols if s.get("metadata", {}).get("section") == "features"]
            print(f"  Features: {len(features)}")
            
            results.append({
                "file": str(cargo_file),
                "symbols": len(symbols),
                "package_info": package_info,
                "dependencies": len(deps),
                "features": len(features)
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return results


def main():
    """Run Cargo.toml tests."""
    print("🚀 Cargo.toml Plugin Testing")
    print("=" * 70)
    
    # Test synthetic content
    synthetic_results = test_cargo_files()
    
    # Test real files
    real_results = test_real_cargo_files()
    
    # Summary
    print(f"\n📊 Summary")
    print("=" * 50)
    print(f"Synthetic Cargo.toml symbols: {synthetic_results['total_symbols']}")
    print(f"Real Cargo.toml files tested: {len(real_results)}")
    
    if real_results:
        total_real_symbols = sum(r["symbols"] for r in real_results)
        total_deps = sum(r["dependencies"] for r in real_results)
        total_features = sum(r["features"] for r in real_results)
        
        print(f"Total symbols in real files: {total_real_symbols}")
        print(f"Total dependencies: {total_deps}")
        print(f"Total features: {total_features}")
        
        print(f"\n📋 Real File Details:")
        for result in real_results:
            name = result["package_info"].get("name", "unknown")
            version = result["package_info"].get("version", "unknown")
            print(f"  {name} v{version}: {result['symbols']} symbols, {result['dependencies']} deps")
    
    print("\n✅ Cargo.toml testing completed!")


if __name__ == "__main__":
    main()