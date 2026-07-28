from typing import Optional

from pydantic import BaseModel, Field


class TranslationItem(BaseModel):
    lang: str
    text: str
    translator: Optional[str] = None


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
    citation: VerseCitation
    sparse_score: Optional[float] = None
    dense_score: Optional[float] = None
    rerank_score: Optional[float] = None
    match_explanation: str


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResult]
