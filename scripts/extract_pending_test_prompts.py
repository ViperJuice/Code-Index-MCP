#!/usr/bin/env python3
"""
Extract prompts for pending tests from batch configurations.
"""
import json
from pathlib import Path

# Load pending tests
with open('test_results/performance_tests/pending_tests.json', 'r') as f:
    pending_data = json.load(f)

pending_tests = set(pending_data['pending_tests'])

# Load batch configurations and extract prompts
test_prompts = {}
batch_dir = Path('test_results/performance_tests')

for batch_file in batch_dir.glob('test_batch_*_fixed.json'):
    with open(batch_file, 'r') as f:
        batch_data = json.load(f)
        for test in batch_data['tests']:
            if test['test_id'] in pending_tests:
                test_prompts[test['test_id']] = {
                    'prompt': test['prompt'],
                    'mode': test['mode'],
                    'query_info': test['query_info']
                }

# Save prompts grouped by repository
output = {
    'total_pending': len(pending_tests),
    'by_repository': {}
}

for repo, test_ids in pending_data['by_repository'].items():
    output['by_repository'][repo] = []
    for test_id in test_ids:
        if test_id in test_prompts:
            output['by_repository'][repo].append({
                'test_id': test_id,
                'mode': test_prompts[test_id]['mode'],
                'query': test_prompts[test_id]['query_info']['query'],
                'category': test_prompts[test_id]['query_info']['category'],
                'prompt': test_prompts[test_id]['prompt']
            })

# Save to file
output_file = batch_dir / 'pending_test_prompts.json'
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Extracted {len(test_prompts)} test prompts")
print(f"Saved to: {output_file}")

# Also create individual files for easier execution
for repo, tests in output['by_repository'].items():
    repo_file = batch_dir / f'pending_{repo}_prompts.json'
    with open(repo_file, 'w') as f:
        json.dump(tests, f, indent=2)
    print(f"Created: {repo_file} ({len(tests)} tests)")