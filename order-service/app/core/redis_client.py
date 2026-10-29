from redis.asyncio import Redis
from app.core.config import settings
from fastapi import Request

def create_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

def get_redis(
    request: Request,
) -> Redis:
    return request.app.state.redis


# GET /orders/123
#         ↓
#       Redis
#      /     \
#    hit     miss
#     ↓        ↓
#  返回缓存    MySQL
#               ↓
#            写 Redis
#               ↓
#             返回

# 订单状态发生修改
#         ↓
#      MySQL commit
#         ↓
#    DELETE Redis cache