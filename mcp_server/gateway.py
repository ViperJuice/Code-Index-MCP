from fastapi import FastAPI, HTTPException
from .dispatcher import Dispatcher
from .plugin_base import SymbolDef, SearchResult

app = FastAPI(title="MCP Server")
dispatcher: Dispatcher | None = None

@app.get("/symbol", response_model=SymbolDef | None)
def symbol(symbol: str):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return dispatcher.lookup(symbol)

@app.get("/search", response_model=list[SearchResult])
def search(q: str, semantic: bool = False, limit: int = 20):
    if dispatcher is None:
        raise HTTPException(503, "Dispatcher not ready")
    return list(dispatcher.search(q, semantic=semantic, limit=limit))
