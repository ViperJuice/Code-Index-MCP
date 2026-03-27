from pathlib import Path

from mcp_server.document_processing import BaseDocumentPlugin
from mcp_server.document_processing.document_interfaces import ProcessedDocument
from mcp_server.interfaces.plugin_interfaces import PluginRuntimeInfo
from mcp_server.interfaces.shared_interfaces import PluginStatus
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.interfaces import (
    IPluginManager as PluginSystemManagerContract,
)
from mcp_server.document_processing.base_document_plugin import (
    DocumentMetadata as BaseDocumentMetadata,
)
from mcp_server.document_processing.base_document_plugin import (
    DocumentStructure as BaseDocumentStructure,
)


class _ContractDocumentPlugin(BaseDocumentPlugin):
    def __init__(self):
        super().__init__({"name": "contract_doc", "code": "text", "extensions": [".txt"]})

    def _get_supported_extensions(self):
        return [".txt"]

    def extract_structure(self, content: str, file_path: Path):
        return BaseDocumentStructure(
            sections=[
                {
                    "title": "Intro",
                    "level": 1,
                    "start_pos": 0,
                    "end_pos": len(content),
                    "start_line": 1,
                    "end_line": max(1, len(content.splitlines())),
                }
            ],
            headings=[],
            metadata={"source": str(file_path)},
            outline=[],
        )

    def extract_metadata(self, content: str, file_path: Path):
        return BaseDocumentMetadata(title=file_path.stem, document_type="text")

    def parse_content(self, content: str, file_path: Path):
        return content


def test_plugin_manager_status_uses_runtime_info_shape():
    manager = PluginManager()
    status = manager.get_plugin_status()

    assert isinstance(status, dict)
    runtime = PluginRuntimeInfo(
        name="example",
        status=PluginStatus.READY,
        enabled=True,
        version="1.0.0",
        language="python",
    )
    assert runtime.status is PluginStatus.READY

    required_methods = {
        "load_plugins_safe",
        "shutdown_safe",
        "get_plugin_status",
        "get_detailed_plugin_status",
    }
    assert required_methods.issubset(set(dir(PluginSystemManagerContract)))


def test_base_document_plugin_process_document_matches_contract():
    plugin = _ContractDocumentPlugin()

    processed = plugin.process_document("First sentence. Second sentence.", "notes.txt")

    assert isinstance(processed, ProcessedDocument)
    assert processed.path.endswith("notes.txt")
    assert processed.language == "text"
    assert processed.validate_chunk_order()
    assert processed.chunks
    assert processed.chunks[0].metadata.document_path.endswith("notes.txt")
