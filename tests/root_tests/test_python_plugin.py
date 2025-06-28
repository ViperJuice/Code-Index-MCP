from pathlib import Path
from pprint import pprint

from mcp_server.plugins.python_plugin.plugin import Plugin

if __name__ == "__main__":
    plugin = Plugin()
    target = Path("mcp_server/plugins/python_plugin/plugin.py")
    res = plugin.indexFile(target, target.read_text())
    pprint(res)
