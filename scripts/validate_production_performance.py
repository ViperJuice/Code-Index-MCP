#!/usr/bin/env python3
"""
Production Performance Validation Script
Validates that the deployed MCP Server meets performance requirements
"""

import os
import sys
import time
import json
import statistics
from typing import Dict, List, Tuple, Any
import httpx
import asyncio
from datetime import datetime
import concurrent.futures

# Configuration
DEPLOYMENT_URL = os.getenv("DEPLOYMENT_URL", "https://mcp-server.example.com")
API_TOKEN = os.getenv("API_TOKEN", "")
PARALLEL_REQUESTS = int(os.getenv("PARALLEL_REQUESTS", "10"))
TEST_DURATION = int(os.getenv("TEST_DURATION", "300"))  # 5 minutes

# Performance requirements
REQUIREMENTS = {
    "symbol_lookup_p95": 100,  # ms
    "semantic_search_p95": 500,  # ms
    "indexing_speed": 10000,  # files/minute
    "memory_usage_max": 2048,  # MB
    "error_rate_max": 0.01,  # 1%
}

class PerformanceValidator:
    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.results = {
            "symbol_lookups": [],
            "searches": [],
            "indexing": [],
            "errors": [],
            "metrics": {}
        }
        
    async def validate_all(self) -> Dict[str, Any]:
        """Run all validation tests."""
        print(f"Starting performance validation against {self.base_url}")
        print(f"Test duration: {TEST_DURATION} seconds")
        print("-" * 60)
        
        # Check health first
        if not await self.check_health():
            return {"success": False, "error": "Health check failed"}
        
        # Run tests concurrently
        start_time = time.time()
        
        tasks = [
            self.test_symbol_lookup_performance(),
            self.test_search_performance(),
            self.test_system_metrics(),
            self.monitor_errors()
        ]
        
        await asyncio.gather(*tasks)
        
        # Calculate results
        duration = time.time() - start_time
        validation_results = self.analyze_results(duration)
        
        return validation_results
    
    async def check_health(self) -> bool:
        """Check if the server is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def test_symbol_lookup_performance(self):
        """Test symbol lookup performance."""
        print("Testing symbol lookup performance...")
        
        # Test symbols
        symbols = [
            "main", "init", "process", "handle", "parse",
            "render", "update", "delete", "create", "validate",
            "Component", "Manager", "Service", "Controller", "Model"
        ]
        
        async def lookup_symbol(symbol: str) -> float:
            start = time.time()
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/symbol",
                        params={"symbol": symbol},
                        headers=self.headers,
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return (time.time() - start) * 1000  # ms
                    else:
                        self.results["errors"].append({
                            "type": "symbol_lookup",
                            "status": response.status_code,
                            "symbol": symbol
                        })
                        return None
            except Exception as e:
                self.results["errors"].append({
                    "type": "symbol_lookup",
                    "error": str(e),
                    "symbol": symbol
                })
                return None
        
        # Run continuous lookups
        end_time = time.time() + TEST_DURATION
        while time.time() < end_time:
            tasks = [lookup_symbol(symbol) for symbol in symbols]
            timings = await asyncio.gather(*tasks)
            
            for timing in timings:
                if timing is not None:
                    self.results["symbol_lookups"].append(timing)
            
            await asyncio.sleep(1)  # Brief pause between batches
    
    async def test_search_performance(self):
        """Test search performance."""
        print("Testing search performance...")
        
        # Test queries
        queries = [
            ("test", False),
            ("function", False),
            ("class", False),
            ("import", False),
            ("how to install", True),
            ("error handling", True),
            ("configuration guide", True),
            ("API documentation", True)
        ]
        
        async def perform_search(query: str, semantic: bool) -> float:
            start = time.time()
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/search",
                        params={"q": query, "semantic": semantic},
                        headers=self.headers,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        return (time.time() - start) * 1000  # ms
                    else:
                        self.results["errors"].append({
                            "type": "search",
                            "status": response.status_code,
                            "query": query
                        })
                        return None
            except Exception as e:
                self.results["errors"].append({
                    "type": "search",
                    "error": str(e),
                    "query": query
                })
                return None
        
        # Run continuous searches
        end_time = time.time() + TEST_DURATION
        while time.time() < end_time:
            tasks = [perform_search(query, semantic) for query, semantic in queries]
            timings = await asyncio.gather(*tasks)
            
            for timing in timings:
                if timing is not None:
                    self.results["searches"].append(timing)
            
            await asyncio.sleep(2)  # Brief pause between batches
    
    async def test_system_metrics(self):
        """Monitor system metrics."""
        print("Monitoring system metrics...")
        
        async with httpx.AsyncClient() as client:
            end_time = time.time() + TEST_DURATION
            
            while time.time() < end_time:
                try:
                    # Get Prometheus metrics
                    response = await client.get(f"{self.base_url}/metrics")
                    if response.status_code == 200:
                        metrics = self.parse_prometheus_metrics(response.text)
                        
                        # Extract key metrics
                        timestamp = time.time()
                        self.results["metrics"][timestamp] = {
                            "memory_rss": metrics.get("mcp_memory_usage_bytes", {}).get("rss", 0),
                            "cpu_usage": metrics.get("mcp_cpu_usage_percent", 0),
                            "active_threads": metrics.get("mcp_active_threads", 0),
                            "cache_hit_rate": self.calculate_cache_hit_rate(metrics),
                            "error_rate": self.calculate_error_rate(metrics)
                        }
                
                except Exception as e:
                    print(f"Failed to collect metrics: {e}")
                
                await asyncio.sleep(10)  # Collect every 10 seconds
    
    async def monitor_errors(self):
        """Monitor error rates."""
        # This runs concurrently with other tests to track overall error rate
        pass  # Errors are collected in other methods
    
    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics text format."""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(' ')
                if len(parts) == 2:
                    metric_name = parts[0]
                    metric_value = float(parts[1])
                    
                    # Handle labeled metrics
                    if '{' in metric_name:
                        base_name = metric_name.split('{')[0]
                        labels = metric_name.split('{')[1].rstrip('}')
                        
                        if base_name not in metrics:
                            metrics[base_name] = {}
                        
                        # Simple label parsing
                        label_dict = {}
                        for label in labels.split(','):
                            if '=' in label:
                                k, v = label.split('=', 1)
                                label_dict[k] = v.strip('"')
                        
                        # Store based on first label for simplicity
                        if label_dict:
                            first_label_value = list(label_dict.values())[0]
                            metrics[base_name][first_label_value] = metric_value
                    else:
                        metrics[metric_name] = metric_value
        
        return metrics
    
    def calculate_cache_hit_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate cache hit rate from metrics."""
        hits = metrics.get("mcp_cache_hits_total", 0)
        misses = metrics.get("mcp_cache_misses_total", 0)
        total = hits + misses
        
        return (hits / total * 100) if total > 0 else 0
    
    def calculate_error_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate error rate from collected errors."""
        total_requests = len(self.results["symbol_lookups"]) + len(self.results["searches"])
        total_errors = len(self.results["errors"])
        
        return (total_errors / total_requests) if total_requests > 0 else 0
    
    def analyze_results(self, duration: float) -> Dict[str, Any]:
        """Analyze collected results and compare against requirements."""
        print("\n" + "=" * 60)
        print("PERFORMANCE VALIDATION RESULTS")
        print("=" * 60)
        
        validation_results = {
            "success": True,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Symbol lookup performance
        if self.results["symbol_lookups"]:
            p95_symbol = self.calculate_percentile(self.results["symbol_lookups"], 95)
            passed = p95_symbol <= REQUIREMENTS["symbol_lookup_p95"]
            validation_results["tests"]["symbol_lookup"] = {
                "p95": p95_symbol,
                "requirement": REQUIREMENTS["symbol_lookup_p95"],
                "passed": passed,
                "samples": len(self.results["symbol_lookups"])
            }
            
            print(f"\nSymbol Lookup Performance:")
            print(f"  P95 Latency: {p95_symbol:.2f}ms (requirement: <{REQUIREMENTS['symbol_lookup_p95']}ms)")
            print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
            
            if not passed:
                validation_results["success"] = False
        
        # Search performance
        if self.results["searches"]:
            p95_search = self.calculate_percentile(self.results["searches"], 95)
            passed = p95_search <= REQUIREMENTS["semantic_search_p95"]
            validation_results["tests"]["search"] = {
                "p95": p95_search,
                "requirement": REQUIREMENTS["semantic_search_p95"],
                "passed": passed,
                "samples": len(self.results["searches"])
            }
            
            print(f"\nSearch Performance:")
            print(f"  P95 Latency: {p95_search:.2f}ms (requirement: <{REQUIREMENTS['semantic_search_p95']}ms)")
            print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
            
            if not passed:
                validation_results["success"] = False
        
        # Memory usage
        if self.results["metrics"]:
            memory_values = [m["memory_rss"] / 1024 / 1024 for m in self.results["metrics"].values()]
            max_memory = max(memory_values) if memory_values else 0
            passed = max_memory <= REQUIREMENTS["memory_usage_max"]
            validation_results["tests"]["memory"] = {
                "max_mb": max_memory,
                "requirement": REQUIREMENTS["memory_usage_max"],
                "passed": passed
            }
            
            print(f"\nMemory Usage:")
            print(f"  Maximum: {max_memory:.2f}MB (requirement: <{REQUIREMENTS['memory_usage_max']}MB)")
            print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
            
            if not passed:
                validation_results["success"] = False
        
        # Error rate
        error_rate = self.calculate_error_rate(self.results["metrics"])
        passed = error_rate <= REQUIREMENTS["error_rate_max"]
        validation_results["tests"]["error_rate"] = {
            "rate": error_rate,
            "requirement": REQUIREMENTS["error_rate_max"],
            "passed": passed,
            "total_errors": len(self.results["errors"])
        }
        
        print(f"\nError Rate:")
        print(f"  Rate: {error_rate:.2%} (requirement: <{REQUIREMENTS['error_rate_max']:.1%})")
        print(f"  Total Errors: {len(self.results['errors'])}")
        print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
        
        if not passed:
            validation_results["success"] = False
        
        # Overall summary
        print("\n" + "=" * 60)
        print(f"OVERALL RESULT: {'✅ ALL TESTS PASSED' if validation_results['success'] else '❌ SOME TESTS FAILED'}")
        print("=" * 60)
        
        # Save detailed results
        with open("validation_results.json", "w") as f:
            json.dump(validation_results, f, indent=2)
        
        print(f"\nDetailed results saved to: validation_results.json")
        
        return validation_results
    
    def calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]


async def main():
    """Main entry point."""
    validator = PerformanceValidator(DEPLOYMENT_URL, API_TOKEN)
    
    try:
        results = await validator.validate_all()
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except Exception as e:
        print(f"\nValidation failed with error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())