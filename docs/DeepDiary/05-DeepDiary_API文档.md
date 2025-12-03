# DeepDiary API 文档

## 一、WebSocket API

### 1.1 连接地址

```
ws://host:8000/xiaozhi/v1/
```

### 1.2 认证方式

**Header 认证：**

```
Authorization: Bearer {token}
Device-Id: {device_id}
Client-Id: {client_id}
```

### 1.3 消息格式

**所有消息均为 JSON 格式**

### 1.4 消息类型

#### 1.4.1 客户端 → 服务器

**hello 消息（初始化）**

```json
{
  "type": "hello",
  "content": "用户消息"
}
```

**iot 消息（设备控制）**

```json
{
  "type": "iot",
  "devices": ["客厅灯", "卧室灯"],
  "action": "打开",
  "value": null
}
```

**mcp 消息（MCP 工具调用）**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "tool_name",
      "arguments": {}
    }
  }
}
```

#### 1.4.2 服务器 → 客户端

**stt 消息（语音识别结果）**

```json
{
  "type": "stt",
  "text": "识别到的文本",
  "session_id": "session_id"
}
```

**llm 消息（LLM 回复）**

```json
{
  "type": "llm",
  "text": "AI回复内容",
  "session_id": "session_id"
}
```

**tts 消息（TTS 状态）**

```json
{
  "type": "tts",
  "state": "start|sentence_start|stop",
  "text": "当前句子文本（可选）",
  "session_id": "session_id"
}
```

**vision 消息（视觉识别结果）**

```json
{
  "type": "vision",
  "result": "识别结果文本",
  "people": ["张三", "李四"],
  "session_id": "session_id"
}
```

**memory_markdown 消息（记忆 Markdown）**

```json
{
  "type": "memory_markdown",
  "content": "# 相关记忆\n...",
  "session_id": "session_id"
}
```

**memory_images 消息（记忆图片）**

```json
{
  "type": "memory_images",
  "images": [
    "http://host/image1.jpg",
    "http://host/image2.jpg"
  ],
  "session_id": "session_id"
}
```

**resource_match 消息（资源匹配结果）**

```json
{
  "type": "resource_match",
  "matches": [
    {
      "resource_id": "resource_123",
      "resource_name": "Python开发技能",
      "match_score": 0.85,
      "match_reason": "技能匹配",
      "opportunity_type": "service",
      "estimated_value": 500
    }
  ],
  "session_id": "session_id"
}
```

## 二、HTTP API

### 2.1 视觉识别 API

**接口地址：** `POST /mcp/vision/explain`

**请求格式：** `multipart/form-data`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 图片文件 |
| question | string | 否 | 问题描述，默认"描述这张图片" |

**请求头：**

```
Authorization: Bearer {token}
Device-Id: {device_id}
Client-Id: {client_id}
```

**响应格式：**

```json
{
  "success": true,
  "action": "RESPONSE",
  "response": "识别结果文本"
}
```

**错误响应：**

```json
{
  "success": false,
  "message": "错误信息"
}
```

### 2.2 记忆检索 API

#### 2.2.1 时间线检索

**接口地址：** `GET /api/memory/timeline`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| start_date | string | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | 结束日期，格式：YYYY-MM-DD |
| limit | int | 否 | 返回数量，默认 20 |

**响应格式：**

```json
{
  "success": true,
  "data": [
    {
      "id": "memory_123",
      "type": "photo",
      "content": "记忆内容",
      "date": "2025-01-15",
      "people": ["张三"],
      "location": "哈尔滨",
      "images": ["url1", "url2"]
    }
  ]
}
```

#### 2.2.2 人物检索

**接口地址：** `GET /api/memory/person`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| person_id | string | 是 | 人物ID |
| limit | int | 否 | 返回数量，默认 20 |

**响应格式：** 同时间线检索

#### 2.2.3 地点检索

**接口地址：** `GET /api/memory/location`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| location | string | 是 | 地点名称 |
| limit | int | 否 | 返回数量，默认 20 |

**响应格式：** 同时间线检索

### 2.3 资源追溯 API

#### 2.3.1 注册资源

**接口地址：** `POST /api/resource/register`

**请求格式：** `application/json`

**请求体：**

```json
{
  "person_id": "person_123",
  "resource_type": "skill",
  "name": "Python开发",
  "description": "5年Python开发经验",
  "tags": ["Python", "后端开发", "Web开发"],
  "availability": "available"
}
```

**响应格式：**

```json
{
  "success": true,
  "resource_id": "resource_123"
}
```

#### 2.3.2 注册需求

**接口地址：** `POST /api/demand/register`

**请求格式：** `application/json`

**请求体：**

```json
{
  "person_id": "person_123",
  "demand_type": "learning",
  "name": "学习Python",
  "description": "想学习Python编程",
  "tags": ["Python", "编程", "学习"],
  "priority": 4
}
```

**响应格式：**

```json
{
  "success": true,
  "demand_id": "demand_123"
}
```

#### 2.3.3 匹配资源

**接口地址：** `GET /api/resource/match`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| demand_id | string | 是 | 需求ID |
| top_k | int | 否 | 返回数量，默认 5 |

**响应格式：**

```json
{
  "success": true,
  "matches": [
    {
      "resource_id": "resource_123",
      "resource_name": "Python开发技能",
      "match_score": 0.85,
      "match_reason": "技能高度匹配",
      "opportunity_type": "service",
      "estimated_value": 500
    }
  ]
}
```

#### 2.3.4 匹配需求

**接口地址：** `GET /api/demand/match`

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| resource_id | string | 是 | 资源ID |
| top_k | int | 否 | 返回数量，默认 5 |

**响应格式：** 同匹配资源

## 三、错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 四、示例代码

### 4.1 WebSocket 客户端示例

```python
import websockets
import json

async def connect_websocket():
    uri = "ws://localhost:8000/xiaozhi/v1/"
    headers = {
        "Authorization": "Bearer your_token",
        "Device-Id": "device_123",
        "Client-Id": "client_123"
    }
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # 发送消息
        message = {
            "type": "hello",
            "content": "你好"
        }
        await websocket.send(json.dumps(message))
        
        # 接收消息
        response = await websocket.recv()
        data = json.loads(response)
        print(data)
```

### 4.2 HTTP API 调用示例

```python
import requests

# 视觉识别
files = {"file": open("image.jpg", "rb")}
data = {"question": "描述这张图片"}
headers = {
    "Authorization": "Bearer your_token",
    "Device-Id": "device_123",
    "Client-Id": "client_123"
}

response = requests.post(
    "http://localhost:8003/mcp/vision/explain",
    files=files,
    data=data,
    headers=headers
)
print(response.json())

# 记忆检索
response = requests.get(
    "http://localhost:8000/api/memory/person",
    params={"person_id": "person_123", "limit": 10},
    headers=headers
)
print(response.json())
```

