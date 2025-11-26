# 小智服务器架构分析文档

## 一、系统架构概览

小智服务器（xiaozhi-server）是一个基于 WebSocket 的智能语音助手服务器，采用模块化设计，支持多种 AI 服务提供商，具备插件化扩展能力。

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端 (ESP32)                         │
│                    WebSocket 连接                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    app.py (入口层)                          │
│  - 配置加载                                                  │
│  - 服务器启动                                                │
│  - 信号处理                                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              WebSocketServer (服务器层)                      │
│  - 连接管理                                                  │
│  - 认证授权                                                  │
│  - 模块初始化 (VAD/ASR/LLM/Memory/Intent)                   │
│  - 配置热更新                                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          ConnectionHandler (连接处理层)                      │
│  - 会话管理 (session_id)                                     │
│  - 消息路由 (文本/音频)                                      │
│  - 对话历史管理                                              │
│  - 组件生命周期管理                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
        ▼                                      ▼
┌──────────────────────┐          ┌──────────────────────┐
│   文本消息处理       │          │   音频消息处理        │
│  - textHandle       │          │  - receiveAudioHandle│
│  - textMessage      │          │  - VAD检测            │
│    Processor        │          │  - ASR识别           │
└──────────────────────┘          └──────────────────────┘
        │                                      │
        └──────────────────┬───────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   核心模块层 (Providers)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   VAD    │  │   ASR    │  │   LLM    │  │   TTS    │  │
│  │语音活动  │  │语音识别  │  │大语言模型│  │语音合成  │  │
│  │  检测    │  │          │  │          │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐                              │
│  │ Memory   │  │ Intent   │                              │
│  │  记忆    │  │意图识别  │                              │
│  └──────────┘  └──────────┘                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   工具系统层 (Tools)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         UnifiedToolHandler (统一工具处理器)           │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                       │
│  ┌──────────────────┼──────────────────┐                   │
│  │                  │                  │                   │
│  ▼                  ▼                  ▼                   │
│  ServerPlugin      DeviceIoT        MCP                   │
│  Executor          Executor         Executor               │
│  (服务端插件)      (设备IoT)        (MCP工具)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   插件系统层 (Plugins)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  plugins_func/functions/                              │  │
│  │  - get_weather.py                                     │  │
│  │  - play_music.py                                      │  │
│  │  - hass_*.py (Home Assistant)                        │  │
│  │  - ...                                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件说明

#### 1.2.1 入口层 (app.py)
- **职责**: 应用程序入口，负责初始化配置、启动服务器
- **关键功能**:
  - 加载配置文件 (`config.yaml`)
  - 初始化日志系统
  - 启动 WebSocket 服务器和 HTTP 服务器
  - 处理退出信号

#### 1.2.2 服务器层 (WebSocketServer)
- **职责**: 管理 WebSocket 连接生命周期
- **关键功能**:
  - 监听 WebSocket 连接请求
  - 设备认证和授权
  - 初始化核心模块 (VAD/ASR/LLM/Memory/Intent)
  - 支持配置热更新

#### 1.2.3 连接处理层 (ConnectionHandler)
- **职责**: 处理单个连接的完整生命周期
- **关键功能**:
  - 会话管理 (每个连接独立的 session_id)
  - 消息路由 (区分文本和音频消息)
  - 对话历史管理 (Dialogue)
  - 组件实例化 (TTS/ASR 等按连接创建)
  - 超时管理

## 二、项目目录结构

### 2.1 根目录结构

