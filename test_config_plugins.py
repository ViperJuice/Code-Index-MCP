#!/usr/bin/env python3
"""
Configuration Plugin Testing Script for DevOps Repositories

Tests our configuration plugins against real-world DevOps and infrastructure repositories:
- Kubernetes (YAML-heavy)
- Docker Compose
- GitHub Actions
- Helm Charts

Validates plugin effectiveness for:
1. YAML configuration analysis
2. JSON configuration parsing
3. Markdown documentation
4. CSV data handling
5. DevOps workflow patterns
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any
import sqlite3

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.config.settings import Settings


class ConfigPluginTester:
    """Test configuration plugins against DevOps repositories."""
    
    def __init__(self, test_repos_path: str):
        self.test_repos_path = Path(test_repos_path)
        self.results = {
            'yaml_analysis': [],
            'json_analysis': [],
            'markdown_analysis': [],
            'csv_analysis': [],
            'devops_patterns': [],
            'performance_metrics': {}
        }
        
        # Initialize plugin manager and storage
        self.settings = Settings()
        self.store = SQLiteStore(":memory:")
        self.plugin_manager = PluginManager(sqlite_store=self.store)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def discover_config_files(self) -> Dict[str, List[Path]]:
        """Discover configuration files by type."""
        file_types = {
            'yaml': [],
            'json': [],
            'markdown': [],
            'csv': []
        }
        
        patterns = {
            'yaml': ['*.yaml', '*.yml'],
            'json': ['*.json'],
            'markdown': ['*.md'],
            'csv': ['*.csv']
        }
        
        for file_type, extensions in patterns.items():
            for ext in extensions:
                for file_path in self.test_repos_path.rglob(ext):
                    # Skip hidden files and node_modules
                    if not any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
                        file_types[file_type].append(file_path)
        
        return file_types
    
    def test_yaml_plugin(self, yaml_files: List[Path]) -> Dict[str, Any]:
        """Test YAML plugin on Kubernetes and Helm configurations."""
        results = {
            'files_processed': 0,
            'successful_parses': 0,
            'errors': [],
            'k8s_resources': [],
            'helm_charts': [],
            'ci_cd_configs': []
        }
        
        for yaml_file in yaml_files[:50]:  # Limit for testing
            try:
                self.logger.info(f"Processing YAML file: {yaml_file}")
                
                # Use our plugin system to index the file
                plugin = self.plugin_manager.get_plugin_for_file(str(yaml_file))
                if plugin:
                    index_result = plugin.index_file(str(yaml_file))
                    
                    results['files_processed'] += 1
                    if index_result and index_result.symbols:
                        results['successful_parses'] += 1
                        
                        # Categorize based on content
                        content = yaml_file.read_text(encoding='utf-8', errors='ignore')
                        
                        # Kubernetes resources
                        if any(k8s_key in content for k8s_key in ['apiVersion', 'kind', 'metadata']):
                            results['k8s_resources'].append({
                                'file': str(yaml_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'kubernetes'
                            })
                        
                        # Helm charts
                        elif 'Chart.yaml' in str(yaml_file) or 'values.yaml' in str(yaml_file):
                            results['helm_charts'].append({
                                'file': str(yaml_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'helm'
                            })
                        
                        # CI/CD configurations
                        elif any(ci_indicator in str(yaml_file) for ci_indicator in ['.github', 'workflows', 'ci']):
                            results['ci_cd_configs'].append({
                                'file': str(yaml_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'ci_cd'
                            })
                
            except Exception as e:
                results['errors'].append({
                    'file': str(yaml_file),
                    'error': str(e)
                })
        
        return results
    
    def test_json_plugin(self, json_files: List[Path]) -> Dict[str, Any]:
        """Test JSON plugin on package configurations."""
        results = {
            'files_processed': 0,
            'successful_parses': 0,
            'errors': [],
            'package_configs': [],
            'config_files': []
        }
        
        for json_file in json_files[:30]:  # Limit for testing
            try:
                self.logger.info(f"Processing JSON file: {json_file}")
                
                plugin = self.plugin_manager.get_plugin_for_file(str(json_file))
                if plugin:
                    index_result = plugin.index_file(str(json_file))
                    
                    results['files_processed'] += 1
                    if index_result and index_result.symbols:
                        results['successful_parses'] += 1
                        
                        # Categorize JSON files
                        filename = json_file.name.lower()
                        if filename in ['package.json', 'composer.json', 'pom.json']:
                            results['package_configs'].append({
                                'file': str(json_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'package_manager'
                            })
                        else:
                            results['config_files'].append({
                                'file': str(json_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'configuration'
                            })
                
            except Exception as e:
                results['errors'].append({
                    'file': str(json_file),
                    'error': str(e)
                })
        
        return results
    
    def test_markdown_plugin(self, markdown_files: List[Path]) -> Dict[str, Any]:
        """Test Markdown plugin on documentation."""
        results = {
            'files_processed': 0,
            'successful_parses': 0,
            'errors': [],
            'readme_files': [],
            'documentation': [],
            'changelogs': []
        }
        
        for md_file in markdown_files[:40]:  # Limit for testing
            try:
                self.logger.info(f"Processing Markdown file: {md_file}")
                
                plugin = self.plugin_manager.get_plugin_for_file(str(md_file))
                if plugin:
                    index_result = plugin.index_file(str(md_file))
                    
                    results['files_processed'] += 1
                    if index_result and index_result.symbols:
                        results['successful_parses'] += 1
                        
                        # Categorize markdown files
                        filename = md_file.name.lower()
                        if filename == 'readme.md':
                            results['readme_files'].append({
                                'file': str(md_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'readme'
                            })
                        elif 'changelog' in filename:
                            results['changelogs'].append({
                                'file': str(md_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'changelog'
                            })
                        else:
                            results['documentation'].append({
                                'file': str(md_file),
                                'symbols_count': len(index_result.symbols),
                                'type': 'documentation'
                            })
                
            except Exception as e:
                results['errors'].append({
                    'file': str(md_file),
                    'error': str(e)
                })
        
        return results
    
    def analyze_devops_patterns(self, discovered_files: Dict[str, List[Path]]) -> Dict[str, Any]:
        """Analyze DevOps and infrastructure patterns."""
        patterns = {
            'kubernetes_manifests': 0,
            'docker_configs': 0,
            'ci_cd_pipelines': 0,
            'helm_charts': 0,
            'github_actions': 0,
            'infrastructure_as_code': 0
        }
        
        all_files = []
        for file_list in discovered_files.values():
            all_files.extend(file_list)
        
        for file_path in all_files:
            file_str = str(file_path).lower()
            
            # Kubernetes patterns
            if any(k8s in file_str for k8s in ['deployment.yaml', 'service.yaml', 'configmap.yaml', 'ingress.yaml']):
                patterns['kubernetes_manifests'] += 1
            
            # Docker patterns
            elif any(docker in file_str for docker in ['dockerfile', 'docker-compose', '.dockerignore']):
                patterns['docker_configs'] += 1
            
            # CI/CD patterns
            elif '.github/workflows' in file_str:
                patterns['github_actions'] += 1
            elif any(ci in file_str for ci in ['ci.yml', 'ci.yaml', 'pipeline', 'build.yml']):
                patterns['ci_cd_pipelines'] += 1
            
            # Helm patterns
            elif any(helm in file_str for helm in ['chart.yaml', 'values.yaml', 'templates/']):
                patterns['helm_charts'] += 1
            
            # Infrastructure as Code
            elif any(iac in file_str for iac in ['terraform', '.tf', 'cloudformation', 'pulumi']):
                patterns['infrastructure_as_code'] += 1
        
        return patterns
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive configuration plugin tests."""
        self.logger.info("Starting comprehensive configuration plugin tests...")
        
        # Discover files
        discovered_files = self.discover_config_files()
        
        self.logger.info(f"Discovered files:")
        for file_type, files in discovered_files.items():
            self.logger.info(f"  {file_type}: {len(files)} files")
        
        # Test each plugin type
        self.results['yaml_analysis'] = self.test_yaml_plugin(discovered_files['yaml'])
        self.results['json_analysis'] = self.test_json_plugin(discovered_files['json'])
        self.results['markdown_analysis'] = self.test_markdown_plugin(discovered_files['markdown'])
        
        # Analyze DevOps patterns
        self.results['devops_patterns'] = self.analyze_devops_patterns(discovered_files)
        
        # Calculate performance metrics
        total_files = sum(len(files) for files in discovered_files.values())
        successful_parses = (
            self.results['yaml_analysis']['successful_parses'] +
            self.results['json_analysis']['successful_parses'] +
            self.results['markdown_analysis']['successful_parses']
        )
        
        self.results['performance_metrics'] = {
            'total_files_discovered': total_files,
            'total_files_processed': (
                self.results['yaml_analysis']['files_processed'] +
                self.results['json_analysis']['files_processed'] +
                self.results['markdown_analysis']['files_processed']
            ),
            'successful_parses': successful_parses,
            'success_rate': successful_parses / max(1, total_files) * 100,
            'file_type_distribution': {
                file_type: len(files) for file_type, files in discovered_files.items()
            }
        }
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        report = [
            "Configuration Plugin Test Report",
            "=" * 40,
            "",
            "Test Overview:",
            f"  Total files discovered: {self.results['performance_metrics']['total_files_discovered']}",
            f"  Total files processed: {self.results['performance_metrics']['total_files_processed']}",
            f"  Successful parses: {self.results['performance_metrics']['successful_parses']}",
            f"  Success rate: {self.results['performance_metrics']['success_rate']:.2f}%",
            "",
            "File Type Distribution:",
        ]
        
        for file_type, count in self.results['performance_metrics']['file_type_distribution'].items():
            report.append(f"  {file_type}: {count} files")
        
        report.extend([
            "",
            "YAML Plugin Analysis:",
            f"  Kubernetes resources: {len(self.results['yaml_analysis']['k8s_resources'])}",
            f"  Helm charts: {len(self.results['yaml_analysis']['helm_charts'])}",
            f"  CI/CD configs: {len(self.results['yaml_analysis']['ci_cd_configs'])}",
            f"  Errors: {len(self.results['yaml_analysis']['errors'])}",
            "",
            "JSON Plugin Analysis:",
            f"  Package configs: {len(self.results['json_analysis']['package_configs'])}",
            f"  Config files: {len(self.results['json_analysis']['config_files'])}",
            f"  Errors: {len(self.results['json_analysis']['errors'])}",
            "",
            "Markdown Plugin Analysis:",
            f"  README files: {len(self.results['markdown_analysis']['readme_files'])}",
            f"  Documentation: {len(self.results['markdown_analysis']['documentation'])}",
            f"  Changelogs: {len(self.results['markdown_analysis']['changelogs'])}",
            f"  Errors: {len(self.results['markdown_analysis']['errors'])}",
            "",
            "DevOps Pattern Analysis:",
        ])
        
        for pattern, count in self.results['devops_patterns'].items():
            report.append(f"  {pattern}: {count}")
        
        return "\n".join(report)


def main():
    """Main test execution."""
    test_repos_path = "/home/jenner/Code/Code-Index-MCP/test_repos/config_test"
    
    if not Path(test_repos_path).exists():
        print(f"Test repositories path not found: {test_repos_path}")
        return 1
    
    # Run tests
    tester = ConfigPluginTester(test_repos_path)
    results = tester.run_comprehensive_test()
    
    # Generate and save report
    report = tester.generate_report()
    print(report)
    
    # Save detailed results
    results_file = Path("config_plugin_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())