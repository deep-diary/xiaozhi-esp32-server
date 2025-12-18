# Gradio Web 客户端通讯协议文档

## 一、概述

本文档详细说明了 xiaozhi-server 与 Gradio Web 客户端之间的 WebSocket 通讯协议，包括消息类型、消息格式、使用场景和最佳实践。

## 二、连接建立

### 2.1 WebSocket 连接地址

```
ws://host:port/?device-id={device_id}&client-id=gradio-client
```

**参数说明：**

- `device-id`: 设备 ID，用于匹配对应的设备连接，Web 客户端将接收该设备的所有消息
- `client-id`: 固定为 `gradio-client`，用于标识客户端类型

**示例：**

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/?device-id=esp32-device-001&client-id=gradio-client"
);
```

### 2.2 认证（可选）

如果服务器启用了认证功能，需要在连接时提供认证 token：

```
ws://host:port/?device-id={device_id}&client-id=gradio-client&authorization=Bearer {token}
```

或者在请求头中提供：

```
Authorization: Bearer {token}
```

## 三、消息类型汇总

### 3.1 消息类型分类

根据消息方向，分为两大类：

#### 3.1.1 Web 客户端 → 服务器

| 消息类型 | 说明     | 使用场景                   |
| -------- | -------- | -------------------------- |
| `hello`  | 聊天消息 | 用户发送文本消息进行对话   |
| `ping`   | 心跳消息 | 保持连接活跃，检测连接状态 |

#### 3.1.2 服务器 → Web 客户端

| 消息类型                | 说明                   | 使用场景                                                                |
| ----------------------- | ---------------------- | ----------------------------------------------------------------------- |
| `stt`                   | 语音识别结果           | 用户说话内容识别结果                                                    |
| `llm`                   | LLM 完整回复           | AI 的完整回复内容                                                       |
| `llm_sentence`          | LLM 句子片段           | 流式输出时的句子片段                                                    |
| `tts`                   | TTS 状态               | TTS 播放状态（开始/句子开始/结束）                                      |
| `voiceprint_identified` | 声纹识别结果（已废弃） | 识别到的说话人信息（已废弃，声纹识别后直接发送 `immich_search_result`） |
| `vision`                | 视觉识别结果           | 图片识别结果，包含人物信息                                              |
| `immich_search_result`  | Immich 搜索结果        | Immich 照片检索结果（声纹识别后自动触发）                               |
| `pong`                  | 心跳响应               | 响应 ping 消息                                                          |
| `memory_markdown`       | 记忆 Markdown 内容     | 记忆检索结果的 Markdown 格式展示                                        |
| `memory_images`         | 记忆图片列表           | 记忆相关的图片 URL 列表                                                 |
| `resource_match`        | 资源匹配结果           | 资源追溯匹配结果                                                        |

## 四、消息格式详解

### 4.1 Web 客户端 → 服务器

#### 4.1.1 聊天消息 (`hello`)

**消息格式：**

```json
{
  "type": "hello",
  "content": "用户消息内容"
}
```

**字段说明：**

- `type`: 固定为 `"hello"`
- `content`: 用户输入的文本消息

**使用示例：**

```javascript
ws.send(
  JSON.stringify({
    type: "hello",
    content: "你好，我想看照片",
  })
);
```

**处理流程：**

1. Web 客户端发送消息到服务器
2. 服务器通过 `WebConnectionHandler` 接收消息
3. 消息被转发到对应的设备连接（`ConnectionHandler`）
4. 设备连接处理消息，触发聊天流程

#### 4.1.2 心跳消息 (`ping`)

**消息格式：**

```json
{
  "type": "ping"
}
```

**字段说明：**

- `type`: 固定为 `"ping"`

**使用示例：**

```javascript
// 定期发送心跳，保持连接活跃
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000); // 每30秒发送一次
```

**响应：**
服务器会返回 `pong` 消息作为响应。

### 4.2 服务器 → Web 客户端

#### 4.2.1 语音识别结果 (`stt`)

**消息格式：**

```json
{
  "type": "stt",
  "text": "用户说的话",
  "session_id": "会话ID",
  "speaker": "说话人名称（可选）"
}
```

**字段说明：**

- `type`: 固定为 `"stt"`
- `text`: 识别到的用户说话内容（已去除标点符号和表情）
- `session_id`: 会话 ID，用于关联同一轮对话
- `speaker`: 说话人名称（可选），如果识别到说话人信息会包含此字段

**使用场景：**

- 显示用户输入的消息
- 更新聊天记录

**示例：**

```json
{
  "type": "stt",
  "text": "我想看照片",
  "session_id": "abc123",
  "speaker": "张三"
}
```

#### 4.2.2 LLM 完整回复 (`llm`)

**消息格式：**

```json
{
  "type": "llm",
  "text": "AI的完整回复内容",
  "session_id": "会话ID",
  "device_id": "设备ID"
}
```

**字段说明：**

- `type`: 固定为 `"llm"`
- `text`: AI 的完整回复内容
- `session_id`: 会话 ID
- `device_id`: 设备 ID

**使用场景：**

- 显示 AI 的完整回复
- 工具调用结果的回复

**示例：**

```json
{
  "type": "llm",
  "text": "好的，我来帮你查找照片。",
  "session_id": "abc123",
  "device_id": "esp32-device-001"
}
```

**触发时机：**

- LLM 生成完整回复时
- 工具调用完成后返回结果时

#### 4.2.3 LLM 句子片段 (`llm_sentence`)

**消息格式：**

```json
{
  "type": "llm_sentence",
  "text": "句子片段内容",
  "session_id": "会话ID",
  "device_id": "设备ID"
}
```

**字段说明：**

- `type`: 固定为 `"llm_sentence"`
- `text`: 单个完整的句子片段
- `session_id`: 会话 ID
- `device_id`: 设备 ID

**使用场景：**

- 流式输出时显示句子片段
- 实时更新聊天界面

**示例：**

```json
{
  "type": "llm_sentence",
  "text": "我找到了几张照片，",
  "session_id": "abc123",
  "device_id": "esp32-device-001"
}
```

**注意：**

- 这是流式输出时的中间消息，最终会通过 `llm` 类型发送完整回复
- 客户端可以选择累积这些片段，或者单独显示每个句子

#### 4.2.4 TTS 状态 (`tts`)

**消息格式：**

```json
{
  "type": "tts",
  "state": "start|sentence_start|stop",
  "session_id": "会话ID",
  "text": "文本内容（可选，仅在sentence_start时存在）"
}
```

**字段说明：**

- `type`: 固定为 `"tts"`
- `state`: TTS 状态
  - `start`: TTS 开始播放
  - `sentence_start`: 开始播放某个句子（包含 text 字段）
  - `stop`: TTS 播放结束
- `session_id`: 会话 ID
- `text`: 句子文本（仅在 `sentence_start` 状态时存在）

**使用场景：**

- 显示 TTS 播放状态
- 高亮正在播放的句子

**示例：**

```json
// TTS开始
{
  "type": "tts",
  "state": "start",
  "session_id": "abc123"
}

// 开始播放某个句子
{
  "type": "tts",
  "state": "sentence_start",
  "text": "我找到了几张照片，",
  "session_id": "abc123"
}

// TTS结束
{
  "type": "tts",
  "state": "stop",
  "session_id": "abc123"
}
```

#### 4.2.5 视觉识别结果 (`vision`)

**消息格式：**

```json
{
  "type": "vision",
  "result": "图片识别结果文本",
  "people": ["张三", "李四"],
  "people_ids": ["person-id-1", "person-id-2"],
  "session_id": "会话ID",
  "device_id": "设备ID",
  "asset_id": "Immich资产ID（可选）",
  "image_url": "图片URL（可选）",
  "image": "base64图片数据（可选，降级方案）"
}
```

**字段说明：**

- `type`: 固定为 `"vision"`
- `result`: VLLM 识别的图片内容描述
- `people`: 识别到的人物名称列表
- `people_ids`: 识别到的人物 ID 列表（Immich）
- `session_id`: 会话 ID（通常使用 device_id）
- `device_id`: 设备 ID
- `asset_id`: Immich 资产 ID（如果图片已上传到 Immich）
- `image_url`: Immich 图片 URL（优先使用）
- `image`: base64 编码的图片数据（降级方案，当没有 asset_id 时使用）

**使用场景：**

- 显示图片识别结果
- 展示识别到的人物信息
- 显示识别的图片

**示例：**

```json
{
  "type": "vision",
  "result": "这是一张在公园拍摄的照片，照片中有两个人正在聊天。",
  "people": ["张三", "李四"],
  "people_ids": ["person-123", "person-456"],
  "session_id": "esp32-device-001",
  "device_id": "esp32-device-001",
  "asset_id": "asset-789",
  "image_url": "http://localhost:2283/photos/asset-789"
}
```

**触发时机：**

- ESP32 设备上传图片时
- 通过 HTTP API 上传图片到 vision_handler 时

#### 4.2.7 Immich 搜索结果 (`immich_search_result`)

**消息格式：**

```json
{
  "type": "immich_search_result",
  "data": {
    "assets": [
      {
        "id": "asset-id-1",
        "url": "http://immich/photos/asset-id-1",
        "thumbnailUrl": "http://immich/thumbs/asset-id-1",
        "createdAt": "2024-01-01T00:00:00Z",
        "exifInfo": {
          "city": "北京",
          "dateTimeOriginal": "2024-01-01T00:00:00Z"
        }
      }
    ],
    "count": 10,
    "query": "查询关键词",
    "person_name": "张三",
    "city": "北京",
    "date": "2024-01-01",
    "device_id": "esp32-device-001"
  },
  "device_id": "esp32-device-001"
}
```

**字段说明：**

- `type`: 固定为 `"immich_search_result"`
- `data`: 搜索结果数据
  - `assets`: 资产列表，每个资产包含：
    - `id`: 资产 ID
    - `url`: 图片 URL
    - `thumbnailUrl`: 缩略图 URL
    - `createdAt`: 创建时间
    - `exifInfo`: EXIF 信息（包含城市、拍摄时间等）
  - `count`: 结果数量
  - `query`: 查询关键词
  - `person_name`: 查询的人物名称
  - `city`: 查询的城市
  - `date`: 查询的日期
  - `device_id`: 设备 ID
- `device_id`: 设备 ID

**使用场景：**

- 显示照片搜索结果
- 展示照片网格
- 更新记忆显示区

**示例：**

```json
{
  "type": "immich_search_result",
  "data": {
    "assets": [
      {
        "id": "asset-123",
        "url": "http://localhost:2283/photos/asset-123",
        "thumbnailUrl": "http://localhost:2283/thumbs/asset-123",
        "createdAt": "2024-01-01T00:00:00Z",
        "exifInfo": {
          "city": "北京",
          "dateTimeOriginal": "2024-01-01T00:00:00Z"
        }
      }
    ],
    "count": 1,
    "query": "photo",
    "person_name": "张三",
    "city": null,
    "date": null,
    "device_id": "esp32-device-001"
  },
  "device_id": "esp32-device-001"
}
```

**触发时机：**

- 调用 Immich 搜索功能时（通过 MCP 工具调用）
- **声纹识别后自动触发**：当声纹识别到有效说话人时，服务端会异步搜索该人物的照片并发送此消息

**注意：**

- 声纹识别触发的搜索消息中，`query` 字段为 `"voiceprint_triggered"`，用于标识这是声纹触发的搜索
- 由于 Immich 图片 URL 不是公开的，声纹识别触发的消息中的 `assets` 只包含 `id`（asset_id）和基本信息（type、createdAt、localDateTime、originalFileName、exifInfo、isFavorite），不包含 `url` 和 `thumbnailUrl`
- 前端需要通过 asset_id 构建访问 URL，或通过服务端代理访问图片
- 照片数量可通过配置项 `Immich.voiceprint_photo_count` 控制（默认 10 张）

#### 4.2.8 心跳响应 (`pong`)

**消息格式：**

```json
{
  "type": "pong"
}
```

**字段说明：**

- `type`: 固定为 `"pong"`

**使用场景：**

- 响应客户端的 ping 消息
- 确认连接正常

**示例：**

```json
{
  "type": "pong"
}
```

#### 4.2.9 记忆 Markdown 内容 (`memory_markdown`)

**消息格式：**

```json
{
  "type": "memory_markdown",
  "content": "# 相关记忆\n\n## 相关照片\n...",
  "session_id": "会话ID"
}
```

**字段说明：**

- `type`: 固定为 `"memory_markdown"`
- `content`: Markdown 格式的记忆内容
- `session_id`: 会话 ID

**使用场景：**

- 在 Markdown 显示区展示记忆内容
- 动态更新记忆展示

**示例：**

```json
{
  "type": "memory_markdown",
  "content": "# 📸 相关记忆\n\n## 相关照片\n![照片](http://immich/photos/asset-123)\n\n## 记忆片段\n- **2024-01-01**: 与张三一起去了北京\n\n## 相关知识\n- 北京是中国的首都",
  "session_id": "abc123"
}
```

**注意：**

- 此消息类型在文档中定义，但可能尚未完全实现
- 需要记忆检索服务支持

#### 4.2.10 记忆图片列表 (`memory_images`)

**消息格式：**

```json
{
  "type": "memory_images",
  "images": ["http://immich/photos/asset-1", "http://immich/photos/asset-2"],
  "session_id": "会话ID"
}
```

**字段说明：**

- `type`: 固定为 `"memory_images"`
- `images`: 图片 URL 列表
- `session_id`: 会话 ID

**使用场景：**

- 批量展示记忆相关的图片
- 更新图片网格

**示例：**

```json
{
  "type": "memory_images",
  "images": [
    "http://localhost:2283/photos/asset-123",
    "http://localhost:2283/photos/asset-456"
  ],
  "session_id": "abc123"
}
```

**注意：**

- 此消息类型在文档中定义，但可能尚未完全实现
- 需要记忆检索服务支持

#### 4.2.11 资源匹配结果 (`resource_match`)

**消息格式：**

```json
{
  "type": "resource_match",
  "matches": {
    "resource_to_demand": [
      {
        "resource_id": "resource-1",
        "demand_id": "demand-1",
        "match_score": 0.95,
        "match_reason": "技能匹配",
        "opportunity_type": "service",
        "estimated_value": 1000.0
      }
    ],
    "demand_to_resource": [
      {
        "resource_id": "resource-2",
        "demand_id": "demand-2",
        "match_score": 0.88,
        "match_reason": "需求匹配",
        "opportunity_type": "cooperation",
        "estimated_value": 500.0
      }
    ]
  },
  "session_id": "会话ID"
}
```

**字段说明：**

- `type`: 固定为 `"resource_match"`
- `matches`: 匹配结果
  - `resource_to_demand`: 根据资源匹配的需求列表
  - `demand_to_resource`: 根据需求匹配的资源列表
- `session_id`: 会话 ID

**使用场景：**

- 显示资源匹配结果
- 展示推荐的服务机会

**注意：**

- 此消息类型在文档中定义，但可能尚未完全实现
- 需要资源追溯服务支持

## 五、消息流转机制

### 5.1 消息转发策略

xiaozhi-server 支持两种消息转发策略：

#### 5.1.1 按 device_id 精确转发（推荐）

**方法：** `forward_to_web_by_device_id(device_id, message)`

**说明：**

- 只转发消息到匹配指定 `device_id` 的 Web 客户端
- 一个 `device_id` 可以对应多个 Web 客户端连接
- 消息会发送到所有匹配的 Web 客户端

**使用场景：**

- 设备连接产生的消息（stt、llm、tts 等）
- 视觉识别结果
- Immich 搜索结果

**优势：**

- 精确匹配，避免不必要的广播
- 支持多 Web 客户端监听同一设备
- 性能更好

#### 5.1.2 广播到所有 Web 客户端（向后兼容）

**方法：** `broadcast_to_all_web(message)`

**说明：**

- 广播消息到所有 Web 客户端
- 不考虑 device_id 匹配

**使用场景：**

- 系统通知
- 全局消息

**注意：**

- 此方法主要用于向后兼容
- 新功能建议使用精确转发

### 5.2 消息流转示例

#### 5.2.1 聊天消息流程

```
用户输入文本
    ↓
