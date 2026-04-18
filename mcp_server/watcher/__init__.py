# Re-export FileWatcher so existing imports (from mcp_server.watcher import FileWatcher) keep working.
# The watcher.py module is shadowed by this package directory; the class lives in _file_watcher.py.
# NOTE: We import from the original watcher.py via a workaround — watcher.py must be moved to
# _file_watcher.py by SL-1, but until then we do a sys.path-level import by filename.
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_watcher_py = _pl.Path(__file__).parent.parent / "watcher.py"
if _watcher_py.exists():
    _spec = _ilu.spec_from_file_location("mcp_server._watcher_module", _watcher_py)
    _mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
    FileWatcher = _mod.FileWatcher
    _sys.modules.setdefault("mcp_server._watcher_module", _mod)
