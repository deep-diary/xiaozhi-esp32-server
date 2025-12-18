# Web连接重构架构说明

## 概述

本次重构将Web/Gradio客户端连接的处理逻辑从原有的分散实现中独立出来,创建了专门的连接管理类,实现了按`device_id`匹配转发的功能,同时保持向后兼容。

## 架构设计

### 1. 核心类

#### WebConnectionHandler (`core/web_connection.py`)
- **职责**: 专门处理Web/Gradio客户端连接
- **功能**:
  - 管理Web客户端的连接生命周期
  - 处理来自Web客户端的消息(如聊天消息、心跳等)
  - 将Web客户端的消息转发到对应的设备连接
  - 接收并转发设备连接的消息到Web客户端

#### WebSocketServer (`core/websocket_server.py`)
- **职责**: 统一管理所有连接(设备连接和Web连接)
- **连接管理**:
  - `device_connections`: `{device_id: ConnectionHandler}` - 设备连接字典
  - `web_connections`: `{device_id: set(WebConnectionHandler)}` - Web连接字典(一个device_id可对应多个Web客户端)
  - `gradio_clients`: `set()` - 保持向后兼容的广播集合

### 2. 消息流转

#### Web客户端 → 设备连接
```
Web客户端发送消息
    ↓
WebConnectionHandler._process_web_message()
    ↓
根据device_id查找对应的设备连接
    ↓
转发消息到ConnectionHandler.handleTextMessage()
    ↓
设备连接处理消息(如触发聊天)
```

#### 设备连接 → Web客户端
```
设备连接产生消息(如LLM回复)
    ↓
ConnectionHandler.chat() 等方法
    ↓
调用 server.broadcast_and_forward_to_device()
    ↓
WebSocketServer:
  1. broadcast_to_gradio() - 广播到所有Web客户端(向后兼容)
  2. forward_to_web_by_device_id() - 转发到匹配device_id的Web客户端
```

### 3. 关键方法

#### WebSocketServer新增方法

- `register_web_client(device_id, web_handler)`: 注册Web客户端连接
- `unregister_web_client(device_id, web_handler)`: 注销Web客户端连接
- `get_device_connection(device_id)`: 根据device_id获取设备连接
- `forward_to_web_by_device_id(device_id, message)`: 按device_id转发消息
- `broadcast_and_forward_to_device(device_id, message)`: 广播+按device_id转发

#### 向后兼容方法

- `broadcast_to_gradio(message)`: 保持原有功能,广播到所有Web客户端

## 使用方式

### Web客户端连接

Web客户端连接时需要指定`device-id`:

```javascript
// WebSocket连接示例
const ws = new WebSocket('ws://server:port/?device-id=your_device_id&client-id=gradio-client');
```

### 消息格式

#### Web客户端发送消息
```json
{
  "type": "hello",
  "content": "用户消息内容"
}
```

#### 服务器发送到Web客户端
```json
{
  "type": "llm",
  "text": "LLM回复内容",
  "session_id": "会话ID",
  "device_id": "设备ID"
}
```

## 优势

1. **职责分离**: Web连接和设备连接分别由独立的类管理
2. **按需转发**: 支持按`device_id`精确匹配转发,避免不必要的广播
3. **向后兼容**: 保持原有`broadcast_to_gradio`方法,不影响现有代码
4. **易于扩展**: Web连接处理逻辑集中,便于后续扩展功能
5. **代码清晰**: 连接管理逻辑集中在`WebSocketServer`,便于维护

## 注意事项

1. **device_id匹配**: Web客户端连接时指定的`device_id`必须与要监听的设备连接的`device_id`一致
2. **多Web客户端**: 一个`device_id`可以对应多个Web客户端连接,消息会转发到所有匹配的客户端
3. **向后兼容**: 原有的`broadcast_to_gradio`调用仍然有效,会广播到所有Web客户端

## 后续扩展建议

1. 支持Web客户端订阅多个设备连接
2. 实现消息过滤和路由规则
3. 添加连接状态监控和统计
4. 支持Web客户端的权限控制

