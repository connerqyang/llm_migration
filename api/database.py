from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import os
from typing import AsyncGenerator

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./llm_migration.db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def init_db():
    """Initialize the database and create tables if they don't exist"""
    try:
        async with engine.begin() as conn:
            # Check if database is accessible
            await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
        # Import models to ensure they are registered
        from db_models import Component, Migration, ValidationStep, ErrorLog, MigrationMetric
        
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Database tables initialized")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """Close database connections"""
    await engine.dispose()