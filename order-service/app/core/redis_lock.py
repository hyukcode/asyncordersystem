from uuid import uuid4

from redis.asyncio import Redis

RELEASE_LOCK_SCRIPT = """
if redis.call("get, KEYS[1] == ARGV[1] then
    return redis.call("del", KEYS[1])
else 
    return 0
end
"""

class RedisLock:

    def __init__(
        self,
        redis: Redis,
        key: str,
        ttl: int = 30,
    ):
        self.redis = redis
        self.key = key
        self.ttl = ttl
        self.token = uuid4().hex
        self.acquired = False

    async def acquire(self) -> bool:
        self.acquired = bool(
            await self.redis.set(
                self.key,
                self.token,
                nx=True,
                ex=self.ttl,
            )
        )
        return self.acquired

    async def release(self) -> None:
        if not self.acquired:
            return
        
        await self.redis.eval(
            RELEASE_LOCK_SCRIPT,
            1,
            self.key,
            self.token,
        )
        self.acquired = False


'''
    set key token nx ex 30
    nx 键不存在时才允许写入
    ex 30 30s过期，避免进程崩溃后永久占锁
    token 每个锁持有自己的随机标识

    释放锁 需要Lua脚本原子比较token并删除
'''