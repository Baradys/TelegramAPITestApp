from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session.models import TelegramSession


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
