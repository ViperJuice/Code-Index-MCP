"""
Thread-safe bounded SQLite connection pool.

The factory callable must return connections opened with
``check_same_thread=False``; failure to do so will raise
``sqlite3.ProgrammingError`` when connections are used across threads.
"""

import queue
import sqlite3
from contextlib import contextmanager
from typing import Callable, Iterator


class ConnectionPool:
    """Bounded pool of ``sqlite3.Connection`` objects.

    Connections are pre-created at construction time using *factory*.
    ``acquire()`` blocks until a connection is available, then returns it
    to the pool on exit.  After ``close_all()`` any call to ``acquire()``
    raises ``RuntimeError`` immediately rather than blocking forever.

    The factory must return connections with ``check_same_thread=False``.
    """

    def __init__(self, factory: Callable[[], sqlite3.Connection], size: int = 4):
        self._factory = factory
        self._size = size
        self._pool: "queue.Queue[sqlite3.Connection]" = queue.Queue(maxsize=size)
        self._closed = False
        for _ in range(size):
            self._pool.put(factory())

    @contextmanager
    def acquire(self) -> Iterator[sqlite3.Connection]:
        if self._closed:
            raise RuntimeError("ConnectionPool is closed; cannot acquire connection")
        conn = self._pool.get()
        try:
            yield conn
        finally:
            if not self._closed:
                self._pool.put(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass

    def close_all(self) -> None:
        """Drain the pool and close every connection.  Idempotent."""
        self._closed = True
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
            except queue.Empty:
                break
