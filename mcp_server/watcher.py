from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .dispatcher import Dispatcher

class _Handler(FileSystemEventHandler):
    def __init__(self, dispatcher: Dispatcher):
        self.dispatcher = dispatcher

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # TODO: dispatcher._match_plugin(path).indexFile(path.read_text())

class FileWatcher:
    def __init__(self, root: Path, dispatcher: Dispatcher):
        self._observer = Observer()
        self._observer.schedule(_Handler(dispatcher), str(root), recursive=True)

    def start(self): self._observer.start()
    def stop(self): self._observer.stop()
