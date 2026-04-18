# Re-export all public symbols from watcher.py so existing imports keep working.
# mcp_server/watcher.py is shadowed by this package directory; we load it by filename.
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_watcher_py = _pl.Path(__file__).parent.parent / "watcher.py"
if _watcher_py.exists():
    _spec = _ilu.spec_from_file_location("mcp_server._watcher_module", _watcher_py)
    _mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
    FileWatcher = _mod.FileWatcher
    _Handler = _mod._Handler
    _is_excluded = _mod._is_excluded
    _sys.modules.setdefault("mcp_server._watcher_module", _mod)