```
xiaozhi-server/
├── app.py                          # 应用程序入口文件
├── config.yaml                     # 主配置文件
├── config_from_api.yaml            # 从 manager-api 获取的配置
├── requirements.txt                # Python 依赖包列表
├── docker-compose.yml              # Docker Compose 配置
├── docker-compose_all.yml          # 完整 Docker Compose 配置
├── mcp_server_settings.json       # MCP 服务器设置
├── performance_tester.py           # 性能测试脚本
├── agent-base-prompt.txt           # Agent 基础提示词
│
├── config/                         # 配置模块
│   ├── settings.py                 # 配置加载和设置
│   ├── logger.py                   # 日志系统配置
│   ├── config_loader.py            # 配置文件加载器
│   └── assets/                     # 配置资源文件
│       ├── bind_code/              # 绑定码相关
│       └── wakeup_words/           # 唤醒词配置
│
├── core/                           # 核心功能模块
│   ├── websocket_server.py         # WebSocket 服务器
│   ├── http_server.py              # HTTP 服务器
│   ├── connection_handler.py       # 连接处理器
│   │
│   ├── handle/                     # 消息处理层
│   │   ├── textHandle.py           # 文本消息处理
│   │   ├── receiveAudioHandle.py   # 音频接收处理
│   │   ├── sendAudioHandle.py      # 音频发送处理
│   │   ├── textMessageHandler.py   # 文本消息处理器基类
│   │   ├── textMessageHandlerRegistry.py  # 消息处理器注册表
│   │   ├── textMessageType.py      # 消息类型定义
│   │   ├── helloHandle.py          # Hello 消息处理
│   │   ├── abortHandle.py          # 中止消息处理
│   │   ├── reportHandle.py         # 报告消息处理
│   │   └── intentHandler.py        # 意图处理
│   │
│   ├── providers/                  # 核心服务提供商
│   │   ├── vad/                    # 语音活动检测 (VAD)
│   │   │   ├── base.py             # VAD 基类
│   │   │   └── silero.py           # Silero VAD 实现
│   │   │
│   │   ├── asr/                    # 语音识别 (ASR)
│   │   │   ├── base.py             # ASR 基类
│   │   │   ├── aliyun.py           # 阿里云 ASR
│   │   │   ├── aliyun_stream.py    # 阿里云流式 ASR
│   │   │   ├── baidu.py            # 百度 ASR
│   │   │   ├── tencent.py          # 腾讯 ASR
│   │   │   ├── doubao.py           # 豆包 ASR
│   │   │   ├── doubao_stream.py    # 豆包流式 ASR
│   │   │   ├── openai.py           # OpenAI Whisper
│   │   │   ├── xunfei_stream.py    # 讯飞流式 ASR
│   │   │   ├── vosk.py             # Vosk 本地 ASR
│   │   │   ├── sherpa_onnx_local.py  # Sherpa-ONNX 本地 ASR
│   │   │   ├── fun_local.py        # FunASR 本地 ASR
│   │   │   ├── fun_server.py       # FunASR 服务端
│   │   │   ├── qwen3_asr_flash.py  # Qwen3 ASR Flash
│   │   │   └── dto/                 # ASR 数据传输对象
│   │   │
│   │   ├── llm/                    # 大语言模型 (LLM)
│   │   │   ├── base.py             # LLM 基类
│   │   │   ├── system_prompt.py    # 系统提示词管理
│   │   │   ├── openai/             # OpenAI 兼容接口
│   │   │   ├── AliBL/              # 阿里云百炼
│   │   │   ├── ollama.py           # Ollama 本地模型
│   │   │   ├── gemini/             # Google Gemini
│   │   │   ├── coze/               # 字节跳动 Coze
│   │   │   ├── dify/               # Dify 平台
│   │   │   ├── fastgpt/            # FastGPT 平台
│   │   │   ├── xinference/         # Xinference 推理引擎
│   │   │   └── homeassistant/      # Home Assistant 集成
│   │   │
│   │   ├── tts/                    # 文本转语音 (TTS)
│   │   │   ├── base.py             # TTS 基类
│   │   │   ├── aliyun.py           # 阿里云 TTS
│   │   │   ├── aliyun_stream.py    # 阿里云流式 TTS
│   │   │   ├── tencent.py          # 腾讯 TTS
│   │   │   ├── doubao_stream.py    # 豆包流式 TTS
│   │   │   ├── edge.py             # Edge TTS
│   │   │   ├── index_stream.py     # Index 流式 TTS
│   │   │   ├── paddle_speech.py    # PaddleSpeech 本地 TTS
│   │   │   └── fishspeech.py       # FishSpeech 本地 TTS
│   │   │
│   │   ├── memory/                 # 记忆管理
│   │   │   ├── base.py             # Memory 基类
│   │   │   ├── mem_local_short.py  # 本地短期记忆
│   │   │   ├── mem0ai/             # Mem0 AI 服务
│   │   │   └── nomem.py            # 无记忆模式
│   │   │
│   │   ├── intent/                 # 意图识别
│   │   │   ├── base.py             # Intent 基类
│   │   │   ├── function_call/      # Function Calling 模式
│   │   │   ├── intent_llm/         # LLM 意图识别
│   │   │   └── nointent/           # 无意图识别
│   │   │
│   │   ├── tools/                  # 工具系统
│   │   │   ├── unified_tool_handler.py    # 统一工具处理器
│   │   │   ├── unified_tool_manager.py    # 工具管理器
│   │   │   ├── server_plugins.py          # 服务端插件执行器
│   │   │   ├── server_mcp.py              # 服务端 MCP 执行器
│   │   │   ├── device_iot.py              # 设备 IoT 执行器
│   │   │   ├── device_mcp.py              # 设备 MCP 执行器
│   │   │   ├── mcp_endpoint.py            # MCP 接入点执行器
│   │   │   └── base/                      # 工具系统基类
│   │   │       ├── tool_executor.py       # 工具执行器基类
│   │   │       └── tool_type.py           # 工具类型定义
│   │   │
│   │   └── vllm/                   # vLLM 推理引擎
│   │
│   ├── utils/                      # 工具函数
│   │   ├── modules_initialize.py   # 模块初始化工具
│   │   ├── llm.py                  # LLM 工具函数
│   │   ├── tts.py                  # TTS 工具函数
│   │   ├── asr.py                  # ASR 工具函数
│   │   ├── memory.py               # Memory 工具函数
│   │   ├── intent.py               # Intent 工具函数
│   │   ├── dialogue.py             # 对话管理工具
│   │   ├── prompt_manager.py       # 提示词管理器
│   │   ├── util.py                 # 通用工具函数
│   │   ├── auth.py                 # 认证工具
│   │   ├── textUtils.py            # 文本处理工具
│   │   ├── opus_encoder_utils.py   # Opus 编码工具
│   │   ├── output_counter.py       # 输出计数器
│   │   ├── current_time.py         # 时间工具
│   │   ├── p3.py                   # P3 工具
│   │   └── cache/                   # 缓存工具
│   │
│   └── api/                        # API 接口
│
├── plugins_func/                   # 插件函数系统
│   ├── loadplugins.py             # 插件加载器
│   ├── register.py                # 插件注册机制
│   └── functions/                  # 插件函数目录
│       ├── get_weather.py         # 天气查询插件
│       ├── get_time.py            # 时间查询插件
│       ├── play_music.py          # 音乐播放插件
│       ├── get_news_from_chinanews.py  # 新闻查询插件
│       ├── get_news_from_newsnow.py    # 新闻查询插件
│       ├── search_from_ragflow.py     # RAGFlow 搜索插件
│       ├── handle_exit_intent.py      # 退出意图处理
│       ├── change_role.py             # 角色切换插件
│       └── hass_*.py                   # Home Assistant 相关插件
│
├── custom/                         # 自定义扩展目录（用户自定义代码）
│   ├── README.md                  # 自定义扩展说明
│   ├── .gitignore                 # Git 忽略文件
│   └── functions/                 # 自定义插件函数
│       ├── __init__.py
│       ├── example.py             # 示例插件
│       └── my_custom_plugin.py    # 用户自定义插件
│
├── data/                           # 数据目录
│   ├── .config.yaml               # 运行时配置
│   └── .wakeup_words.yaml         # 唤醒词配置
│
├── models/                         # 模型文件目录
│   ├── snakers4_silero-vad/        # Silero VAD 模型
│   └── SenseVoiceSmall/           # SenseVoice 模型
│
├── docs/                           # 文档目录
│   ├── ARCHITECTURE.md            # 架构文档（本文档）
│   ├── DATA_FLOW.md               # 数据流文档
│   └── EXTENSION_GUIDE.md         # 扩展开发指南
│
├── test/                           # 测试相关
│   ├── css/                       # 测试页面样式
│   └── js/                        # 测试页面脚本
│       ├── config/                # 配置相关脚本
│       ├── core/                  # 核心功能脚本
│       ├── ui/                    # UI 相关脚本
│       └── utils/                 # 工具脚本
│
├── music/                          # 音乐文件目录
├── tmp/                            # 临时文件目录
└── performance_tester/             # 性能测试工具
```

