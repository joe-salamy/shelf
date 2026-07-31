"""Durable summary checkpoints for resumable LLM summarization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from shelf.models import BookTree
from shelf.summarize.models import (
    ChapterSummary,
    Entity,
    Relationship,
    SectionSummary,
)

CHECKPOINT_VERSION = 1


class SummaryCheckpointStore:
    """Load and save validated summary artifacts by stable content keys."""

    def __init__(
        self,
        cache_dir: Path,
        tree: BookTree,
        *,
        max_chars: int,
        section_limit: int | None,
        section_offset: int,
        backend_options: dict[str, Any],
    ) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        source_path = str(tree.source_path) if tree.source_path else ""
        self._base_parts = {
            "version": CHECKPOINT_VERSION,
            "book_title": tree.title,
            "source_path": source_path,
            "source_name": tree.source_path.name if tree.source_path else "",
            "max_chars": max_chars,
            "section_limit": section_limit,
            "section_offset": section_offset,
            "backend_options": backend_options,
        }

    def section_key(
        self,
        chapter_title: str,
        section_index: int,
        section_title: str,
        content: str,
        prompt: str,
    ) -> str:
        return self._key(
            {
                "kind": "section",
                "chapter_title": chapter_title,
                "section_index": section_index,
                "section_title": section_title,
                "content_hash": _hash_text(content),
                "prompt_hash": _hash_text(prompt),
            }
        )

    def chapter_key(self, chapter_title: str, input_text: str, prompt: str) -> str:
        return self._key(
            {
                "kind": "chapter",
                "chapter_title": chapter_title,
                "input_hash": _hash_text(input_text),
                "prompt_hash": _hash_text(prompt),
            }
        )

    def book_key(self, input_text: str, prompt: str) -> str:
        return self._key(
            {
                "kind": "book",
                "input_hash": _hash_text(input_text),
                "prompt_hash": _hash_text(prompt),
            }
        )

    def load_section(self, key: str) -> SectionSummary | None:
        data = self._load_payload(key, "section")
        if data is None:
            return None
        try:
            return _section_from_dict(data)
        except (KeyError, TypeError, ValueError):
            return None

    def save_section(self, key: str, summary: SectionSummary) -> None:
        self._save_payload(key, "section", asdict(summary))

    def load_chapter(self, key: str) -> ChapterSummary | None:
        data = self._load_payload(key, "chapter")
        if data is None:
            return None
        try:
            return _chapter_from_dict(data)
        except (KeyError, TypeError, ValueError):
            return None

    def save_chapter(self, key: str, summary: ChapterSummary) -> None:
        self._save_payload(key, "chapter", asdict(summary))

    def load_book_overview(self, key: str) -> str | None:
        data = self._load_payload(key, "book")
        if not isinstance(data, dict):
            return None
        overview = data.get("overview")
        return overview if isinstance(overview, str) else None

    def save_book_overview(self, key: str, overview: str) -> None:
        self._save_payload(key, "book", {"overview": overview})

    def _key(self, parts: dict[str, Any]) -> str:
        payload = {**self._base_parts, **parts}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()

    def _path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def _load_payload(self, key: str, kind: str) -> Any | None:
        try:
            with self._path(key).open(encoding="utf-8") as f:
                wrapper = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        if (
            not isinstance(wrapper, dict)
            or wrapper.get("version") != CHECKPOINT_VERSION
            or wrapper.get("kind") != kind
            or wrapper.get("key") != key
        ):
            return None
        return wrapper.get("data")

    def _save_payload(self, key: str, kind: str, data: Any) -> None:
        path = self._path(key)
        tmp_path = path.with_suffix(".json.tmp")
        wrapper = {
            "version": CHECKPOINT_VERSION,
            "kind": kind,
            "key": key,
            "data": data,
        }
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(wrapper, f, ensure_ascii=False, indent=2)
            f.write("\n")
        tmp_path.replace(path)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _entity_from_dict(data: dict[str, Any]) -> Entity:
    return Entity(
        name=str(data["name"]),
        kind=str(data["kind"]),
        definition=str(data["definition"]),
    )


def _relationship_from_dict(data: dict[str, Any]) -> Relationship:
    return Relationship(
        source=str(data["source"]),
        relation=str(data["relation"]),
        target=str(data["target"]),
    )


def _section_from_dict(data: dict[str, Any]) -> SectionSummary:
    return SectionSummary(
        section_title=str(data["section_title"]),
        chapter_title=str(data["chapter_title"]),
        summary=str(data["summary"]),
        key_points=[str(item) for item in data.get("key_points", [])],
        entities=[
            _entity_from_dict(item)
            for item in data.get("entities", [])
            if isinstance(item, dict)
        ],
        relationships=[
            _relationship_from_dict(item)
            for item in data.get("relationships", [])
            if isinstance(item, dict)
        ],
        prerequisites=[str(item) for item in data.get("prerequisites", [])],
        leads_to=[str(item) for item in data.get("leads_to", [])],
    )


def _chapter_from_dict(data: dict[str, Any]) -> ChapterSummary:
    return ChapterSummary(
        chapter_title=str(data["chapter_title"]),
        summary=str(data["summary"]),
        section_summaries=[
            _section_from_dict(item)
            for item in data.get("section_summaries", [])
            if isinstance(item, dict)
        ],
        entities=[
            _entity_from_dict(item)
            for item in data.get("entities", [])
            if isinstance(item, dict)
        ],
        relationships=[
            _relationship_from_dict(item)
            for item in data.get("relationships", [])
            if isinstance(item, dict)
        ],
    )
