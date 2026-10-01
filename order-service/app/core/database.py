from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


# SQLAlchemy 和 数据库之间的核心入口 ，负责连接池、SQL dialect、连接创建、连接管理
engine = create_async_engine(
    settings.database_url,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# async_sessionmaker 是 SQLAlchemy 异步 Session 的工厂。
# bind 指定底层 AsyncEngine，
# class_ 指定生成 AsyncSession，
# expire_on_commit=False 用于避免事务提交后 ORM 实例属性被自动失效。
# 在异步 Web 服务中这样配置比较常见，可以避免提交后访问对象属性时触发隐式数据库 IO。

# session 更接近一次数据库工作单元，管理 ORM对象、事务状态、SQL执行、flush、commit、rollback
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session

# 创建 Session
#    ↓
# 进入数据库会话上下文
#    ↓
# 把 session 交给业务代码
#    ↓
# 业务代码执行完
#    ↓
# 自动退出上下文
#    ↓
# 关闭 Session