### 2.2 关键目录说明

#### 2.2.1 根目录文件
- **`app.py`**: 应用程序入口，负责初始化配置、启动 WebSocket 和 HTTP 服务器
- **`config.yaml`**: 主配置文件，包含服务器、AI 服务提供商等配置
- **`config_from_api.yaml`**: 从 manager-api 动态获取的配置，支持热更新
- **`requirements.txt`**: Python 依赖包列表
- **`docker-compose.yml`**: Docker Compose 配置文件，用于容器化部署

#### 2.2.2 `config/` - 配置模块
- **`settings.py`**: 配置加载和设置管理
- **`logger.py`**: 日志系统配置，提供统一的日志接口
- **`config_loader.py`**: 配置文件加载器，支持从文件或 API 加载配置
- **`assets/`**: 存放配置相关的资源文件，如绑定码、唤醒词等

#### 2.2.3 `core/` - 核心功能模块
- **`websocket_server.py`**: WebSocket 服务器实现，管理连接生命周期
- **`http_server.py`**: HTTP 服务器实现，提供 REST API 接口
- **`connection_handler.py`**: 连接处理器，处理单个连接的完整生命周期

**`core/handle/`** - 消息处理层
- 负责处理不同类型的消息（文本、音频、控制消息等）
- 使用注册表模式管理不同类型的消息处理器