Web客户端发送: {"type": "hello", "content": "用户消息"}
    ↓
WebConnectionHandler接收消息
    ↓
转发到设备连接: ConnectionHandler.handleTextMessage()
    ↓
触发聊天流程: ConnectionHandler.chat()
    ↓
发送STT消息: {"type": "stt", "text": "用户消息"}
    ↓
LLM处理，生成回复
    ↓
发送LLM消息: {"type": "llm", "text": "AI回复"}
    ↓
Web客户端接收并显示
```

#### 5.2.2 图片识别流程

```
ESP32设备上传图片
    ↓
HTTP POST到vision_handler
    ↓
调用VLLM识别图片
    ↓
调用Immich识别人脸
    ↓
发送vision消息: {"type": "vision", "result": "...", "people": [...]}
    ↓
Web客户端接收并显示
```

## 六、最佳实践

### 6.1 连接管理

1. **连接建立**

   - 确保在连接时提供正确的 `device-id`
   - 如果启用认证，提供有效的 token
   - 处理连接失败的情况

2. **连接保持**

   - 定期发送 `ping` 消息保持连接活跃
   - 监听 `pong` 响应确认连接正常
   - 处理连接断开和重连

3. **错误处理**
   - 捕获 WebSocket 错误
   - 实现重连机制
   - 记录错误日志

### 6.2 消息处理

1. **消息解析**

   - 验证消息格式
   - 检查必需字段
   - 处理可选字段

2. **消息显示**

   - 根据消息类型选择不同的显示方式
   - 累积流式消息（llm_sentence）
   - 更新 UI 状态（TTS 状态）

3. **消息关联**
   - 使用 `session_id` 关联同一轮对话的消息
   - 使用 `device_id` 区分不同设备的消息

### 6.3 性能优化

1. **消息去重**

   - 避免重复显示相同的消息
   - 使用消息 ID 或时间戳去重

2. **批量更新**

   - 对于大量消息（如照片列表），使用批量更新
   - 避免频繁的 DOM 操作

3. **图片加载**
   - 使用缩略图 URL 优先加载
   - 实现图片懒加载
   - 缓存已加载的图片

## 七、消息类型枚举建议

### 7.1 问题分析

当前代码中消息类型以字符串形式硬编码在各个地方，存在以下问题：

1. **类型不一致**：容易出现拼写错误
2. **难以维护**：新增消息类型需要修改多处代码
3. **缺少文档**：没有统一的类型定义和说明
4. **难以重构**：字符串类型不利于 IDE 自动补全和重构

### 7.2 实现方案

已创建消息类型枚举类和相关工具类，统一管理所有消息类型：

**文件位置：** `core/protocol/message_types.py`

```python
from enum import Enum

