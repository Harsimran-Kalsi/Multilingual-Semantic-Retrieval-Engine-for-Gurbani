from typing import Optional

from pydantic import BaseModel, Field


class TranslationItem(BaseModel):
    lang: str
    text: str
    translator: Optional[str] = None


class VerseContext(BaseModel):
    shabad_id: str
    line_type: Optional[str] = None
    section_description: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="User query in English, Roman Punjabi, or Gurmukhi")
    top_k: int = Field(default=5, ge=1, le=20)
    language_hint: Optional[str] = Field(default=None, description="Optional hint: en, pa, pa-guru")
    filters: dict[str, str] = Field(default_factory=dict, description="Metadata filters such as raag/author")


class VerseCitation(BaseModel):
    ang: int
    raag: Optional[str] = None
    author: Optional[str] = None
    source_id: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class SearchResult(BaseModel):
    verse_id: str
    gurmukhi: str
    transliteration: Optional[str] = None
    translation: Optional[str] = None
    translations: list[TranslationItem] = Field(default_factory=list)
    context: Optional[VerseContext] = None
    citation: VerseCitation
    sparse_score: Optional[float] = None
    dense_score: Optional[float] = None
    rerank_score: Optional[float] = None
    match_explanation: str


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResult]


class PassageResponse(BaseModel):
    selected_verse_id: str
    lines: list[SearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int = Field(default=8, ge=3, le=12)
    previous_questions: list[str] = Field(default_factory=list, max_length=6)


class GroundedStatement(BaseModel):
    text: str
    citation_ids: list[str] = Field(default_factory=list)


class GroundedAnswer(BaseModel):
    summary: str
    summary_citation_ids: list[str] = Field(default_factory=list)
    statements: list[GroundedStatement] = Field(default_factory=list)
    caveat: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    answer: GroundedAnswer
    sources: list[SearchResult]
    generated: bool
    model: Optional[str] = None
    generation_error: Optional[str] = None