**`core/providers/`** - 核心服务提供商
- 采用策略模式，每个模块都有基类和多个具体实现
- 支持多种 AI 服务提供商，可灵活切换
- 各模块目录结构：
  - `vad/`: 语音活动检测
  - `asr/`: 语音识别（支持流式和非流式）
  - `llm/`: 大语言模型（支持多种平台）
  - `tts/`: 文本转语音（支持流式和非流式）
  - `memory/`: 记忆管理
  - `intent/`: 意图识别
  - `tools/`: 工具系统（插件、IoT、MCP 等）

**`core/utils/`** - 工具函数
- 提供模块初始化、工具函数、对话管理等功能
- `modules_initialize.py`: 模块初始化工具，使用工厂模式创建模块实例

#### 2.2.4 `plugins_func/` - 插件函数系统
- **`loadplugins.py`**: 自动扫描并加载插件函数
- **`register.py`**: 插件注册机制，使用装饰器注册函数
- **`functions/`**: 存放所有插件函数，每个文件对应一个功能插件

#### 2.2.5 `custom/` - 自定义扩展目录
- **用途**: 存放用户自定义开发的代码，与核心代码完全隔离
- **优势**: 不影响原项目，易于更新和维护
- **`functions/`**: 用户自定义插件函数目录
- 详细说明请参考 `custom/README.md`

#### 2.2.6 `data/` - 数据目录
- 存放运行时生成的数据文件
- `.config.yaml`: 运行时配置缓存
- `.wakeup_words.yaml`: 唤醒词配置

#### 2.2.7 `models/` - 模型文件目录
- 存放本地 AI 模型文件
- 如 Silero VAD 模型、SenseVoice 模型等

#### 2.2.8 `docs/` - 文档目录
- 存放项目文档，包括架构文档、数据流文档、扩展开发指南等

### 2.3 文件组织原则

1. **模块化设计**: 每个功能模块独立目录，职责清晰
2. **策略模式**: Provider 模块使用基类+实现的方式，易于扩展
3. **插件化架构**: 插件函数统一管理，支持动态加载
4. **配置分离**: 配置文件与代码分离，支持热更新
5. **自定义隔离**: `custom/` 目录独立，不影响核心代码

### 2.4 扩展点位置

