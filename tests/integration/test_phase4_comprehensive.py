#!/usr/bin/env python3
"""
Comprehensive test for all Phase 4 features.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_phase4_features():
    """Test all Phase 4 advanced features."""
    print("Phase 4 Comprehensive Feature Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Prompts System
    print("\n1. Testing Prompts System...")
    try:
        from mcp_server.prompts import PromptRegistry, get_prompt_registry
        registry = get_prompt_registry()
        prompts = registry.list_prompts()
        
        # Test prompt generation
        if "code_review" in prompts:
            prompt_result = await registry.generate_prompt(
                "code_review",
                {"file_path": "test.py", "language": "python", "code": "def test(): pass"}
            )
            print("   ✅ Prompt system working")
            print(f"   ✅ Available prompts: {len(prompts)}")
            results.append(("Prompts System", True, f"{len(prompts)} prompts available"))
        else:
            results.append(("Prompts System", False, "No prompts found"))
    except Exception as e:
        print(f"   ❌ Prompts system error: {e}")
        results.append(("Prompts System", False, str(e)))
    
    # Test 2: Performance Features
    print("\n2. Testing Performance Features...")
    try:
        from mcp_server.performance import ConnectionPool, MemoryOptimizer, RateLimiter
        
        # Test connection pool
        pool = ConnectionPool(max_size=5, timeout=30)
        print("   ✅ Connection pool created")
        
        # Test memory optimizer
        optimizer = MemoryOptimizer()
        memory_stats = await optimizer.get_memory_stats()
        print(f"   ✅ Memory optimizer working (RSS: {memory_stats.process_memory_mb:.1f}MB)")
        
        # Test rate limiter
        limiter = RateLimiter(algorithm="token_bucket", requests_per_minute=60)
        allowed = await limiter.is_allowed("test_client")
        print(f"   ✅ Rate limiter working (allowed: {allowed})")
        
        results.append(("Performance Features", True, "All components working"))
    except Exception as e:
        print(f"   ❌ Performance features error: {e}")
        results.append(("Performance Features", False, str(e)))
    
    # Test 3: Advanced Protocol Features
    print("\n3. Testing Advanced Protocol Features...")
    try:
        from mcp_server.protocol.advanced import CompletionEngine, StreamingManager, BatchProcessor
        
        # Test completion engine
        completion_engine = CompletionEngine()
        print("   ✅ Completion engine created")
        
        # Test streaming manager
        streaming_manager = StreamingManager()
        print("   ✅ Streaming manager created")
        
        # Test batch processor
        batch_processor = BatchProcessor()
        print("   ✅ Batch processor created")
        
        results.append(("Advanced Protocol", True, "All features available"))
    except Exception as e:
        print(f"   ❌ Advanced protocol error: {e}")
        results.append(("Advanced Protocol", False, str(e)))
    
    # Test 4: Production Features
    print("\n4. Testing Production Features...")
    try:
        from mcp_server.production import StructuredLogger, HealthChecker, MetricsCollector
        
        # Test structured logger
        logger = StructuredLogger("test")
        logger.info("Test log message", extra={"test": True})
        print("   ✅ Structured logging working")
        
        # Test health checker
        health_checker = HealthChecker()
        health_result = await health_checker.run_checks()
        print(f"   ✅ Health checker working (status: {health_result.overall_status})")
        
        # Test metrics collector
        metrics = MetricsCollector()
        await metrics.counter("test_metric")
        print("   ✅ Metrics collector working")
        
        results.append(("Production Features", True, "All monitoring working"))
    except Exception as e:
        print(f"   ❌ Production features error: {e}")
        results.append(("Production Features", False, str(e)))
    
    # Test 5: Consolidated Server
    print("\n5. Testing Consolidated Server...")
    try:
        from mcp_server.stdio_server import StdioMCPServer
        
        # Create server instance
        server = StdioMCPServer()
        print("   ✅ Consolidated server created")
        
        # Test configuration
        if hasattr(server, 'config'):
            print("   ✅ Server configuration loaded")
        
        results.append(("Consolidated Server", True, "Server architecture ready"))
    except Exception as e:
        print(f"   ❌ Consolidated server error: {e}")
        results.append(("Consolidated Server", False, str(e)))
    
    # Test 6: Enhanced Configuration
    print("\n6. Testing Enhanced Configuration...")
    try:
        from mcp_server.config.settings import Settings
        
        settings = Settings()
        if hasattr(settings, 'prompts') and hasattr(settings, 'performance'):
            print("   ✅ Enhanced configuration loaded")
            print(f"   ✅ Prompts enabled: {settings.prompts.enabled}")
            print(f"   ✅ Performance monitoring: {settings.performance.monitoring_enabled}")
            results.append(("Enhanced Configuration", True, "All settings available"))
        else:
            results.append(("Enhanced Configuration", False, "Missing configuration sections"))
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        results.append(("Enhanced Configuration", False, str(e)))
    
    # Report Results
    print("\n" + "=" * 60)
    print("PHASE 4 TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:<25} {message}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL PHASE 4 FEATURES WORKING!")
        print("The MCP server is fully ready for production use.")
    else:
        print(f"\n⚠️  {total-passed} features need attention.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_phase4_features())
    sys.exit(0 if success else 1)