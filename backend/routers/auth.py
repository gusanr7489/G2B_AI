from fastapi import APIRouter, Depends, HTTPException, Response, status

from database import get_db
from dependencies import get_current_user, require_admin
from schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db=Depends(get_db)):
    """로그인 → JWT 발급"""
    user = await db.fetchrow(
        "SELECT id, email, password_hash, name, role, is_active FROM users WHERE email = $1",
        body.email,
    )
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    access_token = create_access_token(user["id"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    # Refresh 토큰은 httpOnly 쿠키로
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token)


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: UserCreate,
    admin=Depends(require_admin),
    db=Depends(get_db),
):
    """사용자 초대 (admin only)"""
    existing = await db.fetchrow(
        "SELECT id FROM users WHERE email = $1", body.email
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다",
        )

    password_hash = hash_password(body.password)
    user = await db.fetchrow(
        """
        INSERT INTO users (email, password_hash, name, role)
        VALUES ($1, $2, $3, $4)
        RETURNING id, email, name, role, is_active, created_at
        """,
        body.email,
        password_hash,
        body.name,
        body.role,
    )
    return UserResponse(**dict(user))


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user)):
    """현재 로그인한 사용자 정보"""
    return UserResponse(**user)