class WebMessageType(str, Enum):
    """WebSocket消息类型枚举"""

    # Web客户端 → 服务器
    HELLO = "hello"
    PING = "ping"

    # 服务器 → Web客户端
    STT = "stt"
    LLM = "llm"
    LLM_SENTENCE = "llm_sentence"
    TTS = "tts"
    VOICEPRINT_IDENTIFIED = "voiceprint_identified"
    VISION = "vision"
    IMMICH_SEARCH_RESULT = "immich_search_result"
    PONG = "pong"
    MEMORY_MARKDOWN = "memory_markdown"
    MEMORY_IMAGES = "memory_images"
    RESOURCE_MATCH = "resource_match"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """检查消息类型是否有效"""
        return value in [item.value for item in cls]

    @classmethod
    def get_all_types(cls) -> list[str]:
        """获取所有消息类型列表"""
        return [item.value for item in cls]

    @classmethod
    def get_client_to_server_types(cls) -> list[str]:
        """获取客户端到服务器的消息类型列表"""
        return [cls.HELLO.value, cls.PING.value]

    @classmethod
    def get_server_to_client_types(cls) -> list[str]:
        """获取服务器到客户端的消息类型列表"""
        return [
            cls.STT.value,
            cls.LLM.value,
            cls.LLM_SENTENCE.value,
            cls.TTS.value,
            cls.VOICEPRINT_IDENTIFIED.value,
            cls.VISION.value,
            cls.IMMICH_SEARCH_RESULT.value,
            cls.MEMORY_MARKDOWN.value,
            cls.MEMORY_IMAGES.value,
            cls.RESOURCE_MATCH.value,
            cls.PONG.value,
        ]
