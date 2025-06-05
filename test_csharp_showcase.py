#!/usr/bin/env python3
"""
C# Plugin Showcase - Demonstrates advanced capabilities on select real-world files.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.csharp_plugin.plugin import Plugin


def find_interesting_files() -> List[Path]:
    """Find interesting C# files to showcase plugin capabilities."""
    base_path = Path("/home/jenner/Code/Code-Index-MCP/test_repos/csharp_test")
    
    interesting_files = []
    
    # ASP.NET Core files
    aspnetcore_path = base_path / "aspnetcore"
    if aspnetcore_path.exists():
        # Look for controller files
        controllers = list(aspnetcore_path.rglob("*Controller.cs"))[:3]
        interesting_files.extend(controllers)
        
        # Look for middleware files
        middleware = list(aspnetcore_path.rglob("*Middleware.cs"))[:2]
        interesting_files.extend(middleware)
        
        # Look for startup files
        startup = list(aspnetcore_path.rglob("Startup.cs"))[:1]
        interesting_files.extend(startup)
    
    # Umbraco CMS files
    umbraco_path = base_path / "Umbraco-CMS"
    if umbraco_path.exists():
        # Look for API controllers
        api_controllers = list(umbraco_path.rglob("*ApiController.cs"))[:2]
        interesting_files.extend(api_controllers)
        
        # Look for service files
        services = list(umbraco_path.rglob("*Service.cs"))[:2]
        interesting_files.extend(services)
    
    # Orchard Core files
    orchard_path = base_path / "OrchardCore"
    if orchard_path.exists():
        # Look for module files
        modules = list(orchard_path.rglob("*Module.cs"))[:2]
        interesting_files.extend(modules)
        
        # Look for handler files
        handlers = list(orchard_path.rglob("*Handler.cs"))[:2]
        interesting_files.extend(handlers)
    
    # ABP Framework files
    abp_path = base_path / "abp"
    if abp_path.exists():
        # Look for application service files
        app_services = list(abp_path.rglob("*AppService.cs"))[:2]
        interesting_files.extend(app_services)
        
        # Look for domain service files
        domain_services = list(abp_path.rglob("*DomainService.cs"))[:1]
        interesting_files.extend(domain_services)
    
    return interesting_files[:15]  # Limit to 15 files for the showcase


