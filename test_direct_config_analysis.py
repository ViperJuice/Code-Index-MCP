#!/usr/bin/env python3
"""
Direct Configuration Analysis Test

Tests our indexing capabilities on specific configuration files from the cloned repositories.
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class DirectConfigAnalyzer:
    """Direct analysis of configuration files."""
    
    def __init__(self):
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_kubernetes_manifest(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Kubernetes manifest file."""
        try:
            self.logger.info(f"Analyzing Kubernetes manifest: {file_path}")
            
            # Read and parse the YAML
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Try to parse as YAML
            try:
                yaml_data = yaml.safe_load(content)
                if yaml_data and isinstance(yaml_data, dict):
                    result = {
                        'file': str(file_path),
                        'type': 'kubernetes_manifest',
                        'api_version': yaml_data.get('apiVersion', 'unknown'),
                        'kind': yaml_data.get('kind', 'unknown'),
                        'metadata': yaml_data.get('metadata', {}),
                        'parsed': True,
                        'line_count': len(content.split('\n')),
                        'size_bytes': len(content.encode('utf-8'))
                    }
                    
                    # Extract additional structure
                    if 'spec' in yaml_data:
                        result['has_spec'] = True
                        result['spec_keys'] = list(yaml_data['spec'].keys()) if isinstance(yaml_data['spec'], dict) else []
                    
                    return result
            except yaml.YAMLError as e:
                return {
                    'file': str(file_path),
                    'type': 'kubernetes_manifest',
                    'parsed': False,
                    'error': str(e),
                    'line_count': len(content.split('\n')),
                    'size_bytes': len(content.encode('utf-8'))
                }
                
        except Exception as e:
            return {
                'file': str(file_path),
                'type': 'kubernetes_manifest',
                'parsed': False,
                'error': str(e)
            }
    
    def analyze_helm_chart(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Helm chart file."""
        try:
            self.logger.info(f"Analyzing Helm chart: {file_path}")
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            try:
                yaml_data = yaml.safe_load(content)
                if yaml_data and isinstance(yaml_data, dict):
                    result = {
                        'file': str(file_path),
                        'type': 'helm_chart',
                        'parsed': True,
                        'line_count': len(content.split('\n')),
                        'size_bytes': len(content.encode('utf-8'))
                    }
                    
                    # Determine chart file type
                    if 'Chart.yaml' in str(file_path) or 'Chart.yml' in str(file_path):
                        result['chart_type'] = 'chart_metadata'
                        result['name'] = yaml_data.get('name', 'unknown')
                        result['version'] = yaml_data.get('version', 'unknown')
                        result['api_version'] = yaml_data.get('apiVersion', 'unknown')
                        result['dependencies'] = yaml_data.get('dependencies', [])
                    elif 'values.yaml' in str(file_path) or 'values.yml' in str(file_path):
                        result['chart_type'] = 'values'
                        result['value_keys'] = list(yaml_data.keys()) if isinstance(yaml_data, dict) else []
                    else:
                        result['chart_type'] = 'template'
                        if 'apiVersion' in yaml_data and 'kind' in yaml_data:
                            result['resource_type'] = yaml_data.get('kind', 'unknown')
                    
                    return result
            except yaml.YAMLError as e:
                return {
                    'file': str(file_path),
                    'type': 'helm_chart',
                    'parsed': False,
                    'error': str(e),
                    'line_count': len(content.split('\n')),
                    'size_bytes': len(content.encode('utf-8'))
                }
                
        except Exception as e:
            return {
                'file': str(file_path),
                'type': 'helm_chart',
                'parsed': False,
                'error': str(e)
            }
    
    def analyze_github_action(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a GitHub Actions workflow file."""
        try:
            self.logger.info(f"Analyzing GitHub Action: {file_path}")
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            try:
                yaml_data = yaml.safe_load(content)
                if yaml_data and isinstance(yaml_data, dict):
                    result = {
                        'file': str(file_path),
                        'type': 'github_action',
                        'name': yaml_data.get('name', 'unnamed'),
                        'parsed': True,
                        'line_count': len(content.split('\n')),
                        'size_bytes': len(content.encode('utf-8'))
                    }
                    
                    # Extract workflow details
                    if 'on' in yaml_data:
                        result['triggers'] = list(yaml_data['on'].keys()) if isinstance(yaml_data['on'], dict) else yaml_data['on']
                    
                    if 'jobs' in yaml_data:
                        result['job_count'] = len(yaml_data['jobs'])
                        result['job_names'] = list(yaml_data['jobs'].keys())
                    
                    return result
            except yaml.YAMLError as e:
                return {
                    'file': str(file_path),
                    'type': 'github_action',
                    'parsed': False,
                    'error': str(e),
                    'line_count': len(content.split('\n')),
                    'size_bytes': len(content.encode('utf-8'))
                }
                
        except Exception as e:
            return {
                'file': str(file_path),
                'type': 'github_action',
                'parsed': False,
                'error': str(e)
            }
    
    def analyze_docker_compose(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Docker Compose file."""
        try:
            self.logger.info(f"Analyzing Docker Compose: {file_path}")
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            try:
                yaml_data = yaml.safe_load(content)
                if yaml_data and isinstance(yaml_data, dict):
                    result = {
                        'file': str(file_path),
                        'type': 'docker_compose',
                        'version': yaml_data.get('version', 'unknown'),
                        'parsed': True,
                        'line_count': len(content.split('\n')),
                        'size_bytes': len(content.encode('utf-8'))
                    }
                    
                    # Extract service information
                    if 'services' in yaml_data:
                        services = yaml_data['services']
                        result['service_count'] = len(services)
                        result['service_names'] = list(services.keys())
                        
                        # Analyze service details
                        service_details = []
                        for name, config in services.items():
                            if isinstance(config, dict):
                                service_info = {'name': name}
                                if 'image' in config:
                                    service_info['image'] = config['image']
                                if 'ports' in config:
                                    service_info['has_ports'] = True
                                if 'volumes' in config:
                                    service_info['has_volumes'] = True
                                service_details.append(service_info)
                        result['services'] = service_details
                    
                    return result
            except yaml.YAMLError as e:
                return {
                    'file': str(file_path),
                    'type': 'docker_compose',
                    'parsed': False,
                    'error': str(e),
                    'line_count': len(content.split('\n')),
                    'size_bytes': len(content.encode('utf-8'))
                }
                
        except Exception as e:
            return {
                'file': str(file_path),
                'type': 'docker_compose',
                'parsed': False,
                'error': str(e)
            }
    
    def find_sample_files(self, test_repos_path: Path) -> Dict[str, List[Path]]:
        """Find sample files for each configuration type."""
        samples = {
            'kubernetes_manifests': [],
            'helm_charts': [],
            'github_actions': [],
            'docker_compose': []
        }
        
        # Find Kubernetes manifests
        k8s_patterns = ['deployment.yaml', 'service.yaml', 'configmap.yaml', 'ingress.yaml', 'pod.yaml']
        for pattern in k8s_patterns:
            for file_path in test_repos_path.rglob(f"*{pattern}"):
                if len(samples['kubernetes_manifests']) < 5:  # Limit samples
                    samples['kubernetes_manifests'].append(file_path)
        
        # Find Helm charts
        for file_path in test_repos_path.rglob("Chart.yaml"):
            if len(samples['helm_charts']) < 5:
                samples['helm_charts'].append(file_path)
        
        for file_path in test_repos_path.rglob("values.yaml"):
            if len(samples['helm_charts']) < 10:
                samples['helm_charts'].append(file_path)
        
        # Find GitHub Actions
        for file_path in test_repos_path.rglob(".github/workflows/*.yml"):
            if len(samples['github_actions']) < 5:
                samples['github_actions'].append(file_path)
        
        for file_path in test_repos_path.rglob(".github/workflows/*.yaml"):
            if len(samples['github_actions']) < 10:
                samples['github_actions'].append(file_path)
        
        # Find Docker Compose files
        compose_patterns = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
        for pattern in compose_patterns:
            for file_path in test_repos_path.rglob(pattern):
                if len(samples['docker_compose']) < 5:
                    samples['docker_compose'].append(file_path)
        
        return samples
    
    def run_analysis(self, test_repos_path: str) -> Dict[str, Any]:
        """Run direct configuration analysis."""
        test_path = Path(test_repos_path)
        
        if not test_path.exists():
            return {'error': f'Test path does not exist: {test_repos_path}'}
        
        # Find sample files
        samples = self.find_sample_files(test_path)
        
        results = {
            'kubernetes_analysis': [],
            'helm_analysis': [],
            'github_actions_analysis': [],
            'docker_compose_analysis': [],
            'summary': {}
        }
        
        # Analyze Kubernetes manifests
        for file_path in samples['kubernetes_manifests']:
            analysis = self.analyze_kubernetes_manifest(file_path)
            results['kubernetes_analysis'].append(analysis)
        
        # Analyze Helm charts
        for file_path in samples['helm_charts']:
            analysis = self.analyze_helm_chart(file_path)
            results['helm_analysis'].append(analysis)
        
        # Analyze GitHub Actions
        for file_path in samples['github_actions']:
            analysis = self.analyze_github_action(file_path)
            results['github_actions_analysis'].append(analysis)
        
        # Analyze Docker Compose
        for file_path in samples['docker_compose']:
            analysis = self.analyze_docker_compose(file_path)
            results['docker_compose_analysis'].append(analysis)
        
        # Generate summary
        results['summary'] = {
            'kubernetes_files_analyzed': len(results['kubernetes_analysis']),
            'kubernetes_parsed_successfully': sum(1 for a in results['kubernetes_analysis'] if a and a.get('parsed', False)),
            'helm_files_analyzed': len(results['helm_analysis']),
            'helm_parsed_successfully': sum(1 for a in results['helm_analysis'] if a and a.get('parsed', False)),
            'github_actions_analyzed': len(results['github_actions_analysis']),
            'github_actions_parsed_successfully': sum(1 for a in results['github_actions_analysis'] if a and a.get('parsed', False)),
            'docker_compose_analyzed': len(results['docker_compose_analysis']),
            'docker_compose_parsed_successfully': sum(1 for a in results['docker_compose_analysis'] if a and a.get('parsed', False))
        }
        
        return results


def main():
    """Main execution."""
    test_repos_path = "/home/jenner/Code/Code-Index-MCP/test_repos/config_test"
    
    analyzer = DirectConfigAnalyzer()
    results = analyzer.run_analysis(test_repos_path)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return 1
    
    # Print summary
    print("Direct Configuration Analysis Results")
    print("=" * 50)
    print()
    
    summary = results['summary']
    
    print("Kubernetes Manifests:")
    print(f"  Files analyzed: {summary['kubernetes_files_analyzed']}")
    print(f"  Successfully parsed: {summary['kubernetes_parsed_successfully']}")
    if summary['kubernetes_files_analyzed'] > 0:
        success_rate = (summary['kubernetes_parsed_successfully'] / summary['kubernetes_files_analyzed']) * 100
        print(f"  Success rate: {success_rate:.1f}%")
    print()
    
    print("Helm Charts:")
    print(f"  Files analyzed: {summary['helm_files_analyzed']}")
    print(f"  Successfully parsed: {summary['helm_parsed_successfully']}")
    if summary['helm_files_analyzed'] > 0:
        success_rate = (summary['helm_parsed_successfully'] / summary['helm_files_analyzed']) * 100
        print(f"  Success rate: {success_rate:.1f}%")
    print()
    
    print("GitHub Actions:")
    print(f"  Files analyzed: {summary['github_actions_analyzed']}")
    print(f"  Successfully parsed: {summary['github_actions_parsed_successfully']}")
    if summary['github_actions_analyzed'] > 0:
        success_rate = (summary['github_actions_parsed_successfully'] / summary['github_actions_analyzed']) * 100
        print(f"  Success rate: {success_rate:.1f}%")
    print()
    
    print("Docker Compose:")
    print(f"  Files analyzed: {summary['docker_compose_analyzed']}")
    print(f"  Successfully parsed: {summary['docker_compose_parsed_successfully']}")
    if summary['docker_compose_analyzed'] > 0:
        success_rate = (summary['docker_compose_parsed_successfully'] / summary['docker_compose_analyzed']) * 100
        print(f"  Success rate: {success_rate:.1f}%")
    print()
    
    # Show sample analyses
    if results['kubernetes_analysis']:
        print("Sample Kubernetes Analysis:")
        k8s_sample = results['kubernetes_analysis'][0]
        print(f"  File: {Path(k8s_sample['file']).name}")
        print(f"  Kind: {k8s_sample.get('kind', 'unknown')}")
        print(f"  API Version: {k8s_sample.get('api_version', 'unknown')}")
        print(f"  Parsed: {k8s_sample.get('parsed', False)}")
        print()
    
    if results['helm_analysis']:
        print("Sample Helm Analysis:")
        helm_sample = results['helm_analysis'][0]
        print(f"  File: {Path(helm_sample['file']).name}")
        print(f"  Chart Type: {helm_sample.get('chart_type', 'unknown')}")
        print(f"  Parsed: {helm_sample.get('parsed', False)}")
        print()
    
    # Save detailed results
    output_file = Path("direct_config_analysis_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Detailed results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())