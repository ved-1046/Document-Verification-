"""
Auth routes: register, login, get current user.

POST /api/v1/auth/register  — create account
POST /api/v1/auth/login     — returns JWT
GET  /api/v1/auth/me        — returns current authenticated user
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, PasswordChange, Token, UserCreate, UserRead
from app.services.user_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201,
             summary="Register a new user account")
def register(body: UserCreate, db: Session = Depends(get_db)):
    # Public registration must never grant privileged roles. Reviewer and
    # approver accounts are provisioned by an administrator/seed process.
    if body.role != UserRole.submitter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is limited to submitter accounts.",
        )
    user = register_user(
        db,
        display_name=body.display_name,
        email=body.email,
        password=body.password,
        role=body.role,
    )
    return user


@router.post("/login", response_model=Token, summary="Log in and receive a JWT")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user, token = authenticate_user(db, body.email, body.password)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead, summary="Return the currently authenticated user")
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", summary="Change the authenticated user's password")
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    if verify_password(body.new_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose a password different from the current password.")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"detail": "Password changed successfully."}
