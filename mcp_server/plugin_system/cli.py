#!/usr/bin/env python3
"""
Plugin management CLI tool.
Provides commands for discovering, loading, and managing plugins.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import click
import yaml
from tabulate import tabulate

from .config import get_config_manager
from .discovery import get_plugin_discovery
from .loader import get_plugin_loader
from .models import PluginConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """MCP Server Plugin Management CLI"""


@cli.command()
def discover():
    """Discover available plugins"""
    discovery = get_plugin_discovery()
    plugins = discovery.discover_plugins()

    if not plugins:
        click.echo("No plugins discovered.")
        return

    # Format data for table
    table_data = []
    for language, info in plugins.items():
        table_data.append(
            [
                language,
                info["name"],
                info["version"],
                (
                    info.get("description", "")[:50] + "..."
                    if len(info.get("description", "")) > 50
                    else info.get("description", "")
                ),
            ]
        )

    headers = ["Language", "Plugin", "Version", "Description"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    click.echo(f"\nTotal plugins discovered: {len(plugins)}")


@cli.command()
@click.argument("language")
def info(language: str):
    """Show detailed information about a plugin"""
    discovery = get_plugin_discovery()
    plugin_info = discovery.get_plugin_info(language)

    if not plugin_info:
        click.echo(f"Plugin not found for language: {language}")
        return

    click.echo(f"\nPlugin Information: {language}")
    click.echo("=" * 50)
    click.echo(f"Name: {plugin_info['name']}")
    click.echo(f"Version: {plugin_info['version']}")
    click.echo(f"Description: {plugin_info.get('description', 'N/A')}")
    click.echo(f"Path: {plugin_info['path']}")
    click.echo(f"Entry Point: {plugin_info['entry_point']}")

    if "manifest" in plugin_info:
        manifest = plugin_info["manifest"]
        if "features" in manifest:
            click.echo("\nFeatures:")
            for feature in manifest["features"]:
                click.echo(f"  - {feature}")

        if "dependencies" in manifest:
            click.echo("\nDependencies:")
            for dep in manifest["dependencies"]:
                click.echo(f"  - {dep}")


@cli.command()
@click.argument("language")
@click.option("--config", help="Configuration file")
def load(language: str, config: Optional[str]):
    """Load a plugin"""
    loader = get_plugin_loader()
    config_manager = get_config_manager()

    # Load configuration if provided
    plugin_config = None
    if config:
        with open(config, "r") as f:
            config_data = yaml.safe_load(f)
        plugin_config = PluginConfig.from_dict(config_data)
    else:
        plugin_config = config_manager.load_plugin_config(language)

    # Load the plugin
    click.echo(f"Loading plugin for {language}...")
    plugin = loader.load_plugin(language, plugin_config)

    if plugin:
        click.echo(f"✅ Successfully loaded plugin for {language}")
        click.echo(f"State: {loader.get_plugin_state(language).value}")
    else:
        click.echo(f"❌ Failed to load plugin for {language}")


@cli.command()
@click.argument("language")
def unload(language: str):
    """Unload a plugin"""
    loader = get_plugin_loader()

    click.echo(f"Unloading plugin for {language}...")
    loader.unload_plugin(language)

    state = loader.get_plugin_state(language)
    if state.value == "unloaded":
        click.echo(f"✅ Successfully unloaded plugin for {language}")
    else:
        click.echo(f"❌ Failed to unload plugin for {language} (state: {state.value})")


@cli.command()
def list():
    """List loaded plugins"""
    loader = get_plugin_loader()
    active_plugins = loader.get_active_plugins()

    if not active_plugins:
        click.echo("No plugins currently loaded.")
        return

    table_data = []
    for language, plugin in active_plugins.items():
        state = loader.get_plugin_state(language)
        table_data.append(
            [
                language,
                plugin.__class__.__name__,
                state.value,
                ("Yes" if hasattr(plugin, "enable_semantic") and plugin.enable_semantic else "No"),
            ]
        )

    headers = ["Language", "Plugin Class", "State", "Semantic"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    click.echo(f"\nTotal loaded plugins: {len(active_plugins)}")


@cli.command()
def stats():
    """Show plugin system statistics"""
    loader = get_plugin_loader()
    stats = loader.get_statistics()

    click.echo("\nPlugin System Statistics")
    click.echo("=" * 40)
    click.echo(f"Total Discovered: {stats['total_discovered']}")
    click.echo(f"Total Loaded: {stats['total_loaded']}")
    click.echo(f"Active Plugins: {stats['active_plugins']}")

    click.echo("\nState Distribution:")
    for state, count in stats["state_distribution"].items():
        if count > 0:
            click.echo(f"  {state}: {count}")

    if stats["languages"]:
        click.echo(f"\nLoaded Languages: {', '.join(stats['languages'])}")


@cli.command()
@click.argument("language")
def enable(language: str):
    """Enable a plugin"""
    config_manager = get_config_manager()
    config_manager.enable_plugin(language)
    click.echo(f"✅ Plugin '{language}' enabled")


@cli.command()
@click.argument("language")
def disable(language: str):
    """Disable a plugin"""
    config_manager = get_config_manager()
    config_manager.disable_plugin(language)
    click.echo(f"✅ Plugin '{language}' disabled")


@cli.command()
@click.argument("language")
@click.argument("key")
@click.argument("value")
def set_config(language: str, key: str, value: str):
    """Set a plugin configuration value"""
    config_manager = get_config_manager()

    # Try to parse value as JSON first
    try:
        parsed_value = json.loads(value)
    except Exception:
        # If not JSON, treat as string
        parsed_value = value

    config_manager.update_plugin_settings(language, {key: parsed_value})
    click.echo(f"✅ Set {key}={parsed_value} for plugin '{language}'")


@cli.command()
@click.argument("language")
def get_config(language: str):
    """Get plugin configuration"""
    config_manager = get_config_manager()
    config = config_manager.load_plugin_config(language)

    click.echo(f"\nConfiguration for '{language}':")
    click.echo("=" * 40)
    click.echo(f"Enabled: {config.enabled}")
    click.echo(f"Priority: {config.priority}")

    if config.settings:
        click.echo("\nSettings:")
        for key, value in config.settings.items():
            click.echo(f"  {key}: {value}")


@cli.command()
@click.option("--format", type=click.Choice(["yaml", "json"]), default="yaml")
@click.argument("output_file")
def export(format: str, output_file: str):
    """Export plugin configuration"""
    config_manager = get_config_manager()

    if not output_file.endswith(f".{format}"):
        output_file = f"{output_file}.{format}"

    config_manager.export_config(output_file)
    click.echo(f"✅ Configuration exported to {output_file}")


@cli.command()
@click.argument("input_file")
def import_config(input_file: str):
    """Import plugin configuration"""
    if not Path(input_file).exists():
        click.echo(f"❌ File not found: {input_file}")
        return

    config_manager = get_config_manager()
    config_manager.import_config(input_file)
    click.echo(f"✅ Configuration imported from {input_file}")


@cli.command()
def reload():
    """Reload all plugins"""
    loader = get_plugin_loader()
    config_manager = get_config_manager()

    # Get current plugins
    current_plugins = list(loader.get_active_plugins().keys())

    click.echo("Reloading plugins...")
    for language in current_plugins:
        config = config_manager.load_plugin_config(language)
        loader.reload_plugin(language, config)

    click.echo(f"✅ Reloaded {len(current_plugins)} plugins")


@cli.command()
@click.argument("language")
def test(language: str):
    """Test a plugin with sample code"""
    loader = get_plugin_loader()

    # Load plugin if not already loaded
    plugin = loader.get_plugin(language)
    if not plugin:
        click.echo(f"❌ Failed to load plugin for {language}")
        return

    # Sample code for testing
    samples = {
        "python": 'def hello():\n    print("Hello, World!")',
        "javascript": 'function hello() {\n    console.log("Hello, World!");\n}',
        "java": 'public class Hello {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
        "markdown": "# Hello World\n\nThis is a test document.\n\n## Section 1\nContent here.",
        "plaintext": "This is a test document. It contains some text for testing the plaintext plugin.",
    }

    sample_code = samples.get(language, f"// Test code for {language}")
    click.echo(f"\nTesting plugin for {language}...")
    click.echo(f"Sample code:\n{sample_code}\n")

    try:
        result = plugin.extract_symbols(sample_code, f"test.{language}")
        click.echo("✅ Plugin test successful!")
        click.echo(f"Extracted {len(result.symbols)} symbols")

        if result.symbols:
            click.echo("\nSymbols found:")
            for symbol in result.symbols[:5]:  # Show first 5
                click.echo(f"  - {symbol.name} ({symbol.symbol_type}) at line {symbol.line}")

            if len(result.symbols) > 5:
                click.echo(f"  ... and {len(result.symbols) - 5} more")

    except Exception as e:
        click.echo(f"❌ Plugin test failed: {e}")


if __name__ == "__main__":
    cli()
