from mcp_server.plugins.repository_plugin_loader import RepositoryPluginLoader


def test_loader_mark_loaded_and_get_active_plugins(monkeypatch):
    loader = RepositoryPluginLoader()

    class FakeMemoryManager:
        def get_plugin(self, language):
            return {"lang": language}

        def get_memory_status(self):
            return {"loaded_plugins": 1}

    loader.memory_manager = FakeMemoryManager()
    loader.mark_loaded("python")

    active = loader.get_active_plugins()
    assert active["python"] == {"lang": "python"}


def test_loader_statistics_alias(monkeypatch):
    loader = RepositoryPluginLoader()

    class FakeMemoryManager:
        def get_memory_status(self):
            return {"loaded_plugins": 0}

    loader.memory_manager = FakeMemoryManager()
    stats = loader.get_statistics()
    assert stats["loaded_plugins"] == 0
