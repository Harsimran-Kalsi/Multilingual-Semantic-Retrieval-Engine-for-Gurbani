import json
import os
from typing import Optional

from backend.app.schemas import GroundedAnswer, GroundedStatement, SearchResult


SYSTEM_INSTRUCTIONS = """You are a careful Gurbani research companion.
Answer only from the supplied Sri Guru Granth Sahib passages and translations.
Do not claim that your answer is the only Sikh interpretation. Distinguish the
scripture from the English translator's wording. Do not invent quotations,
Angs, authors, context, or source IDs. Every substantive statement must cite
one or more supplied source_id values. If the passages do not adequately answer
the question, say that directly in the caveat. Use respectful, plain language.
Never cite general knowledge or material outside the supplied passages."""


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "summary_citation_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "citation_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "citation_ids"],
                "additionalProperties": False,
            },
        },
        "caveat": {"type": ["string", "null"]},
    },
    "required": ["summary", "summary_citation_ids", "statements", "caveat"],
    "additionalProperties": False,
}


class GroundedAnswerGenerator:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _source_text(sources: list[SearchResult]) -> str:
        blocks = []
        for source in sources:
            blocks.append(
                json.dumps(
                    {
                        "source_id": source.citation.source_id,
                        "ang": source.citation.ang,
                        "author": source.citation.author,
                        "raag_or_section": source.citation.raag,
                        "gurmukhi": source.gurmukhi,
                        "transliteration": source.transliteration,
                        "english_translation": source.translation,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(blocks)

    @staticmethod
    def _validate_citations(
        answer: GroundedAnswer,
        sources: list[SearchResult],
    ) -> GroundedAnswer:
        allowed = {source.citation.source_id for source in sources}
        valid_summary_ids = list(dict.fromkeys(
            source_id
            for source_id in answer.summary_citation_ids
            if source_id in allowed
        ))
        if not valid_summary_ids:
            raise ValueError("The generated summary did not contain valid source citations.")
        statements = []
        for statement in answer.statements:
            valid_ids = list(dict.fromkeys(
                source_id
                for source_id in statement.citation_ids
                if source_id in allowed
            ))
            if valid_ids:
                statements.append(
                    GroundedStatement(text=statement.text, citation_ids=valid_ids)
                )
        if not statements:
            raise ValueError("The generated answer did not contain valid source citations.")
        return GroundedAnswer(
            summary=answer.summary,
            summary_citation_ids=valid_summary_ids,
            statements=statements,
            caveat=answer.caveat,
        )

    def generate(
        self,
        question: str,
        sources: list[SearchResult],
        previous_questions: Optional[list[str]] = None,
    ) -> GroundedAnswer:
        if not self.available:
            raise RuntimeError("Set OPENAI_API_KEY to enable grounded AI answers.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Install project requirements to enable grounded AI answers."
            ) from exc

        history = "\n".join(
            f"- {item.strip()}" for item in (previous_questions or []) if item.strip()
        )
        prompt = (
            f"Current question:\n{question.strip()}\n\n"
            f"Earlier questions for conversational context only:\n{history or '(none)'}\n\n"
            "Retrieved sources (the only evidence you may use):\n"
            f"{self._source_text(sources)}"
        )
        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=prompt,
            reasoning={"effort": "low"},
            text={
                "verbosity": "medium",
                "format": {
                    "type": "json_schema",
                    "name": "grounded_gurbani_answer",
                    "strict": True,
                    "schema": ANSWER_SCHEMA,
                },
            },
        )
        payload = GroundedAnswer.model_validate_json(response.output_text)
        return self._validate_citations(payload, sources)
