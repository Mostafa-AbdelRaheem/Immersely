# app/api/sentence_import.py
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.sentence_import import ImportPreviewOut
from app.services.bulk_import_logic import MissingColumnsError, TooManyRowsError
from app.services.bulk_import_reader import InvalidSpreadsheetError
from app.services.sentence_import import build_preview, load_existing_keys

router = APIRouter(prefix="/sentences/import", tags=["sentence-import"])

# Plain numbers on purpose: Starlette renamed the 413/422 constants recently.
_BAD_REQUEST = 400
_TOO_LARGE = 413
_UNPROCESSABLE = 422


@router.post("/preview", response_model=ImportPreviewOut)
@limiter.limit("3/minute")
async def preview(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Read one byte past the limit so an oversized file is detected, not truncated.
    # The filename and content type are client-controlled and are never trusted.
    data = await file.read(settings.bulk_import_max_upload_bytes + 1)
    existing_keys = await load_existing_keys(db, current_user.id)
    try:
        return await build_preview(data, existing_keys=existing_keys)
    except InvalidSpreadsheetError as exc:
        status_code = _BAD_REQUEST if exc.code == "unreadable" else _TOO_LARGE
        raise HTTPException(status_code=status_code, detail={"code": exc.code})
    except MissingColumnsError as exc:
        raise HTTPException(
            status_code=_UNPROCESSABLE,
            detail={"code": "missing_columns", "missing": exc.missing},
        )
    except TooManyRowsError as exc:
        raise HTTPException(
            status_code=_TOO_LARGE,
            detail={"code": "too_many_rows", "limit": exc.limit, "count": exc.count},
        )
