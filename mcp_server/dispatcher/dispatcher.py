from pathlib import Path
from typing import Iterable, Dict, List, Optional, Tuple, Any
import logging
import hashlib
import time
from datetime import datetime
from ..plugin_base import IPlugin, SymbolDef, SearchResult, Reference
from .plugin_router import PluginRouter, FileTypeMatcher, PluginCapability
from .result_aggregator import ResultAggregator, AggregatedResult, AggregationStats
from ..plugin_system.models import PluginInstance, PluginConfig, PluginState

logger = logging.getLogger(__name__)

class Dispatcher:
    """Enhanced dispatcher with advanced routing and result aggregation capabilities."""
    
    def __init__(self, plugins: list[IPlugin], storage=None, enable_advanced_features: bool = True, plugin_manager=None):
        """Initialize the dispatcher.
        
        Args:
            plugins: List of plugins to manage
            storage: Storage backend for persisting index data
            enable_advanced_features: Whether to enable advanced routing and aggregation
            plugin_manager: Plugin manager for lazy loading (optional)
        """
        self._plugins = plugins
        self._by_lang = {p.lang: p for p in plugins}
        self._storage = storage
        self._plugin_manager = plugin_manager  # For lazy loading
        self._lazy_plugins_cache = {}  # Cache for lazy-loaded plugins
        
        # Cache for file hashes to avoid re-indexing unchanged files
        self._file_cache = {}  # path -> (mtime, size, content_hash)
        
        # Advanced components
        self._enable_advanced = enable_advanced_features
        if self._enable_advanced:
            self._file_matcher = FileTypeMatcher()
            self._router = PluginRouter(self._file_matcher)
            self._aggregator = ResultAggregator()
            
            # Register plugins with router
            self._register_plugins_with_router()
        
        # Performance tracking
        self._operation_stats = {
            'searches': 0,
            'lookups': 0,
            'indexings': 0,
            'total_time': 0.0
        }
    
    def _register_plugins_with_router(self):
        """Register plugins with the router and assign capabilities."""
        for plugin in self._plugins:
            # Determine capabilities based on plugin type/language
            capabilities = self._detect_plugin_capabilities(plugin)
            self._router.register_plugin(plugin, capabilities)
    
    def _detect_plugin_capabilities(self, plugin: IPlugin) -> List[PluginCapability]:
        """Detect capabilities for a plugin based on its language and features."""
        capabilities = []
        lang = getattr(plugin, 'lang', 'unknown')
        
        # Base capabilities all plugins have
        capabilities.append(PluginCapability(
            'syntax_analysis', '1.0', f'{lang} syntax analysis', 
            priority=70, metadata={'language': lang}
        ))
        
        capabilities.append(PluginCapability(
            'code_search', '1.0', f'{lang} code search', 
            priority=80, metadata={'language': lang}
        ))
        
        # Language-specific capabilities
        if lang == 'python':
            capabilities.extend([
                PluginCapability('semantic_search', '1.0', 'Python semantic search', 90),
                PluginCapability('refactoring', '1.0', 'Python refactoring support', 75),
                PluginCapability('type_analysis', '1.0', 'Python type analysis', 85)
            ])
        elif lang in ['javascript', 'typescript']:
            capabilities.extend([
                PluginCapability('linting', '1.0', 'JavaScript/TypeScript linting', 85),
                PluginCapability('bundling_analysis', '1.0', 'Module bundling analysis', 70),
                PluginCapability('framework_support', '1.0', 'Framework-specific support', 75)
            ])
        elif lang in ['c', 'cpp']:
            capabilities.extend([
                PluginCapability('compilation_analysis', '1.0', 'Compilation analysis', 80),
                PluginCapability('memory_analysis', '1.0', 'Memory usage analysis', 70),
                PluginCapability('performance_profiling', '1.0', 'Performance profiling', 75)
            ])
        
        return capabilities
    
    @property
    def plugins(self):
        """Get the dictionary of plugins by language."""
        return self._by_lang
    
    @property
    def router(self) -> Optional[PluginRouter]:
        """Get the plugin router (if advanced features enabled)."""
        return self._router if self._enable_advanced else None
    
    @property
    def aggregator(self) -> Optional[ResultAggregator]:
        """Get the result aggregator (if advanced features enabled)."""
        return self._aggregator if self._enable_advanced else None

    def _get_or_load_plugin_for_file(self, path: Path) -> Optional[IPlugin]:
        """Get or lazy-load a plugin for the given file path."""
        # First try existing plugins
        for p in self._plugins:
            if p.supports(path):
                return p
        
        # If no plugin found and we have a plugin manager, try lazy loading
        if self._plugin_manager:
            # Determine file language/type
            file_extension = path.suffix.lower()
            
            # Map extensions to plugin names (simplified mapping)
            extension_to_plugin = {
                '.py': 'Python',
                '.js': 'Js', 
                '.ts': 'Js',
                '.java': 'Jvm',
                '.kt': 'Jvm',
                '.go': 'Go',
                '.rs': 'Rust',
                '.c': 'C',
                '.cpp': 'Cpp',
                '.h': 'C',
                '.cs': 'Csharp',
                '.rb': 'Ruby',
                '.php': 'Php',
                '.dart': 'Dart',
                '.yaml': 'Yaml',
                '.yml': 'Yaml',
                '.json': 'Json',
                '.md': 'Markdown',
                '.hs': 'Haskell',
                '.scala': 'Scala',
                '.lua': 'Lua',
                '.toml': 'Toml',
                '.csv': 'Csv',
                '.html': 'Html Css',
                '.css': 'Html Css',
                '.sh': 'Bash',
                '.bash': 'Bash',
                '.asm': 'Asm',
                '.s': 'Asm'
            }
            
            plugin_name = extension_to_plugin.get(file_extension)
            if plugin_name and plugin_name not in self._lazy_plugins_cache:
                try:
                    logger.info(f"Lazy loading plugin {plugin_name} for file {path}")
                    
                    # First check if plugin exists in instances (from discovery)
                    if plugin_name not in self._plugin_manager._instances:
                        # Discover plugins first if not already done
                        discovered = self._plugin_manager._discovery.discover_plugins(
                            self._plugin_manager.config.plugin_dirs
                        )
                        
                        # Find and register the specific plugin we need
                        for plugin_info in discovered:
                            if plugin_info.name == plugin_name:
                                plugin_class = self._plugin_manager._loader.load_plugin(plugin_info)
                                self._plugin_manager._registry.register_plugin(plugin_info, plugin_class)
                                
                                instance = PluginInstance(
                                    info=plugin_info,
                                    config=PluginConfig(),
                                    instance=None,
                                    state=PluginState.DISCOVERED,
                                    load_time=0
                                )
                                self._plugin_manager._instances[plugin_name] = instance
                                break
                    
                    # Now initialize the specific plugin
                    plugin_instance = self._plugin_manager.initialize_plugin(plugin_name, {})
                    self._lazy_plugins_cache[plugin_name] = plugin_instance
                    self._plugins.append(plugin_instance)
                    self._by_lang[plugin_instance.lang] = plugin_instance
                    return plugin_instance
                except Exception as e:
                    logger.warning(f"Failed to lazy load plugin {plugin_name}: {e}")
        
        return None

    def _match_plugin(self, path: Path) -> IPlugin:
        """Match a plugin for the given file path."""
        if self._enable_advanced and self._router:
            # Use advanced routing
            route_result = self._router.get_best_plugin(path)
            if route_result:
                return route_result.plugin
            raise RuntimeError(f"No plugin found for {path}")
        else:
            # Try to get or lazy-load a plugin
            plugin = self._get_or_load_plugin_for_file(path)
            if plugin:
                return plugin
            raise RuntimeError(f"No plugin for {path}")
    
    def get_plugins_for_file(self, path: Path) -> List[Tuple[IPlugin, float]]:
        """Get all plugins that can handle a file with confidence scores.
        
        Args:
            path: File path to analyze
            
        Returns:
            List of (plugin, confidence) tuples sorted by confidence
        """
        if self._enable_advanced and self._router:
            route_results = self._router.route_file(path)
            return [(result.plugin, result.confidence) for result in route_results]
        else:
            # Basic fallback
            matching_plugins = []
            for plugin in self._plugins:
                if plugin.supports(path):
                    matching_plugins.append((plugin, 1.0))  # Basic confidence
            return matching_plugins

    def lookup(self, symbol: str) -> SymbolDef | None:
        """Look up symbol definition across all plugins."""
        start_time = time.time()
        
        try:
            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                definitions_by_plugin = {}
                for plugin in self._plugins:
                    try:
                        definition = plugin.getDefinition(symbol)
                        definitions_by_plugin[plugin] = definition
                    except Exception as e:
                        logger.warning(f"Plugin {plugin.lang} failed to get definition for {symbol}: {e}")
                        definitions_by_plugin[plugin] = None
                
                result = self._aggregator.aggregate_symbol_definitions(definitions_by_plugin)
                
                self._operation_stats['lookups'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
                return result
            else:
                # Fallback to basic lookup
                for p in self._plugins:
                    res = p.getDefinition(symbol)
                    if res:
                        self._operation_stats['lookups'] += 1
                        self._operation_stats['total_time'] += time.time() - start_time
                        return res
                return None
                
        except Exception as e:
            logger.error(f"Error in symbol lookup for {symbol}: {e}", exc_info=True)
            return None
    
    def find_references(self, symbol: str) -> List[Reference]:
        """Find all references to a symbol across plugins."""
        if self._enable_advanced and self._aggregator:
            # Use advanced aggregation
            references_by_plugin = {}
            for plugin in self._plugins:
                try:
                    references = list(plugin.findReferences(symbol))
                    references_by_plugin[plugin] = references
                except Exception as e:
                    logger.warning(f"Plugin {plugin.lang} failed to find references for {symbol}: {e}")
                    references_by_plugin[plugin] = []
            
            return self._aggregator.aggregate_references(references_by_plugin)
        else:
            # Basic fallback
            all_references = []
            for plugin in self._plugins:
                try:
                    references = list(plugin.findReferences(symbol))
                    all_references.extend(references)
                except Exception as e:
                    logger.warning(f"Plugin {plugin.lang} failed to find references for {symbol}: {e}")
            return all_references

    def search(self, query: str, semantic=False, limit=20) -> Iterable[SearchResult]:
        """Search for code across all plugins."""
        start_time = time.time()
        
        try:
            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                results_by_plugin = {}
                opts = {"semantic": semantic, "limit": limit}
                
                for plugin in self._plugins:
                    try:
                        results = list(plugin.search(query, opts))
                        if results:
                            results_by_plugin[plugin] = results
                    except Exception as e:
                        logger.warning(f"Plugin {plugin.lang} failed to search for {query}: {e}")
                
                aggregated_results, stats = self._aggregator.aggregate_search_results(
                    results_by_plugin, limit=limit
                )
                
                logger.debug(f"Search aggregation stats: {stats.total_results} total, "
                           f"{stats.unique_results} unique, {stats.plugins_used} plugins used")
                
                self._operation_stats['searches'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
                # Yield primary results from aggregated results
                for aggregated in aggregated_results:
                    yield aggregated.primary_result
            else:
                # Fallback to basic search
                opts = {"semantic": semantic, "limit": limit}
                count = 0
                for p in self._plugins:
                    if limit and count >= limit:
                        break
                    try:
                        for result in p.search(query, opts):
                            if limit and count >= limit:
                                break
                            yield result
                            count += 1
                    except Exception as e:
                        logger.warning(f"Plugin {p.lang} failed to search for {query}: {e}")
                
                self._operation_stats['searches'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
        except Exception as e:
            logger.error(f"Error in search for {query}: {e}", exc_info=True)
    
    def advanced_search(self, query: str, semantic=False, limit=20) -> Tuple[List[AggregatedResult], AggregationStats]:
        """Perform advanced search with detailed aggregation results.
        
        Args:
            query: Search query
            semantic: Whether to use semantic search
            limit: Maximum results to return
            
        Returns:
            Tuple of (aggregated results, aggregation statistics)
        """
        if not self._enable_advanced or not self._aggregator:
            raise RuntimeError("Advanced search requires advanced features to be enabled")
        
        start_time = time.time()
        
        try:
            results_by_plugin = {}
            opts = {"semantic": semantic, "limit": limit}
            
            for plugin in self._plugins:
                try:
                    results = list(plugin.search(query, opts))
                    if results:
                        results_by_plugin[plugin] = results
                except Exception as e:
                    logger.warning(f"Plugin {plugin.lang} failed to search for {query}: {e}")
            
            aggregated_results, stats = self._aggregator.aggregate_search_results(
                results_by_plugin, limit=limit
            )
            
            self._operation_stats['searches'] += 1
            self._operation_stats['total_time'] += time.time() - start_time
            
            return aggregated_results, stats
            
        except Exception as e:
            logger.error(f"Error in advanced search for {query}: {e}", exc_info=True)
            raise
    
    def _get_file_hash(self, content: str) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _should_reindex(self, path: Path, content: str) -> bool:
        """Check if file needs re-indexing based on cache."""
        path_str = str(path)
        
        # Get current file stats
        try:
            stat = path.stat()
            mtime = stat.st_mtime
            size = stat.st_size
        except (OSError, IOError):
            # If we can't stat the file, assume we need to index it
            return True
        
        # Check cache
        if path_str not in self._file_cache:
            return True
        
        cached_mtime, cached_size, cached_hash = self._file_cache[path_str]
        
        # Quick check: if mtime and size are the same, assume content is unchanged
        if mtime == cached_mtime and size == cached_size:
            logger.debug(f"Skipping {path}: mtime and size unchanged")
            return False
        
        # If mtime or size changed, check content hash
        content_hash = self._get_file_hash(content)
        if content_hash == cached_hash:
            # Update cache with new mtime/size but same hash
            self._file_cache[path_str] = (mtime, size, content_hash)
            logger.debug(f"Skipping {path}: content unchanged despite mtime/size change")
            return False
        
        return True
    
    def index_file(self, path: Path) -> None:
        """Index a single file if it has changed."""
        try:
            # Find the appropriate plugin
            plugin = self._match_plugin(path)
            
            # Read file content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                try:
                    content = path.read_text(encoding='latin-1')
                except Exception as e:
                    logger.error(f"Failed to read {path}: {e}")
                    return
            
            # Check if we need to re-index
            if not self._should_reindex(path, content):
                return
            
            # Index the file
            start_time = time.time()
            logger.info(f"Indexing {path} with {plugin.lang} plugin")
            shard = plugin.indexFile(path, content)
            
            # Save to storage if available
            if self._storage and shard:
                try:
                    # Get or create repository (assuming current directory)
                    repo_path = str(Path.cwd())
                    repo = self._storage.get_repository(repo_path)
                    if not repo:
                        repo_id = self._storage.create_repository(repo_path, Path(repo_path).name)
                    else:
                        repo_id = repo['id']
                    
                    # Store file
                    try:
                        relative_path = str(path.relative_to(Path.cwd()))
                    except ValueError:
                        # If path is not relative to cwd, use absolute path
                        relative_path = str(path)
                    file_id = self._storage.store_file(
                        repository_id=repo_id,
                        path=str(path),
                        relative_path=relative_path,
                        language=plugin.lang,
                        size=len(content),
                        hash=self._get_file_hash(content)
                    )
                    
                    # Store symbols
                    symbols = shard.get('symbols', [])
                    for symbol in symbols:
                        if isinstance(symbol, dict):
                            self._storage.store_symbol(
                                file_id=file_id,
                                name=symbol.get('name', ''),
                                kind=symbol.get('kind', 'unknown'),
                                line_start=symbol.get('line_start', 0),
                                line_end=symbol.get('line_end', 0),
                                signature=symbol.get('signature'),
                                documentation=symbol.get('documentation'),
                                metadata=symbol.get('metadata', {})
                            )
                    
                    logger.debug(f"Saved {len(symbols)} symbols for {path}")
                    
                except Exception as e:
                    logger.error(f"Failed to save index data for {path}: {e}", exc_info=True)
            
            # Record performance if advanced features enabled
            if self._enable_advanced and self._router:
                execution_time = time.time() - start_time
                self._router.record_performance(plugin, execution_time)
            
            # Update cache
            stat = path.stat()
            content_hash = self._get_file_hash(content)
            self._file_cache[str(path)] = (stat.st_mtime, stat.st_size, content_hash)
            
            self._operation_stats['indexings'] += 1
            self._operation_stats['total_time'] += time.time() - start_time
            
            logger.info(f"Successfully indexed {path}: {len(shard.get('symbols', []))} symbols found")
            
        except RuntimeError as e:
            # No plugin found for this file type
            logger.debug(f"No plugin for {path}: {e}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """Get comprehensive statistics across all plugins and components."""
        # Basic indexing stats
        stats = {"total": 0, "by_language": {}}
        
        for plugin in self._plugins:
            lang = plugin.lang
            # Count files in cache for this plugin
            count = 0
            for file_path in self._file_cache:
                try:
                    if plugin.supports(Path(file_path)):
                        count += 1
                except:
                    pass
            
            if count > 0:
                stats["total"] += count
                stats["by_language"][lang] = count
        
        # Add operation statistics
        stats["operations"] = self._operation_stats.copy()
        if self._operation_stats['searches'] > 0:
            stats["operations"]["avg_search_time"] = self._operation_stats['total_time'] / (
                self._operation_stats['searches'] + self._operation_stats['lookups'] + self._operation_stats['indexings']
            )
        
        # Add advanced component statistics if enabled
        if self._enable_advanced:
            stats["advanced"] = {
                "router_enabled": True,
                "aggregator_enabled": True
            }
            
            if self._router:
                stats["advanced"]["router_stats"] = self._router.get_plugin_stats()
            
            if self._aggregator:
                stats["advanced"]["aggregator_stats"] = self._aggregator.get_aggregation_stats()
        else:
            stats["advanced"] = {"router_enabled": False, "aggregator_enabled": False}
        
        return stats
    
    def get_plugin_by_capability(self, capability: str) -> List[Tuple[IPlugin, float]]:
        """Get plugins that provide a specific capability.
        
        Args:
            capability: Capability name to search for
            
        Returns:
            List of (plugin, confidence) tuples for plugins with the capability
        """
        if not self._enable_advanced or not self._router:
            # Fallback: return all plugins with default confidence
            return [(plugin, 0.5) for plugin in self._plugins]
        
        route_results = self._router.route_by_capability(capability)
        return [(result.plugin, result.confidence) for result in route_results]
    
    def get_plugin_by_language(self, language: str) -> List[Tuple[IPlugin, float]]:
        """Get plugins that support a specific language.
        
        Args:
            language: Programming language name
            
        Returns:
            List of (plugin, confidence) tuples for plugins supporting the language
        """
        if not self._enable_advanced or not self._router:
            # Fallback: check basic language support
            matching_plugins = []
            for plugin in self._plugins:
                if hasattr(plugin, 'lang') and plugin.lang == language:
                    matching_plugins.append((plugin, 1.0))
            return matching_plugins
        
        route_results = self._router.route_by_language(language)
        return [(result.plugin, result.confidence) for result in route_results]
    
    def configure_advanced_features(self, enable_router: bool = True, 
                                  enable_aggregator: bool = True,
                                  router_config: Optional[Dict] = None,
                                  aggregator_config: Optional[Dict] = None) -> None:
        """Configure advanced dispatcher features.
        
        Args:
            enable_router: Whether to enable advanced routing
            enable_aggregator: Whether to enable result aggregation
            router_config: Configuration for the router
            aggregator_config: Configuration for the aggregator
        """
        if not self._enable_advanced:
            logger.warning("Advanced features are disabled. Configuration ignored.")
            return
        
        # Configure router
        if self._router and router_config:
            load_balance = router_config.get('load_balance_enabled', True)
            performance_tracking = router_config.get('performance_tracking_enabled', True)
            max_samples = router_config.get('max_performance_samples', 100)
            
            self._router.configure(
                load_balance_enabled=load_balance,
                performance_tracking_enabled=performance_tracking,
                max_performance_samples=max_samples
            )
        
        # Configure aggregator
        if self._aggregator and aggregator_config:
            from .result_aggregator import (
                SimpleAggregationStrategy, SmartAggregationStrategy, RankingCriteria
            )
            
            strategy_name = aggregator_config.get('strategy', 'smart')
            if strategy_name == 'simple':
                strategy = SimpleAggregationStrategy()
            else:
                similarity_threshold = aggregator_config.get('similarity_threshold', 0.8)
                strategy = SmartAggregationStrategy(similarity_threshold)
            
            criteria_config = aggregator_config.get('ranking_criteria', {})
            criteria = RankingCriteria(**criteria_config)
            
            cache_enabled = aggregator_config.get('cache_enabled', True)
            cache_timeout = aggregator_config.get('cache_timeout', 300.0)
            
            self._aggregator.configure(
                strategy=strategy,
                ranking_criteria=criteria,
                cache_enabled=cache_enabled,
                cache_timeout=cache_timeout
            )
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self._file_cache.clear()
        
        if self._enable_advanced:
            if self._router and hasattr(self._router._file_matcher, 'clear_cache'):
                self._router._file_matcher.clear_cache()
            
            if self._aggregator:
                self._aggregator.clear_cache()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        metrics = {
            'operation_stats': self._operation_stats.copy(),
            'cache_stats': {
                'file_cache_size': len(self._file_cache),
                'file_cache_hit_rate': 0.0  # Would need tracking to calculate
            }
        }
        
        if self._enable_advanced:
            if self._router:
                router_stats = self._router.get_plugin_stats()
                metrics['router_stats'] = router_stats
                
                # Plugin performance metrics
                metrics['plugin_performance'] = {}
                for plugin in self._plugins:
                    avg_perf = self._router._get_avg_performance(plugin)
                    usage_count = self._router._plugin_usage_count.get(plugin, 0)
                    metrics['plugin_performance'][plugin.lang] = {
                        'avg_execution_time': avg_perf,
                        'usage_count': usage_count
                    }
            
            if self._aggregator:
                aggregator_stats = self._aggregator.get_aggregation_stats()
                metrics['aggregator_stats'] = aggregator_stats
        
        return metrics
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on all components."""
        health = {
            'status': 'healthy',
            'components': {},
            'plugins': {},
            'errors': []
        }
        
        # Check basic dispatcher health
        health['components']['dispatcher'] = {
            'status': 'healthy',
            'plugins_loaded': len(self._plugins),
            'files_cached': len(self._file_cache)
        }
        
        # Check plugin health
        for plugin in self._plugins:
            plugin_health = {'status': 'unknown'}
            try:
                # Test basic plugin functionality
                test_path = Path('/test/dummy.py')  # Dummy path for testing
                supports = plugin.supports(test_path)
                plugin_health = {
                    'status': 'healthy',
                    'supports_test': supports,
                    'language': getattr(plugin, 'lang', 'unknown')
                }
            except Exception as e:
                plugin_health = {
                    'status': 'error',
                    'error': str(e)
                }
                health['errors'].append(f"Plugin {plugin.lang}: {str(e)}")
            
            health['plugins'][getattr(plugin, 'lang', 'unknown')] = plugin_health
        
        # Check advanced components
        if self._enable_advanced:
            health['components']['router'] = {
                'status': 'healthy' if self._router else 'disabled',
                'enabled': self._router is not None
            }
            
            health['components']['aggregator'] = {
                'status': 'healthy' if self._aggregator else 'disabled',
                'enabled': self._aggregator is not None
            }
        else:
            health['components']['advanced_features'] = {
                'status': 'disabled',
                'enabled': False
            }
        
        # Determine overall health
        error_count = len(health['errors'])
        if error_count > 0:
            if error_count >= len(self._plugins) / 2:  # More than half plugins have errors
                health['status'] = 'unhealthy'
            else:
                health['status'] = 'degraded'
        
        return health