- **添加新的 Provider**: 在 `core/providers/{module}/` 下创建新文件，继承基类
- **添加新的插件**: 在 `plugins_func/functions/` 或 `custom/functions/` 下创建新文件
- **添加新的工具执行器**: 在 `core/providers/tools/` 下创建新执行器类
- **添加新的消息处理器**: 在 `core/handle/` 下创建新处理器，注册到注册表

## 三、数据流分析

### 3.1 音频输入流程

```
客户端发送音频数据
    │
    ▼
WebSocket 接收 (bytes)
    │
    ▼
ConnectionHandler._route_message()
    │
    ▼
receiveAudioHandle.handleAudioMessage()
    │
    ├─→ VAD 检测 (is_vad)
    │   │
    │   ├─→ 检测到语音 → 更新活动时间
    │   └─→ 未检测到语音 → 检查超时
    │
    ▼
ASR.receive_audio()
    │
    ├─→ 流式 ASR (Stream)
    │   │
    │   └─→ 实时识别结果
    │
    └─→ 非流式 ASR
        │
        └─→ 完整识别结果
    │
    ▼
startToChat() (识别完成)
    │
    ├─→ 意图识别 (handle_user_intent)
    │   │
    │   └─→ 特殊意图处理 (退出、播放音乐等)
    │
    └─→ 常规对话流程
        │
        └─→ chat() → LLM 处理
```

### 3.2 文本输入流程

```
客户端发送文本消息 (JSON)
    │
    ▼
ConnectionHandler._route_message()
    │
    ▼
textHandle.handleTextMessage()
    │
    ▼
TextMessageProcessor.process_message()
    │
    ├─→ 解析消息类型 (type)
    │
    ├─→ hello → HelloMessageHandler
    ├─→ listen → ListenMessageHandler
    ├─→ iot → IoTMessageHandler
    ├─→ mcp → MCPMessageHandler
    ├─→ server → ServerMessageHandler
    └─→ abort → AbortMessageHandler
```

### 3.3 LLM 对话流程

```
用户输入文本
    │
    ▼
ConnectionHandler.chat()
    │
    ├─→ 查询记忆 (memory.query_memory)
    │
    ├─→ 构建对话上下文
    │   │
    │   └─→ dialogue.get_llm_dialogue_with_memory()
    │
    ├─→ LLM 流式响应
    │   │
    │   ├─→ 普通文本响应
    │   │   │
    │   │   └─→ TTS 合成 → 发送音频
    │   │
    │   └─→ Function Call (工具调用)
    │       │
    │       └─→ UnifiedToolHandler.handle_llm_function_call()
    │           │
    │           ├─→ 执行工具
    │           │
    │           └─→ 递归调用 chat() (depth + 1)
    │
    └─→ 保存对话历史
        │
        └─→ dialogue.put(Message)
```

### 3.4 工具调用流程

```
LLM 生成 Function Call
    │
    ▼
UnifiedToolHandler.handle_llm_function_call()
    │
    ├─→ 解析工具名称和参数
    │
    ├─→ ToolManager.execute_tool()
    │   │
    │   ├─→ 查找工具类型
    │   │
    │   └─→ 路由到对应执行器
    │       │
    │       ├─→ ServerPluginExecutor (服务端插件)
    │       ├─→ DeviceIoTExecutor (设备IoT)
    │       ├─→ DeviceMCPExecutor (设备MCP)
    │       ├─→ ServerMCPExecutor (服务端MCP)
    │       └─→ MCPEndpointExecutor (MCP接入点)
    │
    ├─→ 执行工具函数
    │
    └─→ 返回 ActionResponse
        │
        ├─→ Action.RESPONSE → 直接回复用户
        ├─→ Action.REQLLM → 继续调用 LLM
        └─→ Action.ERROR → 错误处理
```

### 3.5 TTS 输出流程

```
LLM 生成文本
    │
    ▼
TTSMessageDTO 入队
    │
    ├─→ sentence_type: FIRST/MIDDLE/LAST
    ├─→ content_type: TEXT/ACTION
    └─→ content_detail: 文本内容
    │
    ▼
TTS 处理线程
    │
    ├─→ 文本 → 音频 (TTS 合成)
    │
    ├─→ 音频编码 (Opus)
    │
    └─→ 发送到客户端
```

