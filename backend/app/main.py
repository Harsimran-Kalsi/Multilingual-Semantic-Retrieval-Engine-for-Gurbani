from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import SearchRequest, SearchResponse

app = FastAPI(title="Gurbani Semantic Retrieval API", version="0.1.0")
retriever = CorpusRetriever()
frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(frontend_path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    normalized_query = request.query.strip()
    results = retriever.search(request)
    return SearchResponse(
        query=request.query,
        normalized_query=normalized_query,
        results=results,
    )
