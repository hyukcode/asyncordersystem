                     ┌──────────────┐
                     │   Client     │
                     └──────┬───────┘
                            │ HTTP
                            ▼
                     ┌──────────────┐
                     │   FastAPI    │
                     │  API Server  │
                     └───┬────┬─────┘
                         │    │
              ┌──────────┘    └────────────┐
              ▼                            ▼
       ┌─────────────┐              ┌─────────────┐
       │    Redis    │              │ PostgreSQL  │
       │ Cache/Lock  │              │  Cloud DB   │
       └─────────────┘              └─────────────┘
              │
              │
              ▼
       ┌─────────────┐
       │  RabbitMQ   │
       │ Message MQ  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │   Worker    │
       │ async task  │
       └──────┬──────┘
              ▼
       PostgreSQL / Redis

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

| 项目能力 | 对应面试知识 |
|---|---|
| FastAPI | ASGI、async/await、依赖注入、中间件 |
| SQLAlchemy | ORM、Session、连接池、事务 |
| PostgreSQL/MySQL | 索引、事务、隔离级别、锁 |
| Redis Cache | Cache Aside、缓存穿透、击穿、雪崩 |
| Redis 幂等 | SET NX、TTL |
| Redis 限流 | INCR、Lua、滑动窗口 |
| RabbitMQ | Producer、Consumer、ACK、重试、DLQ |
| Worker | 异步任务、削峰填谷 |
| Outbox | DB + MQ 分布式一致性 |
| Docker | 镜像、容器、网络、volume |
| Nginx | 反向代理、TLS |
| ECS | Linux、端口、安全组、部署 |
| 日志 | trace_id、结构化日志 |
| API | REST、状态码、幂等 |
| 高并发 | 连接池、限流、异步 IO |
| 故障处理 | timeout、retry、幂等、降级 |

FastAPI + SQLAlchemy：建立项目结构，实现订单 CRUD，搞清楚 async/await、依赖注入、Session、连接池。
数据库工程化：加入 PostgreSQL/MySQL、Alembic、事务、索引、分页、行锁。
Redis 缓存：实现 Cache Aside，处理缓存穿透、击穿、雪崩。
Redis 幂等 + 分布式锁：解决重复下单和并发问题。
RabbitMQ：实现 Producer/Consumer，理解 Exchange、Queue、Routing Key。
可靠消息：加入 ACK、Retry、DLQ、幂等 Consumer。
数据库与 MQ 一致性：故意制造“DB 成功但 MQ 发送失败”，然后使用 Transactional Outbox 修复。
高并发：加入限流、连接池、MQ prefetch、批量消费和 asyncio。
工程化：加入 logging、trace_id、异常处理、JWT、pytest。
部署：Docker → Docker Compose → ECS → Nginx → HTTPS → 日志和监控。


ACK
NACK
Retry
DLQ
prefetch
exchange
routing key

消息队列的作用： 异步 解耦 削峰
创建订单时，只执行订单数据落库以及核心校验，像支付模拟、通知、积分等非同步完成的任务通过 RabbitMQ 投递给 Worker。
这样可以降低接口响应时间，同时在流量突增时由 MQ 暂存任务，Consumer 按自己的消费能力处理，相当于把瞬时流量转化成稳定流量。


Redis 五件事
1. Cache Aside
缓存穿透
缓存击穿
缓存雪崩
TTL
缓存一致性

2. 接口幂等 Redis SET NX 
防止 用户点两次按钮
    网络重试
    客户端超时重发

3. 分布式锁
SET key value NX EX 30
SET NX
锁超时
锁续期
误删除锁
Redlock

4. API限流
fixed window
sliding window
token bucket
leaky bucket

5. 热点数据
将热门商品信息缓存


Redis 是否应该 Docker 跑？
RabbitMQ 是否应该 Docker 跑？
数据库为什么最好使用云数据库？

RabbitMQ → Kafka 对比两种消息系统


第一步
1. FastAPI 为什么性能比较高？

2. async def 和 def 有什么区别？

3. asyncio 为什么适合 Web 服务？

4. SQLAlchemy Session 是什么？

5. 数据库连接池为什么存在？

6. 一个 HTTP 请求应该对应一个 Session 吗？

7. commit / flush / refresh 有什么区别？

8. 数据库事务 ACID 分别是什么？

AsyncSession
事务
连接池
索引
唯一索引
悲观锁
乐观锁
MVCC
隔离级别
慢SQL
EXPLAIN
N+1
分页

FastAPI 项目采用 API、Service、Repository 分层。API 层负责 HTTP 参数校验和响应，Service 层负责业务逻辑和事务边界，Repository 层封装 SQLAlchemy 数据访问。
数据库使用 SQLAlchemy AsyncEngine 和 AsyncSession。每个 HTTP 请求通过 FastAPI Dependency 获取独立 Session，请求结束后释放 Session，而底层数据库连接由 Engine 的连接池复用。
创建订单时 Repository 负责 add 和 flush，Service 层统一控制 commit 和 rollback，这样多个数据库操作可以处于同一个业务事务中。

uvicorn[standard] asig server

configuration code 分离 数据库地址、Redis地址、MQ连接信息通过环境变量注入，同一份镜像可以运行在开发、测试、生产环境

Alembic 管理数据库结构版本

Redis SET NX EX + MYSQL唯一约束

客户端请求 携带 Idempotency-Key请求头
Redis SET NX EX 尝试获得该幂等键的短期锁
加锁成功 - mysql检查幂等建，创建订单并提交事务 - 返回订单
加锁失败 - 存在则复用结果，否则请求重试 - 200 或 409

Redis锁：减少同一请求的并发竞争
MySQL唯一约束：保证数据库中同一个幂等键最多对应一笔订单，是最终正确性保障
请求指纹：防止一个幂等键被复用于不同订单参数

MVCC 版本号 乐观锁 擅长读不阻塞写，写不阻塞普通读
MYSQL InnoDB 默认事务隔离级别 REPEATABLE READ
SELECT ... consistent read 快照读

BEGIN 
SELECT ... FOR UPDATE 拿到行锁 
UPDATE
COMMIT
释放锁

BEGIN
SELECT FOR UPDATE
持锁
业务逻辑
COMMIT / ROLLBACK
释放锁

悲观锁
先锁再改 
高冲突场景（库存扣减 余额扣款 抢票 订单状态流转）
缺点 请求等待 吞吐下降 可能死锁 锁超时

并发考虑冲突概率

另一种 乐观锁 先不锁，更新时检查“这条数据还是不是当初看到的版本”
不锁 -> 大家都可以读 -> 更新时检查version -> version没变，则更新成功；version变了，并发冲突
适合 读很多，真正同时修改同一条数据概率相对低的场景
乐观锁 真正重要的是 update的where条件里必须带旧version

aio-pika 提供 connect_robust()，适合长时间运行的异步服务
AMQP 在一个连接上可以复用多个channel

Lua脚本
错误做法：GET lock -> 检查token 中间锁过期，被别人获取 -> DEL lock 可能删掉别人的锁
正确做法：比较 token + 删除，在 Redis 内部一次原子执行

POST /orders
|
Pydantic validation
|
Idempotency-Key
|
查询旧订单 - 无 - INSERT Order - UNIQUE Constraint - COMMIT - RabbitMQ
｜
有
｜
返回旧订单

HTTP 幂等
数据库唯一约束
并发竞争
IntegrityError
事务 rollback
Redis 分布式锁
RabbitMQ Publisher

orders + outbox_events -> COMMIT
outbox_events(PENDING) -> Outbox Relay -> RabbitMQ -> outbox_events(PUBLISHED)