```

### 7.3 使用示例

#### 7.3.1 使用枚举类

**修改前：**

```python
message = {
    "type": "llm",
    "text": "AI回复",
    "session_id": session_id,
    "device_id": device_id
}
```

**修改后：**

```python
from core.protocol.message_types import WebMessageType

message = {
    "type": WebMessageType.LLM.value,
    "text": "AI回复",
    "session_id": session_id,
    "device_id": device_id
}
```

#### 7.3.2 使用消息构建器（推荐）

**使用消息构建器，更简洁且类型安全：**

```python
from core.protocol.message_builder import WebMessageBuilder

# 构建LLM消息
message = WebMessageBuilder.build_llm_message(
    text="AI回复",
    session_id=session_id,
    device_id=device_id
)

# 构建STT消息
message = WebMessageBuilder.build_stt_message(
    text="用户说的话",
    session_id=session_id,
    speaker="张三"  # 可选
)

# 构建视觉识别消息
message = WebMessageBuilder.build_vision_message(
    result="图片识别结果",
    people=["张三", "李四"],
    people_ids=["person-1", "person-2"],
    session_id=session_id,
    device_id=device_id,
    asset_id="asset-123",
    image_url="http://immich/photos/asset-123"
)
```

#### 7.3.3 使用消息验证器

```python
from core.protocol.message_validator import WebMessageValidator

