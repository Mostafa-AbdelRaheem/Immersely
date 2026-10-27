# app/services/session_chunks.py
"""Pure chunk assembly for scene-mode review sessions. No DB, no LLM."""
import uuid
from dataclasses import dataclass

SPEAKER_MAX_WORDS = 2
SENTENCE_PUNCTUATION = ".,!?;"


class MalformedSceneError(Exception):
    """The scene's line_sentence_map doesn't match its text."""


@dataclass(frozen=True)
class ChunkTarget:
    sentence_id: uuid.UUID
    speaker: str | None
    hint_en: str


@dataclass(frozen=True)
class Chunk:
    filler_lines: list[str]
    target: ChunkTarget | None


def _split_speaker(line: str) -> str | None:
    head, sep, _ = line.partition(": ")
    if not sep:
        return None
    if len(head.split()) > SPEAKER_MAX_WORDS:
        return None
    if any(ch in head for ch in SENTENCE_PUNCTUATION):
        return None
    return head


def build_scene_chunks(
    text_de: str,
    line_sentence_map: dict[str, int],
    sentence_en_by_id: dict[uuid.UUID, str],
) -> list[Chunk]:
    lines = text_de.split("\n")

    targets: list[tuple[int, uuid.UUID]] = []
    for key, index in line_sentence_map.items():
        try:
            sentence_id = uuid.UUID(key)
        except ValueError:
            raise MalformedSceneError(f"Invalid sentence id in map: {key!r}")
        if not 0 <= index < len(lines):
            raise MalformedSceneError(f"Line index {index} out of range")
        if sentence_id not in sentence_en_by_id:
            raise MalformedSceneError(f"No sentence data for {sentence_id}")
        targets.append((index, sentence_id))

    targets.sort()
    indexes = [index for index, _ in targets]
    if len(set(indexes)) != len(indexes):
        raise MalformedSceneError("Two targets map to the same line")

    chunks: list[Chunk] = []
    cursor = 0
    for index, sentence_id in targets:
        chunks.append(
            Chunk(
                filler_lines=lines[cursor:index],
                target=ChunkTarget(
                    sentence_id=sentence_id,
                    speaker=_split_speaker(lines[index]),
                    hint_en=sentence_en_by_id[sentence_id],
                ),
            )
        )
        cursor = index + 1

    if cursor < len(lines):
        chunks.append(Chunk(filler_lines=lines[cursor:], target=None))

    return chunks