def analyze_file_deeply(plugin: Plugin, file_path: Path) -> Dict[str, Any]:
    """Perform deep analysis of a C# file."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        result = plugin.indexFile(str(file_path), content)
        
        if not isinstance(result, dict) or 'symbols' not in result:
            return {"error": "No symbols found"}
        
        symbols = result['symbols']
        
        # Analyze symbol patterns
        analysis = {
            "file_path": str(file_path),
            "file_size": len(content),
            "line_count": len(content.splitlines()),
            "symbol_count": len(symbols),
            "symbol_types": {},
            "interesting_features": [],
            "framework_info": {},
            "complexity_indicators": {}
        }
        
        # Count symbol types
        for symbol in symbols:
            if isinstance(symbol, dict):
                symbol_type = symbol.get('kind', 'unknown')
                analysis["symbol_types"][symbol_type] = analysis["symbol_types"].get(symbol_type, 0) + 1
        
        # Extract interesting features
        async_methods = []
        generic_symbols = []
        attributed_symbols = []
        linq_symbols = []
        inheritance_symbols = []
        
        for symbol in symbols:
            if isinstance(symbol, dict):
                metadata = symbol.get('metadata', {})
                
                # Check for async methods
                if 'async' in symbol.get('modifiers', []) or 'async' in symbol.get('signature', '').lower():
                    async_methods.append(symbol['symbol'])
                
                # Check for generics
                if metadata.get('generics', {}).get('is_generic'):
                    generic_symbols.append({
                        'name': symbol['symbol'],
                        'type_parameters': metadata['generics'].get('type_parameters', [])
                    })
                
                # Check for attributes
                if metadata.get('attributes'):
                    attributed_symbols.append({
                        'name': symbol['symbol'],
                        'attributes': metadata['attributes']
                    })
                
                # Check for LINQ usage
                if metadata.get('uses_linq'):
                    linq_symbols.append(symbol['symbol'])
                
                # Check for inheritance
                if metadata.get('inheritance', {}).get('has_inheritance'):
                    inheritance_symbols.append({
                        'name': symbol['symbol'],
                        'base_types': metadata['inheritance'].get('base_types', [])
                    })
                
                # Extract framework info from first symbol with metadata
                if not analysis["framework_info"] and metadata.get('target_framework'):
                    analysis["framework_info"] = {
                        'target_framework': metadata.get('target_framework'),
                        'project_type': metadata.get('project_type'),
                        'framework_version': metadata.get('framework_version')
                    }
        
        # Store interesting features
        if async_methods:
            analysis["interesting_features"].append(f"Async/await pattern (methods: {', '.join(async_methods[:3])})")
        
        if generic_symbols:
            analysis["interesting_features"].append(f"Generic types ({len(generic_symbols)} found)")
            
        if attributed_symbols:
            analysis["interesting_features"].append(f"Attributes usage ({len(attributed_symbols)} symbols)")
            
        if linq_symbols:
            analysis["interesting_features"].append(f"LINQ expressions ({len(linq_symbols)} symbols)")
            
        if inheritance_symbols:
            analysis["interesting_features"].append(f"Inheritance ({len(inheritance_symbols)} classes)")
        
        # Calculate complexity indicators
        analysis["complexity_indicators"] = {
            "symbols_per_line": analysis["symbol_count"] / analysis["line_count"] if analysis["line_count"] > 0 else 0,
            "method_to_class_ratio": analysis["symbol_types"].get("function", 0) / max(analysis["symbol_types"].get("class", 1), 1),
            "property_usage": analysis["symbol_types"].get("property", 0),
            "has_multiple_namespaces": analysis["symbol_types"].get("namespace", 0) > 1
        }
        
        # Add detailed symbol breakdown for top symbols
        analysis["top_symbols"] = []
        for symbol in symbols[:5]:
            if isinstance(symbol, dict):
                symbol_info = {
                    "name": symbol['symbol'],
                    "type": symbol.get('kind'),
                    "line": symbol.get('line'),
                    "signature": symbol.get('signature', '')[:100] + "..." if len(symbol.get('signature', '')) > 100 else symbol.get('signature', '')
                }
                
                metadata = symbol.get('metadata', {})
                if metadata.get('attributes'):
                    symbol_info["attributes"] = metadata['attributes']
                if metadata.get('generics', {}).get('is_generic'):
                    symbol_info["generic"] = True
                if metadata.get('inheritance', {}).get('has_inheritance'):
                    symbol_info["inherits_from"] = metadata['inheritance'].get('base_types', [])
                
                analysis["top_symbols"].append(symbol_info)
        
        return analysis
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Main showcase function."""
    print("🎯 C# Plugin Advanced Capabilities Showcase")
    print("=" * 60)
    
    # Initialize plugin
    plugin = Plugin()
    
    # Find interesting files
    print("🔍 Finding interesting C# files from real-world projects...")
    interesting_files = find_interesting_files()
    
    if not interesting_files:
        print("❌ No interesting files found. Make sure repositories are cloned.")
        return
    
    print(f"📁 Found {len(interesting_files)} interesting files to analyze")
    
    showcase_results = []
    
    for i, file_path in enumerate(interesting_files):
        print(f"\n📄 Analyzing file {i+1}/{len(interesting_files)}: {file_path.name}")
        print(f"   Path: {file_path.relative_to(Path('/home/jenner/Code/Code-Index-MCP/test_repos/csharp_test'))}")
        
        analysis = analyze_file_deeply(plugin, file_path)
        
        if "error" in analysis:
            print(f"   ❌ Error: {analysis['error']}")
            continue
        
        showcase_results.append(analysis)
        
        # Print summary
        print(f"   📊 {analysis['symbol_count']} symbols, {analysis['line_count']} lines")
        print(f"   🔧 Symbol types: {', '.join(f'{k}:{v}' for k, v in analysis['symbol_types'].items())}")
        
        if analysis['framework_info']:
            fw = analysis['framework_info']
            print(f"   🏗️  Framework: {fw.get('target_framework', 'N/A')} ({fw.get('project_type', 'N/A')})")
        
        if analysis['interesting_features']:
            print(f"   ⭐ Features: {analysis['interesting_features'][0]}")
            if len(analysis['interesting_features']) > 1:
                print(f"              +{len(analysis['interesting_features'])-1} more")
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📋 SHOWCASE SUMMARY")
    print("=" * 60)
    
    if not showcase_results:
        print("❌ No files successfully analyzed.")
        return
    
    total_symbols = sum(r['symbol_count'] for r in showcase_results)
    total_lines = sum(r['line_count'] for r in showcase_results)
    
    print(f"✅ Files analyzed: {len(showcase_results)}")
    print(f"🔍 Total symbols extracted: {total_symbols}")
    print(f"📄 Total lines processed: {total_lines}")
    print(f"⚡ Avg symbols per file: {total_symbols / len(showcase_results):.1f}")
    
    # Aggregate symbol types
    all_symbol_types = {}
    for result in showcase_results:
        for symbol_type, count in result['symbol_types'].items():
            all_symbol_types[symbol_type] = all_symbol_types.get(symbol_type, 0) + count
    
    print(f"\n🔧 Symbol type distribution:")
    for symbol_type, count in sorted(all_symbol_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_symbols) * 100
        print(f"   {symbol_type}: {count} ({percentage:.1f}%)")
    
    # Framework analysis
    frameworks = {}
    project_types = {}
    for result in showcase_results:
        fw_info = result.get('framework_info', {})
        if fw_info.get('target_framework'):
            frameworks[fw_info['target_framework']] = frameworks.get(fw_info['target_framework'], 0) + 1
        if fw_info.get('project_type'):
            project_types[fw_info['project_type']] = project_types.get(fw_info['project_type'], 0) + 1
    
    if frameworks:
        print(f"\n🏗️  Target frameworks detected:")
        for fw, count in frameworks.items():
            print(f"   {fw}: {count} files")
    
    if project_types:
        print(f"\n📦 Project types detected:")
        for pt, count in project_types.items():
            print(f"   {pt}: {count} files")
    
    # Advanced features summary
    print(f"\n⭐ Advanced features detected:")
    feature_counts = {}
    for result in showcase_results:
        for feature in result.get('interesting_features', []):
            feature_type = feature.split('(')[0].strip()
            feature_counts[feature_type] = feature_counts.get(feature_type, 0) + 1
    
    for feature, count in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {feature}: {count} files")
    
    # Save detailed report
    report_path = Path("csharp_plugin_showcase_report.json")
    with open(report_path, 'w') as f:
        json.dump(showcase_results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed showcase report saved to: {report_path.absolute()}")
    print("\n🎯 C# Plugin Showcase completed successfully!")


if __name__ == "__main__":
    main()