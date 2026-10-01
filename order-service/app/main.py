from fastapi import FastAPI 

from app.api.orders import router as order_router

app = FastAPI(
    title="Order Service",
    version="1.0.0",
)
# 创建了一个应用对象
# ASGI Server 监听8000端口 接收TCP请求 解析HTTP 管理连接

app.include_router(order_router)

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }