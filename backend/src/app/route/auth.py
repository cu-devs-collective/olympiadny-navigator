import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import parse_qsl

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.core.config import Settings
from app.db.models.route import LoginSession, Student
from app.route.schemas import Me, Profile, SessionResponse


def validate_init_data(raw: str, token: str, max_age: int, now: float | None = None) -> int:
    now = time.time() if now is None else now
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        fields = dict(pairs)
        if len(pairs) != len(fields):
            raise ValueError("Duplicate keys")
        signature = fields.pop("hash")
        data = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid signature")
        age = now - int(fields["auth_date"])
        if not -30 <= age <= max_age:
            raise ValueError("Expired initData")
        user_id = json.loads(fields["user"])["id"]
        if type(user_id) is not int or not 0 < user_id < 2**63:
            raise ValueError("Invalid user")
        return user_id
    except (ValueError, KeyError, TypeError) as exc:
        raise ApiError(
            401, "invalid_init_data", "Откройте приложение заново через бота MAX"
        ) from exc


def describe_user(user: Student) -> Me:
    return Me(id=user.id, is_demo=user.max_user_id is None, profile=Profile(**user.profile))


async def jury_user(db: AsyncSession) -> Student:
    user = await db.get(Student, "jury:api")
    if user is None:
        user = Student(
            id="jury:api",
            profile=Profile(
                program_ids=["hse-pmi"], consent=True, notifications_enabled=True
            ).model_dump(),
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            user = await db.get(Student, "jury:api")
            if user is None:
                raise
    return user


async def issue_session(db: AsyncSession, user: Student, settings: Settings) -> SessionResponse:
    token = secrets.token_urlsafe(32)
    expires = time.time() + settings.session_ttl_seconds
    await db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=expires,
        )
    )
    await db.commit()
    return SessionResponse(token=token, expires_at=expires, user=describe_user(user))
