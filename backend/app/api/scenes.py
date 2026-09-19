# app/api/scenes.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.scene import SceneRequest, SceneRead
from app.services.scene_verification import SceneVerificationFailedError
from app.services.scenes import NoDueSentencesError, get_or_create_scene

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("", response_model=SceneRead)
@limiter.limit("10/minute")
async def get_scene(
    request: Request,
    scene_in: SceneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        scene = await get_or_create_scene(
            db, current_user.id, scene_in.topic, max_targets=scene_in.max_targets
        )
    except NoDueSentencesError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No due sentences for topic '{scene_in.topic}'",
        )
    except SceneVerificationFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate a verified scene right now. Please try again.",
        )
    return scene