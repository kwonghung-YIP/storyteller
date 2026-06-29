import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from types import TracebackType
import uuid

from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncEngine, 
    async_sessionmaker, AsyncSession
)
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import joinedload

from .model import PostgresHostConfig, Chat, GoogleBatchJob

logger = logging.getLogger(__name__)

@asynccontextmanager
async def create_engine(postgres_url:str) -> AsyncGenerator[Any,Any,Any]:
    try:
        logger.info("create AsyncEngine for Postgres DB...")
        engine:AsyncEngine = create_async_engine(postgres_url, echo=True)
        yield engine
    except Exception as err:
        raise err
    finally:
        await engine.dispose()

@asynccontextmanager
async def open_session(pgHostConfig:PostgresHostConfig):
    postgres_url:str = pgHostConfig.to_connection_url()
    async with create_engine(postgres_url) as engine:
        try:
            sessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False)

            logger.info("call async_sessionmaker()... ")
            session:AsyncSession = sessionMaker()
            yield session
        
            logger.info("commit Session...")
            await session.commit()
        except Exception as err:
            logger.info("rollback Session...")
            await session.rollback()
            raise err
        finally:
            logger.info("close AsyncSession...")
            await session.close()

class ChatRepository:
    
    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def findById(self, chatId: uuid.UUID) -> Chat|None:
        stmt = select(Chat).options(joinedload(Chat.messages)).where(Chat.id==chatId)
        result = await self._session.scalars(stmt)
        return result.unique().one()
    
class GoolgeBatchJobRepository:
    
    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def findByName(self, name:str) -> GoogleBatchJob|None:
        stmt = select(GoogleBatchJob).where(GoogleBatchJob.name==name)
        result = await self._session.scalars(stmt)
        return result.unique().one()