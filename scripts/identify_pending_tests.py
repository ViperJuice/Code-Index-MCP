#!/usr/bin/env python3
"""
Identify pending tests by comparing batch configurations with completed results.
"""
import json
from pathlib import Path

# Get all configured tests
all_tests = set()
batch_dir = Path('test_results/performance_tests')

for batch_file in batch_dir.glob('test_batch_*_fixed.json'):
    with open(batch_file, 'r') as f:
        batch_data = json.load(f)
        for test in batch_data['tests']:
            all_tests.add(test['test_id'])

print(f"Total configured tests: {len(all_tests)}")

# Get completed tests
completed_tests = set()
results_dir = batch_dir / 'results'

for result_file in results_dir.glob('result_*.json'):
    with open(result_file, 'r') as f:
        result = json.load(f)
        test_id = result.get('test_id')
        if test_id:
            completed_tests.add(test_id)

print(f"Completed tests: {len(completed_tests)}")

# Find pending tests
pending_tests = all_tests - completed_tests
print(f"Pending tests: {len(pending_tests)}")

# Group by repository
by_repo = {}
for test_id in sorted(pending_tests):
    repo = test_id.split('_')[0] + '_' + test_id.split('_')[1]
    if repo not in by_repo:
        by_repo[repo] = []
    by_repo[repo].append(test_id)

print("\nPending tests by repository:")
for repo, tests in by_repo.items():
    print(f"\n{repo}: {len(tests)} tests")
    for test in sorted(tests)[:5]:  # Show first 5
        print(f"  - {test}")
    if len(tests) > 5:
        print(f"  ... and {len(tests) - 5} more")

# Save pending tests list
pending_file = batch_dir / 'pending_tests.json'
with open(pending_file, 'w') as f:
    json.dump({
        'total_configured': len(all_tests),
        'total_completed': len(completed_tests),
        'total_pending': len(pending_tests),
        'pending_tests': sorted(pending_tests),
        'by_repository': by_repo
    }, f, indent=2)

print(f"\nPending tests saved to: {pending_file}")