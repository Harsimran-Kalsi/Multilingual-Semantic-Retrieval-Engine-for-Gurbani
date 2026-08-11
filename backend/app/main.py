from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from backend.app.generation import GroundedAnswerGenerator
from backend.app.feedback import FeedbackStore
from backend.app.retrieval import CorpusRetriever
from backend.app.schemas import (
    AskRequest,
    AskResponse,
    GroundedAnswer,
    FeedbackRequest,
    FeedbackResponse,
    PassageResponse,
    ReaderWindowResponse,
    SearchRequest,
    SearchResponse,
)

app = FastAPI(title="Gurbani Semantic Retrieval API", version="0.1.0")
retriever = CorpusRetriever()
answer_generator = GroundedAnswerGenerator()
feedback_store = FeedbackStore()
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
        retrieval_mode=(
            "hybrid" if any(result.dense_score is not None for result in results)
            else "keyword"
        ),
    )


@app.get("/passage/{verse_id}", response_model=PassageResponse)
def passage(verse_id: str) -> PassageResponse:
    lines = retriever.passage(verse_id)
    if not lines:
        raise HTTPException(status_code=404, detail="Verse not found")
    return PassageResponse(selected_verse_id=verse_id, lines=lines)


@app.get("/reader/{verse_id}", response_model=ReaderWindowResponse)
def reader_window(
    verse_id: str, before: int = 20, after: int = 20
) -> ReaderWindowResponse:
    if not 0 <= before <= 100 or not 0 <= after <= 100:
        raise HTTPException(status_code=400, detail="Reader window must be between 0 and 100 lines")
    lines, has_more_before, has_more_after = retriever.reader_window(
        verse_id, before=before, after=after
    )
    if not lines:
        raise HTTPException(status_code=404, detail="Verse not found")
    return ReaderWindowResponse(
        selected_verse_id=verse_id,
        lines=lines,
        has_more_before=has_more_before,
        has_more_after=has_more_after,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    record = retriever.records_by_id.get(request.verse_id)
    if not record:
        raise HTTPException(status_code=404, detail="Verse not found")
    expected_source = (record.get("citation") or {}).get("source_id")
    if expected_source != request.source_id:
        raise HTTPException(status_code=400, detail="Source does not match verse")
    feedback_id = feedback_store.record(request)
    return FeedbackResponse(recorded=True, feedback_id=feedback_id)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    sources = retriever.search(
        SearchRequest(query=request.question, top_k=request.top_k)
    )
    if not sources:
        raise HTTPException(status_code=404, detail="No relevant SGGS passages found")
    try:
        answer = answer_generator.generate(
            question=request.question,
            sources=sources,
            previous_questions=request.previous_questions,
        )
        return AskResponse(
            question=request.question,
            answer=answer,
            sources=sources,
            generated=True,
            model=answer_generator.model,
            retrieval_mode=(
                "hybrid" if any(source.dense_score is not None for source in sources)
                else "keyword"
            ),
        )
    except Exception as exc:
        return AskResponse(
            question=request.question,
            answer=GroundedAnswer(
                summary="Relevant SGGS passages were retrieved, but an AI explanation is not available.",
                summary_citation_ids=[],
                statements=[],
                caveat="Read the cited source cards below directly.",
            ),
            sources=sources,
            generated=False,
            model=answer_generator.model if answer_generator.available else None,
            generation_error=(
                str(exc)
                if not answer_generator.available
                else "The model request failed. Check the server API configuration."
            ),
            retrieval_mode=(
                "hybrid" if any(source.dense_score is not None for source in sources)
                else "keyword"
            ),
        )

