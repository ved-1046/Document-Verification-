"""Authenticated assignee lookup and administrator-only identity management."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.request import Request, RequestStatus
from app.schemas.user import AdminUserCreate, AdminUserCreated, AdminUserUpdate, UserRead, UserSummary

router = APIRouter(tags=["users"])


@router.get("/users/eligible-assignees", response_model=list[UserSummary])
def eligible_assignees(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    users = db.query(User).filter(
        User.is_active.is_(True),
        User.role.in_([UserRole.reviewer, UserRole.approver]),
        ~User.email.endswith(".local"),
    ).order_by(User.display_name.asc(), User.id.asc()).all()

    # Disambiguate duplicate display names within the same role by adding email
    name_counts = {}
    for u in users:
        key = (u.role, u.display_name)
        name_counts[key] = name_counts.get(key, 0) + 1

    result = []
    for u in users:
        if name_counts.get((u.role, u.display_name), 0) > 1:
            disp_name = f"{u.display_name} ({u.email})"
        else:
            disp_name = u.display_name
        result.append(UserSummary(id=u.id, display_name=disp_name, role=u.role))
    return result


@router.get("/admin/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/admin/users", response_model=AdminUserCreated, status_code=status.HTTP_201_CREATED)
def create_managed_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
):
    email = str(body.email).lower()
    if db.query(User.id).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Generated once and returned only to the authenticated administrator that
    # created this record. Only a bcrypt hash is persisted; never log the value.
    temporary_password = secrets.token_urlsafe(18)
    user = User(
        display_name=body.display_name,
        email=email,
        password_hash=hash_password(temporary_password),
        role=body.role,
        is_active=body.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserCreated(
        **UserRead.model_validate(user).model_dump(),
        temporary_password=temporary_password,
    )


@router.patch("/admin/users/{user_id}", response_model=UserRead)
def update_managed_user(
    user_id: int,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    updates = body.model_dump(exclude_unset=True)
    if "email" in updates:
        email = str(updates["email"]).lower()
        duplicate = db.query(User.id).filter(
            func.lower(User.email) == email, User.id != user_id
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        updates["email"] = email
    if user.id == admin.id and updates.get("is_active") is False:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own administrator account.")
    assignments = db.query(Request.id).filter(
        Request.status.notin_([RequestStatus.approved, RequestStatus.rejected]),
        ((Request.assigned_reviewer_id == user_id) | (Request.assigned_approver_id == user_id)),
    ).first()
    role_changed = "role" in updates and updates["role"] != user.role
    being_deactivated = updates.get("is_active") is False and user.is_active
    if assignments and (role_changed or being_deactivated):
        raise HTTPException(
            status_code=422,
            detail="Reassign this person's active requests before changing their role or deactivating the account.",
        )
    next_role = updates.get("role", user.role)
    next_active = updates.get("is_active", user.is_active)
    if user.role == UserRole.admin and (next_role != UserRole.admin or not next_active):
        remaining_admins = db.query(User.id).filter(
            User.role == UserRole.admin,
            User.is_active.is_(True),
            User.id != user_id,
        ).count()
        if remaining_admins == 0:
            raise HTTPException(status_code=422, detail="At least one active administrator must remain.")
    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
