#!/usr/bin/env python3
"""
DevOps Workflow Analysis

Analyzes CI/CD pipeline configurations, Infrastructure as Code files,
and DevOps patterns from the cloned repositories.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
import logging


class DevOpsWorkflowAnalyzer:
    """Analyze DevOps workflows and infrastructure patterns."""
    
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_github_actions_patterns(self, test_repos_path: Path) -> Dict[str, Any]:
        """Analyze GitHub Actions workflow patterns."""
        workflows = []
        
        # Find all GitHub Actions workflows
        workflow_files = list(test_repos_path.rglob(".github/workflows/*.yml")) + \
                        list(test_repos_path.rglob(".github/workflows/*.yaml"))
        
        for workflow_file in workflow_files:
            try:
                content = workflow_file.read_text(encoding='utf-8', errors='ignore')
                yaml_data = yaml.safe_load(content)
                
                if yaml_data and isinstance(yaml_data, dict):
                    workflow_info = {
                        'file': str(workflow_file.relative_to(test_repos_path)),
                        'name': yaml_data.get('name', 'Unnamed Workflow'),
                        'triggers': [],
                        'jobs': [],
                        'uses_actions': [],
                        'secrets_used': [],
                        'matrix_strategies': [],
                        'environments': []
                    }
                    
                    # Analyze triggers
                    if 'on' in yaml_data:
                        triggers = yaml_data['on']
                        if isinstance(triggers, dict):
                            workflow_info['triggers'] = list(triggers.keys())
                        elif isinstance(triggers, list):
                            workflow_info['triggers'] = triggers
                        else:
                            workflow_info['triggers'] = [triggers]
                    
                    # Analyze jobs
                    if 'jobs' in yaml_data:
                        jobs = yaml_data['jobs']
                        for job_name, job_config in jobs.items():
                            if isinstance(job_config, dict):
                                job_info = {
                                    'name': job_name,
                                    'runs_on': job_config.get('runs-on', 'unknown'),
                                    'steps_count': len(job_config.get('steps', [])),
                                    'needs': job_config.get('needs', []),
                                    'strategy': job_config.get('strategy', {}),
                                    'environment': job_config.get('environment', None)
                                }
                                
                                # Extract used actions
                                steps = job_config.get('steps', [])
                                for step in steps:
                                    if isinstance(step, dict) and 'uses' in step:
                                        action = step['uses']
                                        if action not in workflow_info['uses_actions']:
                                            workflow_info['uses_actions'].append(action)
                                    
                                    # Check for secrets
                                    step_str = str(step)
                                    if '${{ secrets.' in step_str or '${{secrets.' in step_str:
                                        import re
                                        secrets = re.findall(r'secrets\.(\w+)', step_str)
                                        workflow_info['secrets_used'].extend(secrets)
                                
                                # Matrix strategies
                                if 'strategy' in job_config and 'matrix' in job_config['strategy']:
                                    workflow_info['matrix_strategies'].append({
                                        'job': job_name,
                                        'matrix': job_config['strategy']['matrix']
                                    })
                                
                                # Environments
                                if 'environment' in job_config:
                                    env = job_config['environment']
                                    if env not in workflow_info['environments']:
                                        workflow_info['environments'].append(env)
                                
                                workflow_info['jobs'].append(job_info)
                    
                    # Remove duplicates
                    workflow_info['secrets_used'] = list(set(workflow_info['secrets_used']))
                    
                    workflows.append(workflow_info)
                    
            except Exception as e:
                self.logger.error(f"Error analyzing workflow {workflow_file}: {e}")
        
        return {
            'total_workflows': len(workflows),
            'workflows': workflows,
            'common_patterns': self._analyze_common_workflow_patterns(workflows)
        }
    
    def _analyze_common_workflow_patterns(self, workflows: List[Dict]) -> Dict[str, Any]:
        """Analyze common patterns across workflows."""
        patterns = {
            'most_common_triggers': {},
            'most_used_actions': {},
            'common_secrets': {},
            'runner_types': {},
            'workflow_categories': {
                'ci_cd': 0,
                'security': 0,
                'automation': 0,
                'release': 0
            }
        }
        
        for workflow in workflows:
            # Count triggers
            for trigger in workflow['triggers']:
                patterns['most_common_triggers'][trigger] = \
                    patterns['most_common_triggers'].get(trigger, 0) + 1
            
            # Count actions
            for action in workflow['uses_actions']:
                patterns['most_used_actions'][action] = \
                    patterns['most_used_actions'].get(action, 0) + 1
            
            # Count secrets
            for secret in workflow['secrets_used']:
                patterns['common_secrets'][secret] = \
                    patterns['common_secrets'].get(secret, 0) + 1
            
            # Count runner types
            for job in workflow['jobs']:
                runner = job['runs_on']
                if isinstance(runner, list):
                    runner = runner[0] if runner else 'unknown'
                patterns['runner_types'][runner] = \
                    patterns['runner_types'].get(runner, 0) + 1
            
            # Categorize workflows
            name_lower = workflow['name'].lower()
            if any(keyword in name_lower for keyword in ['test', 'build', 'ci', 'lint']):
                patterns['workflow_categories']['ci_cd'] += 1
            elif any(keyword in name_lower for keyword in ['security', 'codeql', 'scan']):
                patterns['workflow_categories']['security'] += 1
            elif any(keyword in name_lower for keyword in ['release', 'deploy', 'publish']):
                patterns['workflow_categories']['release'] += 1
            else:
                patterns['workflow_categories']['automation'] += 1
        
        # Sort by frequency
        patterns['most_common_triggers'] = dict(sorted(
            patterns['most_common_triggers'].items(), 
            key=lambda x: x[1], reverse=True
        ))
        patterns['most_used_actions'] = dict(sorted(
            patterns['most_used_actions'].items(), 
            key=lambda x: x[1], reverse=True
        ))
        
        return patterns
    
    def analyze_infrastructure_patterns(self, test_repos_path: Path) -> Dict[str, Any]:
        """Analyze infrastructure as code patterns."""
        infrastructure = {
            'kubernetes_resources': [],
            'docker_configurations': [],
            'helm_charts': [],
            'compose_services': []
        }
        
        # Kubernetes resources
        k8s_files = list(test_repos_path.rglob("*.yaml")) + list(test_repos_path.rglob("*.yml"))
        for k8s_file in k8s_files:
            if any(indicator in str(k8s_file).lower() for indicator in 
                   ['deployment', 'service', 'configmap', 'ingress', 'pod', 'namespace']):
                try:
                    content = k8s_file.read_text(encoding='utf-8', errors='ignore')
                    yaml_data = yaml.safe_load(content)
                    
                    if yaml_data and isinstance(yaml_data, dict) and \
                       'apiVersion' in yaml_data and 'kind' in yaml_data:
                        infrastructure['kubernetes_resources'].append({
                            'file': str(k8s_file.relative_to(test_repos_path)),
                            'kind': yaml_data.get('kind'),
                            'api_version': yaml_data.get('apiVersion'),
                            'namespace': yaml_data.get('metadata', {}).get('namespace', 'default')
                        })
                except:
                    pass
        
        # Docker configurations
        docker_files = list(test_repos_path.rglob("Dockerfile*")) + \
                      list(test_repos_path.rglob("docker-compose*.yml")) + \
                      list(test_repos_path.rglob("docker-compose*.yaml"))
        
        for docker_file in docker_files:
            if 'compose' in docker_file.name.lower():
                try:
                    content = docker_file.read_text(encoding='utf-8', errors='ignore')
                    yaml_data = yaml.safe_load(content)
                    
                    if yaml_data and 'services' in yaml_data:
                        services = yaml_data['services']
                        for service_name, service_config in services.items():
                            infrastructure['compose_services'].append({
                                'file': str(docker_file.relative_to(test_repos_path)),
                                'service': service_name,
                                'image': service_config.get('image', 'custom') if isinstance(service_config, dict) else 'unknown',
                                'has_ports': 'ports' in service_config if isinstance(service_config, dict) else False,
                                'has_volumes': 'volumes' in service_config if isinstance(service_config, dict) else False
                            })
                except:
                    pass
            else:
                infrastructure['docker_configurations'].append({
                    'file': str(docker_file.relative_to(test_repos_path)),
                    'type': 'dockerfile'
                })
        
        # Helm charts
        chart_files = list(test_repos_path.rglob("Chart.yaml")) + list(test_repos_path.rglob("Chart.yml"))
        for chart_file in chart_files:
            try:
                content = chart_file.read_text(encoding='utf-8', errors='ignore')
                yaml_data = yaml.safe_load(content)
                
                if yaml_data and isinstance(yaml_data, dict):
                    infrastructure['helm_charts'].append({
                        'file': str(chart_file.relative_to(test_repos_path)),
                        'name': yaml_data.get('name', 'unknown'),
                        'version': yaml_data.get('version', 'unknown'),
                        'dependencies': len(yaml_data.get('dependencies', []))
                    })
            except:
                pass
        
        return infrastructure
    
    def analyze_devops_maturity(self, workflows: Dict, infrastructure: Dict) -> Dict[str, Any]:
        """Analyze DevOps maturity indicators."""
        maturity = {
            'ci_cd_maturity': 0,
            'security_maturity': 0,
            'infrastructure_maturity': 0,
            'automation_maturity': 0,
            'indicators': []
        }
        
        # CI/CD Maturity
        if workflows['total_workflows'] > 0:
            maturity['ci_cd_maturity'] += 30
            maturity['indicators'].append('Has CI/CD workflows')
        
        if workflows['common_patterns']['workflow_categories']['ci_cd'] > 0:
            maturity['ci_cd_maturity'] += 25
            maturity['indicators'].append('Has dedicated CI/CD workflows')
        
        if 'push' in workflows['common_patterns']['most_common_triggers']:
            maturity['ci_cd_maturity'] += 20
            maturity['indicators'].append('Automated on push')
        
        if 'pull_request' in workflows['common_patterns']['most_common_triggers']:
            maturity['ci_cd_maturity'] += 25
            maturity['indicators'].append('PR validation')
        
        # Security Maturity
        if workflows['common_patterns']['workflow_categories']['security'] > 0:
            maturity['security_maturity'] += 40
            maturity['indicators'].append('Has security workflows')
        
        security_actions = [action for action in workflows['common_patterns']['most_used_actions'] 
                          if any(sec in action.lower() for sec in ['security', 'scan', 'codeql'])]
        if security_actions:
            maturity['security_maturity'] += 35
            maturity['indicators'].append('Uses security scanning actions')
        
        if workflows['common_patterns']['common_secrets']:
            maturity['security_maturity'] += 25
            maturity['indicators'].append('Uses secrets management')
        
        # Infrastructure Maturity
        if infrastructure['kubernetes_resources']:
            maturity['infrastructure_maturity'] += 40
            maturity['indicators'].append('Uses Kubernetes')
        
        if infrastructure['helm_charts']:
            maturity['infrastructure_maturity'] += 35
            maturity['indicators'].append('Uses Helm for package management')
        
        if infrastructure['compose_services']:
            maturity['infrastructure_maturity'] += 25
            maturity['indicators'].append('Uses Docker Compose')
        
        # Automation Maturity
        release_workflows = workflows['common_patterns']['workflow_categories']['release']
        if release_workflows > 0:
            maturity['automation_maturity'] += 35
            maturity['indicators'].append('Automated releases')
        
        matrix_usage = any(workflow.get('matrix_strategies') for workflow in workflows['workflows'])
        if matrix_usage:
            maturity['automation_maturity'] += 30
            maturity['indicators'].append('Uses matrix strategies')
        
        scheduled_workflows = 'schedule' in workflows['common_patterns']['most_common_triggers']
        if scheduled_workflows:
            maturity['automation_maturity'] += 35
            maturity['indicators'].append('Has scheduled automation')
        
        return maturity
    
    def run_comprehensive_analysis(self, test_repos_path: str) -> Dict[str, Any]:
        """Run comprehensive DevOps workflow analysis."""
        test_path = Path(test_repos_path)
        
        self.logger.info("Starting DevOps workflow analysis...")
        
        # Analyze GitHub Actions
        workflows = self.analyze_github_actions_patterns(test_path)
        self.logger.info(f"Found {workflows['total_workflows']} GitHub Actions workflows")
        
        # Analyze infrastructure
        infrastructure = self.analyze_infrastructure_patterns(test_path)
        self.logger.info(f"Found {len(infrastructure['kubernetes_resources'])} Kubernetes resources")
        self.logger.info(f"Found {len(infrastructure['helm_charts'])} Helm charts")
        self.logger.info(f"Found {len(infrastructure['compose_services'])} Docker Compose services")
        
        # Analyze maturity
        maturity = self.analyze_devops_maturity(workflows, infrastructure)
        
        return {
            'workflows': workflows,
            'infrastructure': infrastructure,
            'maturity': maturity,
            'summary': {
                'total_workflows': workflows['total_workflows'],
                'kubernetes_resources': len(infrastructure['kubernetes_resources']),
                'helm_charts': len(infrastructure['helm_charts']),
                'docker_configs': len(infrastructure['docker_configurations']),
                'compose_services': len(infrastructure['compose_services']),
                'ci_cd_maturity': maturity['ci_cd_maturity'],
                'security_maturity': maturity['security_maturity'],
                'infrastructure_maturity': maturity['infrastructure_maturity'],
                'automation_maturity': maturity['automation_maturity']
            }
        }


def main():
    """Main execution."""
    test_repos_path = "/home/jenner/Code/Code-Index-MCP/test_repos/config_test"
    
    if not Path(test_repos_path).exists():
        print(f"Test repositories path not found: {test_repos_path}")
        return 1
    
    analyzer = DevOpsWorkflowAnalyzer()
    results = analyzer.run_comprehensive_analysis(test_repos_path)
    
    # Print comprehensive report
    print("DevOps Workflow Analysis Report")
    print("=" * 50)
    print()
    
    summary = results['summary']
    print("Infrastructure Overview:")
    print(f"  GitHub Actions workflows: {summary['total_workflows']}")
    print(f"  Kubernetes resources: {summary['kubernetes_resources']}")
    print(f"  Helm charts: {summary['helm_charts']}")
    print(f"  Docker configurations: {summary['docker_configs']}")
    print(f"  Docker Compose services: {summary['compose_services']}")
    print()
    
    print("DevOps Maturity Scores (out of 100):")
    print(f"  CI/CD Maturity: {summary['ci_cd_maturity']}")
    print(f"  Security Maturity: {summary['security_maturity']}")
    print(f"  Infrastructure Maturity: {summary['infrastructure_maturity']}")
    print(f"  Automation Maturity: {summary['automation_maturity']}")
    print()
    
    print("Maturity Indicators:")
    for indicator in results['maturity']['indicators']:
        print(f"  ✓ {indicator}")
    print()
    
    if results['workflows']['common_patterns']['most_common_triggers']:
        print("Most Common Workflow Triggers:")
        for trigger, count in list(results['workflows']['common_patterns']['most_common_triggers'].items())[:5]:
            print(f"  {trigger}: {count} workflows")
        print()
    
    if results['workflows']['common_patterns']['most_used_actions']:
        print("Most Used GitHub Actions:")
        for action, count in list(results['workflows']['common_patterns']['most_used_actions'].items())[:5]:
            print(f"  {action}: {count} uses")
        print()
    
    # Save results
    output_file = Path("devops_workflow_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Detailed analysis saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())