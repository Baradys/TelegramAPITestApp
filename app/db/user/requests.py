from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.user.models import User


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