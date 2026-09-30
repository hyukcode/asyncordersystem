Client
  │
  │ POST /orders
  ▼
FastAPI
  │
  ├── Redis
  │    ├── 接口限流
  │    ├── 防重复提交
  │    └── 订单缓存
  │
  ├── PostgreSQL / MySQL
  │    ├── orders
  │    └── outbox_events
  │
  └── RabbitMQ
         │
         ▼
      Worker
         │
         ├── 消费消息
         ├── 执行业务
         └── 更新订单状态
