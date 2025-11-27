# 小智系统通讯架构详解

本文档详细说明小智设备、服务器、MCP接入点、MQTT网关之间的通讯架构和消息传递机制。

## 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        小智系统通讯架构                               │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  小智设备     │  ESP32硬件设备
│ (ESP32)      │  支持WebSocket或MQTT+UDP连接
└──────┬───────┘
       │
       │ 方式1: 直接WebSocket连接
       │ 方式2: MQTT+UDP (通过MQTT网关)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MQTT网关 (可选)                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 功能: 协议转换层                                           │  │
│  │ - MQTT (1883端口) ←→ WebSocket                             │  │
│  │ - UDP (8884端口) ←→ WebSocket                              │  │
│  │ - 管理API (8007端口)                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ WebSocket (带?from=mqtt_gateway标识)
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  xiaozhi-server (核心服务器)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 核心功能:                                                   │  │
│  │ - WebSocket服务器 (8000端口)                               │  │
│  │ - OTA接口 (8002端口)                                       │  │
│  │ - 语音识别 (ASR)                                           │  │
│  │ - 大语言模型 (LLM)                                         │  │
│  │ - 语音合成 (TTS)                                           │  │
│  │ - 工具调用管理                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            │                                       │
│                            │ WebSocket (MCP协议)                   │
│                            ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              MCP接入点 (可选)                                │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ 功能: 扩展工具能力                                    │  │  │
│  │  │ - 连接外部MCP服务器                                   │  │  │
│  │  │ - 提供工具列表                                        │  │  │
│  │  │ - 执行工具调用                                        │  │  │
│  │  │ - 管理API (8004端口)                                  │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP API
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   智控台 (Manager API)                             │
│  - 设备管理                                                        │
│  - 参数配置                                                        │
│  - 用户管理                                                        │
└──────────────────────────────────────────────────────────────────┘
```

## 二、组件详细说明

### 2.1 小智设备 (ESP32)

**连接方式：**
- **方式1：直接WebSocket连接**
  - 协议：WebSocket (ws://)
  - 端口：8000
  - 路径：`/xiaozhi/v1/`
  - 用途：实时双向通信，支持音频流和文本消息

- **方式2：MQTT+UDP连接（通过MQTT网关）**
  - MQTT协议：TCP 1883端口
  - UDP协议：UDP 8884端口
  - 用途：适用于网络环境受限的场景，通过MQTT网关转换为WebSocket

**发送的消息类型：**
- 音频数据：Opus编码的二进制音频流
- 文本消息：JSON格式的控制消息
  - `hello`: 问候消息，初始化连接
  - `listen`: 切换监听模式
  - `iot`: IoT设备控制消息
  - `mcp`: MCP工具调用消息（设备端MCP）
  - `server`: 服务器控制消息
  - `abort`: 中断当前操作

**接收的消息类型：**
- 音频数据：TTS生成的Opus编码音频流
- 文本消息：JSON格式的状态消息
  - `tts`: TTS状态消息（start/sentence_start/stop）
  - `stt`: 语音识别结果消息

### 2.2 MQTT网关 (xiaozhi-mqtt-gateway)

**作用：**
MQTT网关是一个协议转换层，将MQTT/UDP协议转换为WebSocket协议，使得ESP32设备可以通过MQTT协议连接到xiaozhi-server。

**核心功能：**
1. **协议转换**
   - 接收设备的MQTT消息，转换为WebSocket消息发送给xiaozhi-server
   - 接收xiaozhi-server的WebSocket消息，转换为MQTT消息发送给设备
   - UDP音频流与WebSocket二进制消息的转换

2. **音频包处理**
   - 设备→服务器：接收带16字节头部的音频包，解析后转发
   - 服务器→设备：为音频包添加16字节头部（包含timestamp、sequence等信息）

3. **连接管理**
   - 管理多个设备的MQTT连接
   - 维护设备与WebSocket连接的映射关系

**端口说明：**
- **1883端口 (TCP)**: MQTT协议端口，设备通过此端口连接
- **8884端口 (UDP)**: UDP协议端口，用于音频流传输
- **8007端口 (TCP)**: 管理API端口，智控台通过此端口管理设备

**消息格式：**

**音频包头部格式（16字节）：**
```
字节0:     type (1=音频)
字节1:     保留
字节2-3:   payload length (2字节，大端序)
字节4-7:   sequence (4字节，大端序)
字节8-11:  timestamp (4字节，大端序)
字节12-15: opus length (4字节，大端序)
```

**配置下发：**
设备通过OTA接口获取MQTT配置：
```json
{
  "mqtt": {
    "endpoint": "192.168.0.7:1883",
    "client_id": "GID_default@@@11_22_33_44_55_66@@@7b94d69a-9808-4c59-9c9b-704333b38aff",
    "username": "eyJpcCI6IjA6MDowOjA6MDowOjA6MSJ9",
    "password": "Y8XP9xcUhVIN9OmbCHT9ETBiYNE3l3Z07Wk46wV9PE8=",
    "publish_topic": "device-server",
    "subscribe_topic": "devices/p2p/11_22_33_44_55_66"
  }
}
```

### 2.3 xiaozhi-server (核心服务器)

**作用：**
xiaozhi-server是整个系统的核心，负责处理所有的AI交互逻辑。

**核心功能：**
1. **连接管理**
   - 管理设备WebSocket连接
   - 识别来自MQTT网关的连接（通过`?from=mqtt_gateway`标识）
   - 处理音频和文本消息路由

2. **语音处理**
   - **VAD (Voice Activity Detection)**: 语音活动检测
   - **ASR (Automatic Speech Recognition)**: 语音识别，将音频转换为文本
   - **LLM (Large Language Model)**: 大语言模型，生成回复
   - **TTS (Text-to-Speech)**: 语音合成，将文本转换为音频

3. **工具调用管理**
   - 统一工具处理器 (`UnifiedToolHandler`)
   - 支持多种工具类型：
     - 服务端插件 (SERVER_PLUGIN)
     - 服务端MCP (SERVER_MCP)
     - 设备IoT (DEVICE_IOT)
     - 设备MCP (DEVICE_MCP)
     - **MCP接入点 (MCP_ENDPOINT)**

4. **OTA服务**
   - 提供设备配置下发接口
   - 根据配置决定下发WebSocket或MQTT配置

**与MCP接入点的交互：**
- 通过WebSocket连接到MCP接入点
- 使用MCP协议（JSON-RPC 2.0）进行通信
- 获取工具列表、调用工具、接收结果

### 2.4 MCP接入点 (mcp-endpoint-server)

**作用：**
MCP接入点是一个独立的服务，用于扩展xiaozhi-server的工具能力。它作为xiaozhi-server与外部MCP服务器之间的桥梁。

**核心功能：**
1. **工具代理**
   - 连接到外部MCP服务器
   - 将xiaozhi-server的工具调用请求转发给MCP服务器
   - 将MCP服务器的响应返回给xiaozhi-server

2. **工具管理**
   - 维护工具列表
   - 处理工具调用的异步响应
   - 管理工具调用的超时和错误处理

3. **连接管理**
   - 管理xiaozhi-server的WebSocket连接
   - 管理外部MCP服务器的连接
   - 维护连接状态和健康检查

**端口说明：**
- **8004端口**: WebSocket服务端口，xiaozhi-server通过此端口连接

**MCP协议消息格式：**

**初始化消息：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {"listChanged": true},
      "sampling": {}
    },
    "clientInfo": {
      "name": "XiaozhiMCPEndpointClient",
      "version": "1.0.0"
    }
  }
}
```

**工具列表请求：**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

**工具调用请求：**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "arg1": "value1"
    }
  }
}
```

**工具调用响应：**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "工具执行结果"
      }
    ]
  }
}
```

## 三、消息流转详解

### 3.1 语音交互流程（直接WebSocket）

```
设备 → [音频流] → xiaozhi-server
                    ↓
                  VAD检测
                    ↓
                  ASR识别
                    ↓
                  LLM处理
                    ↓
                  工具调用（可选）
                    ↓
                  TTS合成
                    ↓
xiaozhi-server → [音频流] → 设备
```

### 3.2 语音交互流程（通过MQTT网关）

```
设备 → [MQTT/UDP音频] → MQTT网关 → [WebSocket音频] → xiaozhi-server
                                                          ↓
                                                        VAD/ASR/LLM/TTS
                                                          ↓
xiaozhi-server → [WebSocket音频] → MQTT网关 → [MQTT/UDP音频] → 设备
```

**关键点：**
- MQTT网关在音频包中添加/移除16字节头部
- xiaozhi-server通过`?from=mqtt_gateway`标识识别来自MQTT网关的连接
- 服务器→设备：添加头部（timestamp、sequence等）
- 设备→服务器：解析头部，提取音频数据

### 3.3 MCP工具调用流程

```
LLM生成工具调用请求
    ↓
UnifiedToolHandler.handle_llm_function_call()
    ↓
ToolManager.execute_tool()
    ↓
MCPEndpointExecutor.execute()
    ↓
MCP接入点 (WebSocket, MCP协议)
    ↓
外部MCP服务器
    ↓
工具执行结果返回
    ↓
LLM继续处理或直接返回结果
```