## 四、模块详细说明

### 4.1 核心模块 (Providers)

#### 4.1.1 VAD (Voice Activity Detection)
- **位置**: `core/providers/vad/`
- **职责**: 检测音频中是否包含人声
- **实现**: 
  - `silero.py`: 基于 Silero VAD 模型
  - `base.py`: 抽象基类

#### 4.1.2 ASR (Automatic Speech Recognition)
- **位置**: `core/providers/asr/`
- **职责**: 将音频转换为文本
- **支持类型**:
  - 流式 ASR: `aliyun_stream.py`, `doubao_stream.py`, `xunfei_stream.py`
  - 非流式 ASR: `aliyun.py`, `baidu.py`, `tencent.py`, `openai.py`
  - 本地 ASR: `vosk.py`, `sherpa_onnx_local.py`, `fun_local.py`

#### 4.1.3 LLM (Large Language Model)
- **位置**: `core/providers/llm/`
- **职责**: 理解用户意图，生成回复
- **支持类型**:
  - OpenAI 兼容: `openai.py`
  - 阿里云: `AliBL/`
  - 其他: `ollama.py`, `gemini.py`, `coze/`, `dify/`, `fastgpt/`

#### 4.1.4 TTS (Text-to-Speech)
- **位置**: `core/providers/tts/`
- **职责**: 将文本转换为语音
- **支持类型**:
  - 流式 TTS: `aliyun_stream.py`, `doubao_stream.py`, `index_stream.py`
  - 非流式 TTS: `aliyun.py`, `tencent.py`, `edge.py`
  - 本地 TTS: `paddle_speech.py`, `fishspeech.py`

#### 4.1.5 Memory (记忆)
- **位置**: `core/providers/memory/`
- **职责**: 管理对话历史，提供上下文
- **实现**:
  - `mem_local_short.py`: 本地短期记忆
  - `mem0ai.py`: Mem0 AI 服务
  - `nomem.py`: 无记忆模式

#### 4.1.6 Intent (意图识别)
- **位置**: `core/providers/intent/`
- **职责**: 识别用户意图，决定是否需要调用工具
- **实现**:
  - `function_call/`: Function Calling 模式
  - `intent_llm/`: LLM 意图识别
  - `nointent/`: 无意图识别

### 4.2 工具系统 (Tools)

#### 4.2.1 工具类型 (ToolType)
- `SERVER_PLUGIN`: 服务端插件
- `DEVICE_IOT`: 设备 IoT 控制
- `DEVICE_MCP`: 设备 MCP 工具
- `SERVER_MCP`: 服务端 MCP 工具
- `MCP_ENDPOINT`: MCP 接入点

#### 4.2.2 工具执行器 (ToolExecutor)
- **基类**: `core/providers/tools/base/tool_executor.py`
- **实现**:
  - `ServerPluginExecutor`: 执行服务端插件
  - `DeviceIoTExecutor`: 执行设备 IoT 控制
  - `DeviceMCPExecutor`: 执行设备 MCP 工具
  - `ServerMCPExecutor`: 执行服务端 MCP 工具
  - `MCPEndpointExecutor`: 执行 MCP 接入点工具

### 4.3 插件系统 (Plugins)

#### 4.3.1 插件加载机制
- **位置**: `plugins_func/loadplugins.py`
- **机制**: 自动扫描 `plugins_func/functions/` 目录，导入所有 Python 模块
- **注册**: 使用 `@register_function` 装饰器注册函数

#### 4.3.2 插件结构
```python
@register_function("function_name", FUNCTION_DESC, ToolType.SYSTEM_CTL)
def function_name(conn, param1: str, param2: int = 0):
    # 函数实现
    return ActionResponse(Action.REQLLM, result, None)
```

#### 4.3.3 插件类型 (ToolType)
- `NONE`: 调用后不做其他操作
- `WAIT`: 等待函数返回
- `CHANGE_SYS_PROMPT`: 修改系统提示词
- `SYSTEM_CTL`: 系统控制 (需要 conn 参数)
- `IOT_CTL`: IoT 设备控制 (需要 conn 参数)
- `MCP_CLIENT`: MCP 客户端