message = {
    "type": "llm",
    "text": "AI回复",
    "session_id": "abc123",
    "device_id": "esp32-001"
}

is_valid, error = WebMessageValidator.validate(message)
if not is_valid:
    print(f"消息验证失败: {error}")
else:
    # 发送消息
    await websocket.send(json.dumps(message))
```

### 7.4 重构收益

1. **类型安全**：使用枚举避免拼写错误
2. **易于维护**：集中管理消息类型
3. **IDE 支持**：自动补全和类型检查
4. **文档化**：枚举类本身就是文档
5. **易于扩展**：新增类型只需在枚举中添加

## 八、代码架构优化建议

### 8.1 已实现的工具类

#### 8.1.1 消息类型枚举类

**文件：** `core/protocol/message_types.py`

已实现 `WebMessageType` 枚举类，包含所有消息类型定义。

#### 8.1.2 消息构建器

**文件：** `core/protocol/message_builder.py`

已实现 `WebMessageBuilder` 类，提供所有消息类型的构建方法：

- `build_hello_message()` - 构建 hello 消息
- `build_ping_message()` - 构建 ping 消息
- `build_stt_message()` - 构建 STT 消息
- `build_llm_message()` - 构建 LLM 消息
- `build_llm_sentence_message()` - 构建 LLM 句子片段消息
- `build_tts_message()` - 构建 TTS 消息
- `build_voiceprint_identified_message()` - 构建声纹识别消息
- `build_vision_message()` - 构建视觉识别消息
- `build_immich_search_result_message()` - 构建 Immich 搜索结果消息
- `build_pong_message()` - 构建 pong 消息
- `build_memory_markdown_message()` - 构建记忆 Markdown 消息
- `build_memory_images_message()` - 构建记忆图片列表消息
- `build_resource_match_message()` - 构建资源匹配结果消息

#### 8.1.3 消息验证器

**文件：** `core/protocol/message_validator.py`

已实现 `WebMessageValidator` 类，提供消息格式验证功能：

- `validate()` - 验证消息格式的完整性和正确性
- `validate_required_fields()` - 验证必需字段

### 8.2 迁移指南

#### 8.2.1 逐步迁移策略

1. **第一阶段：新代码使用新工具类**

   - 所有新代码使用 `WebMessageBuilder` 构建消息
   - 使用 `WebMessageType` 枚举类

2. **第二阶段：重构现有代码**

   - 逐步将现有代码中的消息构建改为使用 `WebMessageBuilder`
   - 将字符串类型的消息类型改为使用 `WebMessageType`

3. **第三阶段：添加验证**
   - 在关键位置添加消息验证
   - 确保所有消息都符合协议规范

#### 8.2.2 重构示例

**重构前：**

```python
# sendAudioHandle.py
message = {
    "type": "llm",
    "text": content,
    "session_id": self.session_id,
    "device_id": self.device_id
}
```

**重构后：**

```python
# sendAudioHandle.py
from core.protocol.message_builder import WebMessageBuilder

message = WebMessageBuilder.build_llm_message(
    text=content,
    session_id=self.session_id,
    device_id=self.device_id
)
```

### 8.3 未来扩展建议

#### 8.3.1 消息处理器模式

可以考虑实现消息处理器模式，统一处理消息：

```python
# core/protocol/message_handler.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class MessageHandler(ABC):
    """消息处理器接口"""

    @abstractmethod
    async def handle(self, message: Dict[str, Any]) -> None:
        """处理消息"""
        pass

class STTMessageHandler(MessageHandler):
    """STT消息处理器"""

    async def handle(self, message: Dict[str, Any]) -> None:
        # 处理STT消息
        text = message.get("text")
        speaker = message.get("speaker")
        # ... 处理逻辑

class LLMMessageHandler(MessageHandler):
    """LLM消息处理器"""

    async def handle(self, message: Dict[str, Any]) -> None:
        # 处理LLM消息
        text = message.get("text")
        # ... 处理逻辑
