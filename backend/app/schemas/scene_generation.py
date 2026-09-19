# app/schemas/scene_generation.py
from pydantic import BaseModel, Field


class SceneLineOutput(BaseModel):
    speaker: str | None = Field(
        None,
        description="Speaker name for dialogue lines, or null for narrative/monologue lines.",
    )
    text_de: str = Field(..., description="The line's text in German.")
    text_en: str = Field(..., description="English translation of this line.")
    target_sentence_id: str | None = Field(
        None,
        description=(
            "If this line is (a near-verbatim rendering of, minor conjugation "
            "allowed) one of the provided target sentences, its id as a string. "
            "Null for connective/flavor lines that are not a target sentence."
        ),
    )


class SceneGenerationOutput(BaseModel):
    lines: list[SceneLineOutput] = Field(
        ..., description="The scene's lines in order, dialogue or narrative."
    )


class SemanticVerificationResult(BaseModel):
    sentence_id: str = Field(..., description="The target sentence id being checked.")
    preserved: bool = Field(
        ...,
        description=(
            "True if the scene line's meaning matches the target sentence's "
            "meaning (minor conjugation/tense changes allowed), false if the "
            "wording or meaning has drifted too far or changed the core meaning."
        ),
    )
    reason: str = Field(
        ..., description="One short sentence explaining the verdict."
    )


class SceneSemanticVerificationOutput(BaseModel):
    results: list[SemanticVerificationResult]