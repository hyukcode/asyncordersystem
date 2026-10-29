from contextlib import asynccontextmanager
from fastapi import FastAPI 

from app.api.orders import router as order_router
from app.core.redis_client import create_redis
# from app.mq.rabbitmq import rabbitmq_publisher


# lifespan 管理应用级资源

# uvicorn start 
# RabbitMQ connect
# FastAPI 接收请求 
# ...
# uvicorn shutdown
# RabbitMQ close

@asynccontextmanager
async def lifespan(app: FastAPI):
#     await rabbitmq_publisher.connect()

    redis = create_redis()

    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()
#         await rabbitmq_publisher.close()

app = FastAPI(
    title="Async Order System",
    version="1.0.0",
    lifespan=lifespan,
)

# 创建了一个应用对象
# ASGI Server 监听8000端口 接收TCP请求 解析HTTP 管理连接

app.include_router(order_router)

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# RabbitMQ Connection 和 FastAPI Application 生命周期绑定

# 启动 -> RabbitMQ connect -> Redis connect -> yield 应用运行 -> Redis close -> RabbitMQ close
