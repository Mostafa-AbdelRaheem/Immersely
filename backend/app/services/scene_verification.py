# app/services/scene_verification.py
import uuid
import logging
from collections import Counter
from app.schemas.scene_generation import SceneGenerationOutput
from app.models.sentence import Sentence
from app.langchain_.scene_generation import generate_scene, verify_semantic_preservation

logger = logging.getLogger(__name__)


def check_structural_completeness(
    target_ids: list[uuid.UUID], generated: SceneGenerationOutput
) -> tuple[bool, list[uuid.UUID], list[uuid.UUID]]:
    """Every target id must appear exactly once as a line's
    target_sentence_id. Returns (ok, missing_ids, duplicated_ids).
    Cheap, deterministic — no LLM call, runs before any semantic check.
    """
    claimed_ids = [
        line.target_sentence_id
        for line in generated.lines
        if line.target_sentence_id is not None
    ]
    claim_counts = Counter(claimed_ids)

    present = set(claim_counts)
    missing = [tid for tid in target_ids if str(tid) not in present]
    duplicated = [
        tid for tid in target_ids if claim_counts.get(str(tid), 0) > 1
    ]

    ok = not missing and not duplicated
    return (ok, missing, duplicated)



MAX_GENERATION_ATTEMPTS = 3


class SceneVerificationFailedError(Exception):
    """Raised when generation could not produce a verifiably correct scene
    within MAX_GENERATION_ATTEMPTS retries."""
    pass

# app/services/scene_verification.py — replace the loop body

async def generate_verified_scene(
    topic: str, targets: list[Sentence], padding: list[Sentence]
) -> SceneGenerationOutput:
    target_ids = [s.id for s in targets]
    last_reason = "unknown"

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            generated = await generate_scene(topic, targets, padding)
        except Exception as exc:
            last_reason = f"generation call failed: {exc}"
            logger.warning("Scene generation attempt %d/%d failed: %s", attempt, MAX_GENERATION_ATTEMPTS, last_reason)
            continue

        ok, missing, duplicated = check_structural_completeness(target_ids, generated)
        if not ok:
            last_reason = f"structural check failed: missing={missing}, duplicated={duplicated}"
            logger.warning("Scene generation attempt %d/%d failed: %s", attempt, MAX_GENERATION_ATTEMPTS, last_reason)
            continue

        try:
            semantic = await verify_semantic_preservation(targets, generated)
        except Exception as exc:
            last_reason = f"semantic verification call failed: {exc}"
            logger.warning("Scene generation attempt %d/%d failed: %s", attempt, MAX_GENERATION_ATTEMPTS, last_reason)
            continue

        failed = [r for r in semantic.results if not r.preserved]
        if failed:
            last_reason = f"semantic check failed: {[(r.sentence_id, r.reason) for r in failed]}"
            logger.warning("Scene generation attempt %d/%d failed: %s", attempt, MAX_GENERATION_ATTEMPTS, last_reason)
            continue

        return generated

    raise SceneVerificationFailedError(
        f"Could not generate a verified scene for topic '{topic}' after "
        f"{MAX_GENERATION_ATTEMPTS} attempts. Last failure: {last_reason}"
    )