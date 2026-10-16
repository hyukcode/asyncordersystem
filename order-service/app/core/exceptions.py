# 异常体系

# Domain / Business Exception

# 订单不存在
class OrderNotFoundError(Exception):
    pass

# 状态流转非法
class InvalidOrderStatusTransitionError(Exception):
    pass

# 并发更新冲突
class OptimisticLockError(Exception):
    pass