**消息示例：**

1. **xiaozhi-server → MCP接入点**（工具调用请求）
```json
{
  "jsonrpc": "2.0",
  "id": 100,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "city": "北京"
    }
  }
}
```

2. **MCP接入点 → xiaozhi-server**（工具调用响应）
```json
{
  "jsonrpc": "2.0",
  "id": 100,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "北京今天晴天，温度25度"
      }
    ]
  }
}
```

### 3.4 设备配置下发流程

```
设备启动
    ↓
请求OTA接口: POST /xiaozhi/ota/
    ↓
xiaozhi-server检查配置
    ├─ 如果配置了mqtt_gateway → 返回MQTT配置
    └─ 否则 → 返回WebSocket配置
    ↓
设备根据配置连接
    ├─ MQTT配置 → 连接MQTT网关
    └─ WebSocket配置 → 直接连接xiaozhi-server
```

## 四、各组件作用总结

### 4.1 MCP接入点的作用

1. **扩展工具能力**
   - xiaozhi-server本身支持的工具有限
   - MCP接入点可以连接到外部MCP服务器，获取更多工具
   - 例如：天气查询、地图服务、数据库操作等

2. **解耦设计**
   - MCP接入点作为独立服务，可以单独部署和扩展
   - 不影响xiaozhi-server的核心功能
   - 可以连接多个MCP服务器，统一管理

3. **协议转换**
   - 将xiaozhi-server的工具调用转换为MCP协议
   - 将MCP服务器的响应转换为xiaozhi-server可理解的格式

### 4.2 MQTT网关的作用

1. **协议适配**
   - ESP32设备原生支持MQTT协议
   - 通过MQTT网关，设备可以使用MQTT连接，而不需要实现WebSocket客户端

2. **网络优化**
   - MQTT协议更适合低带宽、高延迟的网络环境
   - UDP协议可以降低音频传输的延迟
   - 适合IoT设备的网络特性

3. **连接管理**
   - 统一管理多个设备的连接
   - 提供设备管理API，方便智控台管理设备
   - 支持设备分组和批量操作

## 五、配置关系

### 5.1 全模块部署配置

**智控台参数配置：**
- `server.websocket`: WebSocket地址（用于直接连接）
- `server.mqtt_gateway`: MQTT网关地址（格式：IP:端口）
- `server.mqtt_signature_key`: MQTT签名密钥
- `server.udp_gateway`: UDP网关地址（格式：IP:端口）
- `server.mqtt_manager_api`: MQTT管理API地址（格式：IP:端口）
- `server.mcp_endpoint`: MCP接入点HTTP地址（用于健康检查）

### 5.2 单模块部署配置

**配置文件 `data/.config.yaml`：**
```yaml
server:
  websocket: ws://your-ip:8000/xiaozhi/v1/
  http_port: 8002

mcp_endpoint: ws://your-ip:8004/mcp_endpoint/mcp/?token=xxx

# MQTT网关配置（可选）
server:
  mqtt_gateway: 192.168.0.7:1883
  mqtt_signature_key: your-secret-key
  udp_gateway: 192.168.0.7:8884
```

## 六、关键代码位置

### 6.1 MQTT网关相关

- **音频包处理**: `main/xiaozhi-server/core/connection.py` (第301-332行)
- **音频发送**: `main/xiaozhi-server/core/handle/sendAudioHandle.py` (第58-77行)
- **OTA配置下发**: `main/xiaozhi-server/core/api/ota_handler.py` (第138-151行)

### 6.2 MCP接入点相关

- **MCP接入点连接**: `main/xiaozhi-server/core/providers/tools/mcp_endpoint/mcp_endpoint_handler.py`
- **工具调用**: `main/xiaozhi-server/core/providers/tools/mcp_endpoint/mcp_endpoint_executor.py`
- **统一工具处理**: `main/xiaozhi-server/core/providers/tools/unified_tool_handler.py` (第80-100行)

### 6.3 连接管理

- **WebSocket服务器**: `main/xiaozhi-server/core/websocket_server.py`
- **连接处理**: `main/xiaozhi-server/core/connection.py`
- **消息路由**: `main/xiaozhi-server/core/connection.py` (第268-299行)

## 七、总结

1. **小智设备**：ESP32硬件，支持WebSocket或MQTT+UDP两种连接方式
2. **MQTT网关**：协议转换层，将MQTT/UDP转换为WebSocket，适合IoT场景
3. **xiaozhi-server**：核心服务器，处理所有AI交互逻辑
4. **MCP接入点**：工具扩展层，连接外部MCP服务器，扩展系统能力

整个系统采用模块化设计，各组件职责清晰，可以灵活组合使用。

