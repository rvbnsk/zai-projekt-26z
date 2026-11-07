from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..db import get_db
from ..schemas import LoginRequest, LoginResponse, PasswordChange
from ..security import TOKEN_TTL_SECONDS, current_session, hash_password, new_secret, sha256, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: DbSession = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.username == data.username))
    if user is None or not verify_password(user.password_hash, data.password):
        raise HTTPException(401, "Invalid username or password")

    token = new_secret()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
    db.add(models.Session(user_id=user.id, token_hash=sha256(token), expires_at=expires_at))
    db.commit()
    return LoginResponse(accessToken=token, expiresIn=TOKEN_TTL_SECONDS)


@router.post("/logout", status_code=204)
def logout(session: models.Session = Depends(current_session), db: DbSession = Depends(get_db)):
    db.delete(session)
    db.commit()
    return Response(status_code=204)


@router.put("/password", status_code=204)
def change_password(
    data: PasswordChange,
    session: models.Session = Depends(current_session),
    db: DbSession = Depends(get_db),
):
    user = db.get(models.User, session.user_id)
    if not verify_password(user.password_hash, data.currentPassword):
        raise HTTPException(403, "Current password is incorrect")
    user.password_hash = hash_password(data.newPassword)
    db.commit()
    return Response(status_code=204)