```

#### 8.3.2 消息版本管理

可以考虑添加消息版本管理，支持协议升级：

```python
# core/protocol/message_version.py
class MessageVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"

class VersionedMessageBuilder:
    """支持版本的消息构建器"""

    @staticmethod
    def build_llm_message_v1(...):
        """构建V1版本的LLM消息"""
        pass

    @staticmethod
    def build_llm_message_v2(...):
        """构建V2版本的LLM消息"""
        pass
```

## 九、总结

### 9.1 当前状态

- ✅ WebSocket 连接机制已实现
- ✅ 按 device_id 精确转发已实现
- ✅ 主要消息类型已实现（stt、llm、tts、vision 等）
- ✅ 消息类型枚举类已创建（`WebMessageType`）
- ✅ 消息构建器已实现（`WebMessageBuilder`）
- ✅ 消息验证器已实现（`WebMessageValidator`）
- ⚠️ 现有代码尚未完全迁移到新工具类
- ⚠️ 部分消息类型（memory_markdown 等）尚未完全实现

### 9.2 优化建议

1. **短期优化（已完成）**

   - ✅ 创建消息类型枚举类
   - ✅ 统一消息构建方式
   - ✅ 添加消息验证

2. **中期优化（进行中）**

   - ⏳ 逐步迁移现有代码到新工具类
   - ⏳ 完善记忆检索相关消息类型
   - ⏳ 添加消息统计和监控

3. **长期优化（计划中）**
   - 📋 实现消息处理器模式
   - 📋 实现消息版本管理
   - 📋 支持消息压缩和加密
   - 📋 实现消息队列和重试机制

### 9.3 参考实现

可以参考以下文件了解当前实现：

**核心文件：**

- `core/websocket_server.py` - WebSocket 服务器
- `core/web_connection.py` - Web 连接处理器
- `core/connection_manager.py` - 连接管理器
- `core/handle/sendAudioHandle.py` - 消息发送处理
- `core/api/vision_handler.py` - 视觉识别处理

**协议相关文件（新增）：**

- `core/protocol/message_types.py` - 消息类型枚举
- `core/protocol/message_builder.py` - 消息构建器
- `core/protocol/message_validator.py` - 消息验证器

## 十、附录

### 10.1 消息类型快速参考

| 类型                    | 方向 | 必需字段                                                | 可选字段                                               |
| ----------------------- | ---- | ------------------------------------------------------- | ------------------------------------------------------ |
| `hello`                 | C→S  | type, content                                           | -                                                      |
| `ping`                  | C→S  | type                                                    | -                                                      |
| `stt`                   | S→C  | type, text, session_id                                  | speaker                                                |
| `llm`                   | S→C  | type, text, session_id, device_id                       | -                                                      |
| `llm_sentence`          | S→C  | type, text, session_id, device_id                       | -                                                      |
| `tts`                   | S→C  | type, state, session_id                                 | text                                                   |
| `voiceprint_identified` | S→C  | type, data（已废弃）                                    | -（已废弃，声纹识别后直接发送 `immich_search_result`） |
| `vision`                | S→C  | type, result, people, people_ids, session_id, device_id | asset_id, image_url, image                             |
| `immich_search_result`  | S→C  | type, data, device_id                                   | -                                                      |
| `pong`                  | S→C  | type                                                    | -                                                      |
| `memory_markdown`       | S→C  | type, content, session_id                               | -                                                      |
| `memory_images`         | S→C  | type, images, session_id                                | -                                                      |
| `resource_match`        | S→C  | type, matches, session_id                               | -                                                      |

**说明：**

- C→S: Web 客户端 → 服务器
- S→C: 服务器 → Web 客户端

### 10.2 常见问题

**Q: 如何区分不同设备的消息？**

A: 使用 `device_id` 字段。Web 客户端连接时指定 `device-id`，服务器只会转发匹配的消息。

**Q: 如何处理流式输出？**

A: 使用 `llm_sentence` 类型接收句子片段，累积后显示完整回复。最终会收到 `llm` 类型的完整消息。

**Q: 如何保持连接活跃？**

A: 定期发送 `ping` 消息，服务器会返回 `pong` 响应。

**Q: 消息顺序如何保证？**

A: WebSocket 保证消息顺序，但建议使用 `session_id` 关联同一轮对话的消息。

**Q: 如何处理连接断开？**

A: 监听 WebSocket 的 `close` 事件，实现重连机制。建议使用指数退避策略。
