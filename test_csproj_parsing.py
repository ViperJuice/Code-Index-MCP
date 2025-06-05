#!/usr/bin/env python3
"""
Test C# plugin's .csproj file parsing capabilities.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.csharp_plugin.plugin import Plugin


def find_csproj_files() -> List[Path]:
    """Find interesting .csproj files from the repositories."""
    base_path = Path("/home/jenner/Code/Code-Index-MCP/test_repos/csharp_test")
    
    csproj_files = []
    
    # Find different types of projects
    for repo in ["aspnetcore", "Umbraco-CMS", "OrchardCore", "abp"]:
        repo_path = base_path / repo
        if repo_path.exists():
            # Get a sample of .csproj files
            projects = list(repo_path.rglob("*.csproj"))[:10]
            csproj_files.extend(projects)
    
    return csproj_files[:20]  # Limit to 20 for the test


def test_csproj_parsing(plugin: Plugin, csproj_files: List[Path]) -> List[Dict[str, Any]]:
    """Test .csproj file parsing by indexing related C# files."""
    results = []
    
    for csproj_file in csproj_files:
        try:
            # Find C# files in the same directory
            project_dir = csproj_file.parent
            cs_files = list(project_dir.rglob("*.cs"))
            
            if not cs_files:
                continue
            
            # Test with the first C# file to see if project info is detected
            test_file = cs_files[0]
            if test_file.stat().st_size > 1024 * 1024:  # Skip very large files
                continue
                
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            result = plugin.indexFile(str(test_file), content)
            
            if isinstance(result, dict) and 'symbols' in result and result['symbols']:
                first_symbol = result['symbols'][0]
                if isinstance(first_symbol, dict) and 'metadata' in first_symbol:
                    metadata = first_symbol['metadata']
                    
                    project_info = {
                        'csproj_file': str(csproj_file.relative_to(Path("/home/jenner/Code/Code-Index-MCP/test_repos/csharp_test"))),
                        'test_cs_file': str(test_file.relative_to(project_dir)),
                        'target_framework': metadata.get('target_framework'),
                        'project_type': metadata.get('project_type'),
                        'framework_version': metadata.get('framework_version'),
                        'has_project_info': bool(metadata.get('target_framework') or metadata.get('project_type'))
                    }
                    
                    # Try to read and parse the .csproj file directly
                    try:
                        csproj_content = csproj_file.read_text(encoding='utf-8')
                        project_info['csproj_size'] = len(csproj_content)
                        project_info['csproj_lines'] = len(csproj_content.splitlines())
                        
                        # Extract some key information from .csproj
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(csproj_content)
                        
                        # Extract SDK information
                        sdk = root.get('Sdk', '')
                        if sdk:
                            project_info['sdk'] = sdk
                        
                        # Extract target framework from XML
                        target_fw = root.find('.//TargetFramework')
                        if target_fw is not None:
                            project_info['xml_target_framework'] = target_fw.text
                        
                        target_fws = root.find('.//TargetFrameworks')
                        if target_fws is not None:
                            project_info['xml_target_frameworks'] = target_fws.text
                        
                        # Extract output type
                        output_type = root.find('.//OutputType')
                        if output_type is not None:
                            project_info['xml_output_type'] = output_type.text
                        
                        # Count package references
                        package_refs = root.findall('.//PackageReference')
                        project_info['package_references_count'] = len(package_refs)
                        
                        # Extract some package names
                        packages = []
                        for pkg in package_refs[:5]:  # First 5 packages
                            include = pkg.get('Include')
                            version = pkg.get('Version', pkg.find('Version'))
                            if version is not None and hasattr(version, 'text'):
                                version = version.text
                            if include:
                                packages.append(f"{include}:{version}" if version else include)
                        project_info['sample_packages'] = packages
                        
                        # Check for specific project types
                        if root.find('.//UseWPF') is not None:
                            project_info['is_wpf'] = True
                        if root.find('.//UseWindowsForms') is not None:
                            project_info['is_winforms'] = True
                        if any(ref.get('Include', '').startswith('Microsoft.AspNetCore') for ref in package_refs):
                            project_info['is_aspnetcore'] = True
                        if any(ref.get('Include', '').startswith('Microsoft.EntityFrameworkCore') for ref in package_refs):
                            project_info['uses_ef_core'] = True
                        
                    except Exception as xml_error:
                        project_info['csproj_parse_error'] = str(xml_error)
                    
                    results.append(project_info)
        
        except Exception as e:
            results.append({
                'csproj_file': str(csproj_file),
                'error': str(e)
            })
    
    return results


