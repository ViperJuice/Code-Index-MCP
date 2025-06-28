from pathlib import Path

from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper

if __name__ == "__main__":
    wrapper = TreeSitterWrapper()
    print(wrapper.parse_file(Path(__file__)))