## 五、配置管理

### 5.1 配置文件结构
- **主配置**: `config.yaml`
- **API 配置**: `config_from_api.yaml` (从 manager-api 获取)
- **配置加载**: `config/config_loader.py`

### 5.2 配置热更新
- WebSocketServer 支持从 manager-api 获取新配置
- 检测 VAD/ASR 类型变化，动态重新初始化
- 无需重启服务器

## 六、关键设计模式

### 6.1 工厂模式
- **模块初始化**: `core/utils/modules_initialize.py`
- **工具创建**: `core/utils/llm.py`, `core/utils/tts.py` 等

### 6.2 策略模式
- **Provider 抽象**: 每个模块都有基类，具体实现可替换
- **工具执行器**: 不同类型的工具使用不同的执行器

### 6.3 观察者模式
- **消息路由**: TextMessageHandlerRegistry 注册不同类型的处理器

### 6.4 单例模式
- **日志系统**: `config/logger.py`
- **函数注册表**: `plugins_func/register.py` 中的 `all_function_registry`

## 七、扩展点分析

### 7.1 插件扩展
- **位置**: `plugins_func/functions/`
- **方式**: 创建新的 Python 文件，使用 `@register_function` 装饰器

### 7.2 Provider 扩展
- **位置**: `core/providers/{module}/`
- **方式**: 继承基类，实现接口，在 `core/utils/{module}.py` 中注册

### 7.3 工具执行器扩展
- **位置**: `core/providers/tools/`
- **方式**: 继承 `ToolExecutor`，在 `UnifiedToolHandler` 中注册

## 八、数据流总结

### 8.1 完整对话流程

```
1. 客户端连接
   └─→ WebSocketServer._handle_connection()
       └─→ ConnectionHandler.handle_connection()

2. 音频输入
   └─→ ConnectionHandler._route_message() (bytes)
       └─→ receiveAudioHandle.handleAudioMessage()
           ├─→ VAD 检测
           └─→ ASR.receive_audio()
               └─→ startToChat() (识别完成)

3. 文本处理
   └─→ startToChat()
       ├─→ handle_user_intent() (意图识别)
       └─→ chat() (LLM 对话)

4. LLM 处理
   └─→ ConnectionHandler.chat()
       ├─→ memory.query_memory() (查询记忆)
       ├─→ llm.response() (LLM 生成)
       │   ├─→ 文本响应 → TTS 合成
       │   └─→ Function Call → 工具调用
       └─→ dialogue.put() (保存对话)

5. 工具调用
   └─→ UnifiedToolHandler.handle_llm_function_call()
       └─→ ToolManager.execute_tool()
           └─→ 对应执行器执行
               └─→ 递归调用 chat() (如果需要)

6. TTS 输出
   └─→ TTS 处理线程
       ├─→ 文本 → 音频
       └─→ 发送到客户端

7. 连接关闭
   └─→ memory.save_memory() (保存记忆)
       └─→ ConnectionHandler.close()
```

### 8.2 关键数据结构

#### 8.2.1 Message
```python
class Message:
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    tool_calls: List[Dict]  # Function Call 信息
```

#### 8.2.2 Dialogue
```python
class Dialogue:
    dialogue: List[Message]  # 对话历史
    system_message: str  # 系统提示词
```

#### 8.2.3 ActionResponse
```python
class ActionResponse:
    action: Action  # 动作类型
    result: Any  # 工具执行结果
    response: str  # 直接回复内容
```

## 九、性能优化点

1. **连接级组件实例化**: TTS/ASR 按连接创建，避免共享状态冲突
2. **异步处理**: 使用 asyncio 处理并发连接
3. **线程池**: 使用 ThreadPoolExecutor 处理 CPU 密集型任务
4. **缓存机制**: 记忆、IP 信息等使用缓存
5. **流式处理**: ASR/TTS 支持流式，降低延迟

## 十、安全机制

1. **认证授权**: JWT Token 认证
2. **设备白名单**: 支持设备白名单机制
3. **配置隔离**: 每个连接独立的配置副本
4. **敏感信息过滤**: 日志中过滤敏感信息

