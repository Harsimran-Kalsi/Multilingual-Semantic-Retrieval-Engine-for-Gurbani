from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator


QueryText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]


class TranslationItem(BaseModel):
    lang: str
    text: str
    translator: Optional[str] = None


class VerseContext(BaseModel):
    shabad_id: str
    line_type: Optional[str] = None
    section_description: Optional[str] = None


class SearchRequest(BaseModel):
    query: QueryText = Field(description="User query in English, Roman Punjabi, or Gurmukhi")
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal['lexical', 'hybrid'] = Field(default='lexical', description='Wording lookup or optional semantic exploration')
    language_hint: Optional[Literal['en', 'pa', 'pa-guru']] = None
    filters: dict[str, str] = Field(default_factory=dict, description="Metadata filters such as raag/author")

    @field_validator('filters')
    @classmethod
    def validate_filters(cls, values: dict[str, str]) -> dict[str, str]:
        if set(values) - {'ang', 'raag', 'author'}:
            raise ValueError('Supported filters are ang, raag, and author')
        cleaned = {key: value.strip() for key, value in values.items()}
        if any(not value or len(value) > 200 for value in cleaned.values()):
            raise ValueError('Filter values must contain 1 to 200 characters')
        if 'ang' in cleaned:
            if not cleaned['ang'].isdigit() or not 1 <= int(cleaned['ang']) <= 1430:
                raise ValueError('Ang must be a number from 1 to 1430')
            cleaned['ang'] = str(int(cleaned['ang']))
        return cleaned


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
    fusion_score: Optional[float] = None
    match_explanation: str


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResult]
    retrieval_mode: str
    requested_mode: str = 'lexical'


class FeedbackRequest(BaseModel):
    query: QueryText
    verse_id: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=200)
    result_rank: int = Field(ge=1, le=20)
    helpful: bool
    sparse_score: Optional[float] = None
    dense_score: Optional[float] = None
    fusion_score: Optional[float] = None


class FeedbackResponse(BaseModel):
    recorded: bool
    feedback_id: int


class PassageResponse(BaseModel):
    selected_verse_id: str
    lines: list[SearchResult]


class ReaderWindowResponse(BaseModel):
    selected_verse_id: str
    lines: list[SearchResult]
    has_more_before: bool
    has_more_after: bool


class AskRequest(BaseModel):
    question: QuestionText
    top_k: int = Field(default=8, ge=3, le=12)
    previous_questions: list[QuestionText] = Field(default_factory=list, max_length=6)


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
    retrieval_mode: str = "keyword"
