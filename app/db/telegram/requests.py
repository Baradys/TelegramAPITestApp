from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.telegram.models import User, TelegramProfile, TelegramSession


async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    stmt = select(User).where(User.id == user_id)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()


async def get_app_user(session: AsyncSession, email) -> User:
    stmt = select(User).where(User.email == email)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()


async def create_user(
        session: AsyncSession,
        email,
        password_hash

):
    user = User(
        email=email,
        password_hash=password_hash
    )
    async with session as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_profile_by_phone(session: AsyncSession, phone: str) -> TelegramProfile | None:
    stmt = select(TelegramProfile).where(TelegramProfile.phone == phone)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()


async def get_profile_by_user_and_phone(
        session: AsyncSession,
        user_id: int,
        phone: str,
) -> TelegramProfile | None:
    stmt = select(TelegramProfile).where(
        TelegramProfile.user_id == user_id,
        TelegramProfile.phone == phone,
    )
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()


async def create_profile(
        session: AsyncSession,
        user_id: int,
        phone: str,
        is_authorized: bool,
        phone_code_hash: str | None = None,
) -> TelegramProfile:
    profile = TelegramProfile(
        user_id=user_id,
        phone=phone,
        is_authorized=is_authorized,
        phone_code_hash=phone_code_hash,
    )
    async with session as session:
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def update_profile(
        session: AsyncSession,
        profile: TelegramProfile,
        *,
        is_authorized: bool | None = None,
        phone_code_hash: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
) -> TelegramProfile:
    if is_authorized is not None:
        profile.is_authorized = is_authorized
    if phone_code_hash is not None:
        profile.phone_code_hash = phone_code_hash
    if first_name is not None:
        profile.first_name = first_name
    if last_name is not None:
        profile.last_name = last_name
    if username is not None:
        profile.username = username
    profile.last_login = datetime.now()
    async with session as session:
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def get_tg_profile(session: AsyncSession, user_id, profile_id) -> TelegramProfile:
    stmt = select(TelegramProfile).where(TelegramProfile.id == profile_id, TelegramProfile.user_id == user_id)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()

async def get_users_profiles(session: AsyncSession, user_id) -> Sequence[TelegramProfile]:
    stmt = select(TelegramProfile).where(TelegramProfile.user_id == user_id)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalars().all()


async def create_tg_session(
        session: AsyncSession,
        profile_id,
        session_string):
    tg_session = TelegramSession(
        profile_id=profile_id,
        session_string=session_string,
        is_active=True
    )
    async with session as session:
        session.add(tg_session)
        await session.commit()


async def get_tg_session(session: AsyncSession, profile_id) -> TelegramSession:
    stmt = select(TelegramSession).where(TelegramSession.profile_id == profile_id, TelegramSession.is_active == True)
    async with session as session:
        result = await session.execute(stmt)
        return result.unique().scalar()


async def update_session(
        session: AsyncSession,
        tg_session: TelegramSession,
        *,
        is_active: bool | None = None,
        session_string: str | None = None,
) -> TelegramSession:
    if is_active is not None:
        tg_session.is_active = is_active
    if session_string is not None:
        tg_session.session_string = session_string
    async with session as session:
        session.add(tg_session)
        await session.commit()
        await session.refresh(tg_session)
        return tg_session


