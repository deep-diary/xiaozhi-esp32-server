# 连接管理器架构说明

## 概述

本次重构创建了统一的连接管理器 `ConnectionManager`，集中管理所有WebSocket连接（设备端和Web端），提供清晰的消息转发接口。

## 架构设计

### 1. 核心类

#### ConnectionManager (`core/connection_manager.py`)
- **职责**: 统一管理所有连接（设备端和Web端）
- **功能**:
  - 管理设备连接: `{device_id: ConnectionHandler}`
  - 管理Web连接: `{device_id: set(WebConnectionHandler)}` - 一个device_id可对应多个Web客户端
  - 提供统一的消息转发接口

#### WebSocketServer (`core/websocket_server.py`)
- **职责**: WebSocket服务器，使用ConnectionManager管理连接
- **简化**: 移除了分散的连接管理逻辑，统一使用 `connection_manager`

#### WebConnectionHandler (`core/web_connection.py`)
- **职责**: 处理Web/Gradio客户端连接
- **功能**: 处理Web客户端消息，转发到对应的设备连接

#### ConnectionHandler (`core/connection.py`)
- **职责**: 处理设备连接
- **功能**: 处理设备消息，通过ConnectionManager转发到Web客户端

### 2. 连接管理接口

#### ConnectionManager 提供的方法

1. **连接注册/注销**
   - `register_device(device_id, connection_handler)`: 注册设备连接
   - `unregister_device(device_id)`: 注销设备连接
   - `register_web(device_id, web_handler)`: 注册Web客户端连接
   - `unregister_web(device_id, web_handler)`: 注销Web客户端连接
   - `get_device_connection(device_id)`: 根据device_id获取设备连接

2. **消息转发**
   - `broadcast_to_all_web(message)`: 广播消息到所有Web客户端
   - `broadcast_to_all_devices(message)`: 广播消息到所有设备连接
   - `forward_to_web_by_device_id(device_id, message)`: 根据device_id转发消息到匹配的Web客户端
   - `forward_to_device_by_device_id(device_id, message)`: 根据device_id转发消息到匹配的设备连接

3. **统计信息**
   - `get_connection_stats()`: 获取连接统计信息

### 3. 消息流转

#### Web客户端 → 设备连接
```
Web客户端发送消息
    ↓
WebConnectionHandler._process_web_message()
    ↓
通过 connection_manager.get_device_connection(device_id) 查找设备连接
    ↓
转发消息到ConnectionHandler.handleTextMessage()
    ↓
设备连接处理消息(如触发聊天)
```

#### 设备连接 → Web客户端
```
设备连接产生消息(如LLM回复、STT、TTS等)
    ↓
ConnectionHandler / 其他处理器
    ↓
调用 server.forward_to_web_by_device_id(device_id, message)
    ↓
ConnectionManager.forward_to_web_by_device_id()
    ↓
转发到匹配device_id的所有Web客户端
```

### 4. 使用示例

#### 在ConnectionHandler中转发消息
```python
# 转发LLM回复到匹配的Web客户端
if hasattr(self.server, 'connection_manager'):
    asyncio.run_coroutine_threadsafe(
        self.server.forward_to_web_by_device_id(
            self.device_id,
            {
                "type": "llm",
                "text": content,
                "session_id": self.session_id,
                "device_id": self.device_id
            }
        ),
        self.loop
    )
```

#### 广播消息到所有Web客户端
```python
# 如果需要广播到所有Web客户端（不常用）
await server.broadcast_to_all_web({
    "type": "system",
    "message": "系统通知"
})
```

#### 转发消息到设备连接
```python
# 从Web端转发消息到设备连接
await server.forward_to_device_by_device_id(device_id, {
    "type": "command",
    "action": "restart"
})
```

## 优势

1. **统一管理**: 所有连接由 `ConnectionManager` 统一管理，职责清晰
2. **接口清晰**: 提供明确的消息转发接口，易于使用和理解
3. **按需转发**: 支持按 `device_id` 精确匹配转发，避免不必要的广播
4. **易于扩展**: 连接管理逻辑集中，便于后续扩展功能（如连接统计、监控等）
5. **代码简洁**: 移除了分散的连接管理代码，代码更清晰

## 消息转发策略

### 设备消息 → Web客户端
- **默认策略**: 使用 `forward_to_web_by_device_id()` 转发到匹配的Web客户端
- **原因**: 设备消息通常只与特定设备相关，不需要广播到所有Web客户端

### Web消息 → 设备连接
- **策略**: 通过 `connection_manager.get_device_connection()` 获取设备连接后直接转发
- **原因**: Web客户端连接时已指定device_id，直接匹配转发

### 系统消息
- **策略**: 使用 `broadcast_to_all_web()` 或 `broadcast_to_all_devices()` 广播
- **场景**: 系统通知、配置更新等需要所有客户端知道的消息

## 注意事项

1. **device_id匹配**: Web客户端连接时指定的`device_id`必须与要监听的设备连接的`device_id`一致
2. **多Web客户端**: 一个`device_id`可以对应多个Web客户端连接，消息会转发到所有匹配的客户端
3. **连接清理**: ConnectionManager会自动清理断开的连接
4. **线程安全**: 消息转发方法都是异步的，需要注意在同步代码中使用 `asyncio.run_coroutine_threadsafe()`

## 后续扩展建议

1. 支持Web客户端订阅多个设备连接
2. 实现消息过滤和路由规则
3. 添加连接状态监控和统计
4. 支持Web客户端的权限控制
5. 实现消息队列和重试机制