def main():
    """Main function to test .csproj parsing capabilities."""
    print("📦 C# Plugin .csproj File Parsing Test")
    print("=" * 50)
    
    # Initialize plugin
    plugin = Plugin()
    
    # Find .csproj files
    print("🔍 Finding .csproj files from repositories...")
    csproj_files = find_csproj_files()
    
    if not csproj_files:
        print("❌ No .csproj files found. Make sure repositories are cloned.")
        return
    
    print(f"📁 Found {len(csproj_files)} .csproj files to test")
    
    # Test .csproj parsing
    print("\n🧪 Testing .csproj file parsing capabilities...")
    results = test_csproj_parsing(plugin, csproj_files)
    
    # Filter successful results
    successful_results = [r for r in results if 'error' not in r]
    error_results = [r for r in results if 'error' in r]
    
    print(f"\n✅ Successfully processed: {len(successful_results)}")
    print(f"❌ Errors encountered: {len(error_results)}")
    
    if not successful_results:
        print("❌ No successful .csproj parsing results to analyze.")
        return
    
    # Analyze results
    print("\n📊 .csproj Parsing Analysis")
    print("-" * 30)
    
    # Count project types
    project_types = {}
    target_frameworks = {}
    sdks = {}
    
    total_with_project_info = 0
    total_package_refs = 0
    
    for result in successful_results:
        if result.get('has_project_info'):
            total_with_project_info += 1
        
        # Count project types
        if result.get('project_type'):
            pt = result['project_type']
            project_types[pt] = project_types.get(pt, 0) + 1
        
        # Count target frameworks
        if result.get('target_framework'):
            tf = result['target_framework']
            target_frameworks[tf] = target_frameworks.get(tf, 0) + 1
        
        # Count SDKs
        if result.get('sdk'):
            sdk = result['sdk']
            sdks[sdk] = sdks.get(sdk, 0) + 1
        
        # Count package references
        total_package_refs += result.get('package_references_count', 0)
    
    print(f"🎯 Project info detection rate: {total_with_project_info}/{len(successful_results)} ({100*total_with_project_info/len(successful_results):.1f}%)")
    
    if project_types:
        print(f"\n🏗️  Project types detected:")
        for pt, count in sorted(project_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {pt}: {count}")
    
    if target_frameworks:
        print(f"\n🎯 Target frameworks detected:")
        for tf, count in sorted(target_frameworks.items(), key=lambda x: x[1], reverse=True):
            print(f"   {tf}: {count}")
    
    if sdks:
        print(f"\n🔧 SDKs detected:")
        for sdk, count in sorted(sdks.items(), key=lambda x: x[1], reverse=True):
            print(f"   {sdk}: {count}")
    
    print(f"\n📦 Total package references: {total_package_refs}")
    print(f"📦 Avg packages per project: {total_package_refs/len(successful_results):.1f}")
    
    # Show specific project features
    feature_counts = {
        'is_wpf': 0,
        'is_winforms': 0,
        'is_aspnetcore': 0,
        'uses_ef_core': 0
    }
    
    for result in successful_results:
        for feature in feature_counts:
            if result.get(feature):
                feature_counts[feature] += 1
    
    print(f"\n⭐ Special project features:")
    feature_names = {
        'is_wpf': 'WPF projects',
        'is_winforms': 'Windows Forms projects',
        'is_aspnetcore': 'ASP.NET Core projects',
        'uses_ef_core': 'Entity Framework Core projects'
    }
    
    for feature, count in feature_counts.items():
        if count > 0:
            print(f"   {feature_names[feature]}: {count}")
    
    # Show sample projects with detailed info
    print(f"\n📋 Sample Project Details:")
    print("-" * 30)
    
    for i, result in enumerate(successful_results[:5]):
        print(f"\n{i+1}. {Path(result['csproj_file']).name}")
        print(f"   📁 Path: {result['csproj_file']}")
        print(f"   🎯 Framework: {result.get('target_framework', 'N/A')}")
        print(f"   🏗️  Type: {result.get('project_type', 'N/A')}")
        print(f"   🔧 SDK: {result.get('sdk', 'N/A')}")
        if result.get('sample_packages'):
            print(f"   📦 Packages: {', '.join(result['sample_packages'][:3])}")
            if len(result.get('sample_packages', [])) > 3:
                print(f"              +{len(result['sample_packages'])-3} more")
    
    # Save detailed report
    report_path = Path("csproj_parsing_test_report.json")
    with open(report_path, 'w') as f:
        json.dump({
            'summary': {
                'total_projects_tested': len(csproj_files),
                'successful_parsing': len(successful_results),
                'error_count': len(error_results),
                'project_info_detection_rate': total_with_project_info / len(successful_results) if successful_results else 0,
                'total_package_references': total_package_refs
            },
            'project_types': project_types,
            'target_frameworks': target_frameworks,
            'sdks': sdks,
            'feature_counts': feature_counts,
            'detailed_results': successful_results,
            'errors': error_results
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_path.absolute()}")
    print("\n✅ .csproj parsing test completed successfully!")


if __name__ == "__main__":
    main()