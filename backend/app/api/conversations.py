# app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.core.scenarios import SCENARIOS
from app.models.user import User
from app.schemas.conversation import (
    ChipRead,
    CorrectionRead,
    ScenarioRead,
    TurnRequest,
    TurnResponse,
)
from app.services.chat_logic import ChatInputError, ChatOutputError
from app.services.conversations import (
    ChatServiceBusyError,
    UnknownScenarioError,
    run_turn,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/scenarios", response_model=list[ScenarioRead])
async def list_scenarios(current_user: User = Depends(get_current_user)):
    return [ScenarioRead(id=s.id, title=s.title) for s in SCENARIOS]


@router.post("/turn", response_model=TurnResponse)
@limiter.limit("10/minute")
async def turn(
    request: Request,
    body: TurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history = [(m.role, m.text) for m in body.history]
    try:
        result = await run_turn(db, current_user.id, body.scenario_id, history)
    except UnknownScenarioError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found"
        )
    except ChatInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    except ChatServiceBusyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The chat service is busy. Please try again.",
        )
    except ChatOutputError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not produce a reply right now. Please try again.",
        )

    correction = None
    if result.correction is not None:
        correction = CorrectionRead(
            verdict=result.correction.grammar_verdict,
            corrected_text=result.correction.corrected_text,
            note=result.correction.note,
        )
    return TurnResponse(
        partner_reply=result.partner_reply,
        correction=correction,
        chips=[ChipRead.model_validate(s) for s in result.chips],
    )