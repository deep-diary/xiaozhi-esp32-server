# 小智服务器 UML 架构图

本文档使用 UML 图描述小智服务器的完整架构和流程。

> **注意**：由于 PlantUML 代码较长，在线查看可能会遇到 "Request header is too large" 错误。
> 
> **解决方案**：
> 1. 查看独立的 UML 文件：所有 UML 图已拆分为独立文件，位于 `docs/uml/` 目录
> 2. 使用 VS Code PlantUML 插件：安装后可直接预览
> 3. 使用本地 PlantUML 工具：`brew install plantuml` 或下载 jar 包
> 
> 详细说明请查看：`docs/uml/README.md`

## 一、系统类图

### 1.1 核心类图

> **独立文件**：`docs/uml/01_core_class_diagram.puml`  
> 建议使用独立文件查看，避免在线工具请求头过大错误。

```plantuml
@startuml 核心类图
!theme plain

package "入口层" {
    class app {
        +main()
        +wait_for_exit()
    }
}

package "服务器层" {
    class WebSocketServer {
        -config: dict
        -_vad: VADProvider
        -_asr: ASRProvider
        -_llm: LLMProvider
        -_memory: MemoryProvider
        -_intent: IntentProvider
        -auth: AuthManager
        +start()
        +_handle_connection()
        +update_config()
        +_handle_auth()
    }
}

package "连接处理层" {
    class ConnectionHandler {
        -session_id: str
        -device_id: str
        -client_ip: str
        -websocket: WebSocket
        -vad: VADProvider
        -asr: ASRProvider
        -llm: LLMProvider
        -tts: TTSProvider
        -memory: MemoryProvider
        -intent: IntentProvider
        -dialogue: Dialogue
        -func_handler: UnifiedToolHandler
        +handle_connection()
        +_route_message()
        +chat()
        +_initialize_components()
    }
    
    class Dialogue {
        -dialogue: List[Message]
        -system_message: str
        +put(message: Message)
        +get_llm_dialogue_with_memory()
    }
    
    class Message {
        +role: str
        +content: str
        +tool_calls: List[Dict]
    }
}

package "核心模块层" {
    abstract class VADProvider {
        +is_vad(conn, audio): bool
    }
    
    abstract class ASRProvider {
        +receive_audio(conn, audio, have_voice)
        +open_audio_channels(conn)
    }
    
    abstract class LLMProvider {
        +response(session_id, dialogue)
        +response_with_functions(session_id, dialogue, functions)
    }
    
    abstract class TTSProvider {
        +tts_one_sentence(conn, content_type, content_detail)
        +open_audio_channels(conn)
    }
    
    abstract class MemoryProvider {
        +query_memory(query): str
        +save_memory(dialogue)
        +init_memory(role_id, llm, summary_memory)
    }
    
    abstract class IntentProviderBase {
        +detect_intent(conn, dialogue_history, text): str
    }
    
    class SileroVAD {
        +is_vad(conn, audio): bool
    }
    
    class FunASR {
        +receive_audio(conn, audio, have_voice)
    }
    
    class ChatGLMLLM {
        +response(session_id, dialogue)
        +response_with_functions(session_id, dialogue, functions)
    }
    
    class EdgeTTS {
        +tts_one_sentence(conn, content_type, content_detail)
    }
    
    class MemLocalShort {
        +query_memory(query): str
        +save_memory(dialogue)
    }
    
    class IntentLLM {
        -llm: LLMProvider
        +detect_intent(conn, dialogue_history, text): str
    }
    
    class FunctionCallIntent {
        +detect_intent(conn, dialogue_history, text): str
    }
}

package "工具系统层" {
    class UnifiedToolHandler {
        -tool_manager: ToolManager
        -server_plugin_executor: ServerPluginExecutor
        -device_iot_executor: DeviceIoTExecutor
        -device_mcp_executor: DeviceMCPExecutor
        -server_mcp_executor: ServerMCPExecutor
        -mcp_endpoint_executor: MCPEndpointExecutor
        +get_functions()
        +handle_llm_function_call(conn, function_call_data)
        +_initialize()
    }
    
    class ToolManager {
        -executors: Dict[ToolType, ToolExecutor]
        +register_executor(tool_type, executor)
        +execute_tool(tool_name, arguments)
        +get_all_tools()
    }
    
    abstract class ToolExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
        +get_tools(): Dict[str, ToolDefinition]
    }
    
    class ServerPluginExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
        +get_tools(): Dict[str, ToolDefinition]
    }
    
    class DeviceIoTExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
        +register_iot_tools(descriptors)
    }
    
    class DeviceMCPExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
    }
    
    class ServerMCPExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
        +initialize()
    }
    
    class MCPEndpointExecutor {
        +execute(conn, tool_name, arguments): ActionResponse
    }
}

package "插件系统层" {
    class FunctionRegistry {
        -function_registry: Dict[str, FunctionItem]
        +register_function(name, func_item)
        +get_function(name): FunctionItem
    }
    
    class FunctionItem {
        +name: str
        +description: dict
        +func: callable
        +type: ToolType
    }
    
    enum ToolType {
        NONE
        WAIT
        CHANGE_SYS_PROMPT
        SYSTEM_CTL
        IOT_CTL
        MCP_CLIENT
    }
    
    enum Action {
        ERROR
        NOTFOUND
        NONE
        RESPONSE
        REQLLM
    }
    
    class ActionResponse {
        +action: Action
        +result: Any
        +response: str
    }
}

' 关系定义
app --> WebSocketServer
WebSocketServer --> ConnectionHandler
ConnectionHandler --> Dialogue
Dialogue --> Message
ConnectionHandler --> VADProvider
ConnectionHandler --> ASRProvider
ConnectionHandler --> LLMProvider
ConnectionHandler --> TTSProvider
ConnectionHandler --> MemoryProvider
ConnectionHandler --> IntentProviderBase
ConnectionHandler --> UnifiedToolHandler

VADProvider <|-- SileroVAD
ASRProvider <|-- FunASR
LLMProvider <|-- ChatGLMLLM
TTSProvider <|-- EdgeTTS
MemoryProvider <|-- MemLocalShort
IntentProviderBase <|-- IntentLLM
IntentProviderBase <|-- FunctionCallIntent

UnifiedToolHandler --> ToolManager
ToolManager --> ToolExecutor
ToolExecutor <|-- ServerPluginExecutor
ToolExecutor <|-- DeviceIoTExecutor
ToolExecutor <|-- DeviceMCPExecutor
ToolExecutor <|-- ServerMCPExecutor
ToolExecutor <|-- MCPEndpointExecutor

ServerPluginExecutor --> FunctionRegistry
FunctionRegistry --> FunctionItem
FunctionItem --> ToolType
FunctionItem --> ActionResponse
ActionResponse --> Action

@enduml
```

## 二、序列图

### 2.1 完整对话流程序列图

> **独立文件**：`docs/uml/02_complete_dialogue_sequence.puml`

```plantuml
@startuml 完整对话流程
!theme plain

actor 客户端 as Client
participant WebSocketServer
participant ConnectionHandler
participant VAD
participant ASR
participant IntentHandler
participant LLM
participant UnifiedToolHandler
participant ToolExecutor
participant PluginFunction
participant TTS

Client -> WebSocketServer: WebSocket连接请求
WebSocketServer -> WebSocketServer: 认证授权
WebSocketServer -> ConnectionHandler: 创建连接处理器
WebSocketServer -> ConnectionHandler: 初始化组件(VAD/ASR/LLM/TTS/Memory/Intent)

Client -> ConnectionHandler: 发送音频数据(bytes)
ConnectionHandler -> VAD: 检测语音活动
VAD --> ConnectionHandler: have_voice: bool
ConnectionHandler -> ASR: 接收音频
ASR -> ASR: 识别处理
ASR --> ConnectionHandler: 识别结果(文本)

alt intent_type == "function_call"
    ConnectionHandler -> LLM: response_with_functions(dialogue, functions)
    LLM --> ConnectionHandler: 流式响应(文本或Function Call)
    
    alt 检测到Function Call
        ConnectionHandler -> UnifiedToolHandler: handle_llm_function_call()
        UnifiedToolHandler -> ToolManager: execute_tool()
        ToolManager -> ToolExecutor: execute()
        ToolExecutor -> PluginFunction: 调用函数
        PluginFunction --> ToolExecutor: ActionResponse
        ToolExecutor --> ToolManager: ActionResponse
        ToolManager --> UnifiedToolHandler: ActionResponse
        
        alt Action == REQLLM
            UnifiedToolHandler --> ConnectionHandler: 工具执行结果
            ConnectionHandler -> LLM: chat(depth+1) 递归调用
            LLM --> ConnectionHandler: 最终回复
        else Action == RESPONSE
            UnifiedToolHandler --> ConnectionHandler: 直接回复
        end
    end
    
else intent_type == "intent_llm"
    ConnectionHandler -> IntentHandler: handle_user_intent(text)
    IntentHandler -> IntentLLM: detect_intent(dialogue, text)
    IntentLLM -> LLM: 意图识别LLM调用
    LLM --> IntentLLM: 意图识别结果(JSON)
    IntentLLM --> IntentHandler: function_call JSON
    
    alt 需要调用工具
        IntentHandler -> UnifiedToolHandler: handle_llm_function_call()
        UnifiedToolHandler -> ToolExecutor: execute()
        ToolExecutor -> PluginFunction: 调用函数
        PluginFunction --> ToolExecutor: ActionResponse
        ToolExecutor --> UnifiedToolHandler: ActionResponse
        
        alt Action == REQLLM
            UnifiedToolHandler -> IntentLLM: replyResult(工具结果, 原始文本)
            IntentLLM -> LLM: 生成自然语言回复
            LLM --> IntentLLM: 回复文本
            IntentLLM --> IntentHandler: 回复文本
        end
    else continue_chat
        IntentHandler -> LLM: 常规对话
        LLM --> IntentHandler: 回复文本
    end
end

ConnectionHandler -> TTS: tts_one_sentence(文本)
TTS -> TTS: 文本转语音
TTS --> ConnectionHandler: 音频数据
ConnectionHandler -> Client: 发送音频数据

@enduml
```

### 2.2 意图识别流程对比序列图

> **独立文件**：`docs/uml/03_intent_comparison.puml`

```plantuml
@startuml 意图识别流程对比
!theme plain

== intent_llm 模式 ==

actor 用户
participant ConnectionHandler
participant IntentHandler
participant IntentLLM
participant IntentLLM_LLM as "意图识别LLM"
participant UnifiedToolHandler
participant ToolExecutor
participant PluginFunction
participant MainLLM as "主LLM"

用户 -> ConnectionHandler: 用户输入文本
ConnectionHandler -> IntentHandler: handle_user_intent(text)
IntentHandler -> IntentLLM: detect_intent(dialogue, text)

note right of IntentLLM
  使用独立的LLM进行意图识别
  分析用户意图，决定是否需要调用工具
end note

IntentLLM -> IntentLLM_LLM: 意图识别调用
IntentLLM_LLM --> IntentLLM: 返回JSON格式的意图结果
IntentLLM --> IntentHandler: {"function_call": {"name": "xxx", "arguments": {...}}}

alt 需要调用工具
    IntentHandler -> UnifiedToolHandler: handle_llm_function_call()
    UnifiedToolHandler -> ToolExecutor: execute()
    ToolExecutor -> PluginFunction: 调用函数
    PluginFunction --> ToolExecutor: ActionResponse
    ToolExecutor --> UnifiedToolHandler: ActionResponse
    
    alt Action == REQLLM
        UnifiedToolHandler -> IntentLLM: replyResult(工具结果, 原始文本)
        IntentLLM -> MainLLM: 生成自然语言回复
        MainLLM --> IntentLLM: 回复文本
        IntentLLM --> IntentHandler: 回复文本
    end
else continue_chat
    IntentHandler -> MainLLM: 常规对话
    MainLLM --> IntentHandler: 回复文本
end

IntentHandler --> ConnectionHandler: 回复文本

== function_call 模式 ==

actor 用户2 as "用户"
participant ConnectionHandler2 as "ConnectionHandler"
participant MainLLM2 as "主LLM(支持Function Calling)"
participant UnifiedToolHandler2 as "UnifiedToolHandler"
participant ToolExecutor2 as "ToolExecutor"
participant PluginFunction2 as "PluginFunction"

用户2 -> ConnectionHandler2: 用户输入文本
ConnectionHandler2 -> MainLLM2: response_with_functions(dialogue, functions)

note right of MainLLM2
  主LLM在生成回复过程中
  自动决定是否需要调用工具
  无需额外的意图识别步骤
end note

MainLLM2 --> ConnectionHandler2: 流式响应

alt 检测到Function Call
    ConnectionHandler2 -> UnifiedToolHandler2: handle_llm_function_call()
    UnifiedToolHandler2 -> ToolExecutor2: execute()
    ToolExecutor2 -> PluginFunction2: 调用函数
    PluginFunction2 --> ToolExecutor2: ActionResponse
    ToolExecutor2 --> UnifiedToolHandler2: ActionResponse
    
    alt Action == REQLLM
        UnifiedToolHandler2 --> ConnectionHandler2: 工具执行结果
        ConnectionHandler2 -> MainLLM2: chat(depth+1) 递归调用
        MainLLM2 --> ConnectionHandler2: 最终回复
    end
else 普通文本回复
    MainLLM2 --> ConnectionHandler2: 直接回复文本
end

ConnectionHandler2 --> 用户2: 回复

@enduml
```

### 2.3 工具调用流程序列图

> **独立文件**：`docs/uml/04_tool_call_sequence.puml`

```plantuml
@startuml 工具调用流程
!theme plain

participant LLM
participant ConnectionHandler
participant UnifiedToolHandler
participant ToolManager
participant ToolExecutor
participant ServerPluginExecutor
participant DeviceIoTExecutor
participant DeviceMCPExecutor
participant ServerMCPExecutor
participant MCPEndpointExecutor
participant FunctionRegistry
participant PluginFunction
participant MCPClient

LLM -> ConnectionHandler: Function Call请求
ConnectionHandler -> UnifiedToolHandler: handle_llm_function_call(function_call_data)

UnifiedToolHandler -> UnifiedToolHandler: 解析function_name和arguments
UnifiedToolHandler -> ToolManager: execute_tool(tool_name, arguments)

ToolManager -> ToolManager: get_tool_type(tool_name)

alt tool_type == SERVER_PLUGIN
    ToolManager -> ServerPluginExecutor: execute(conn, tool_name, arguments)
    ServerPluginExecutor -> FunctionRegistry: get_function(tool_name)
    FunctionRegistry --> ServerPluginExecutor: FunctionItem
    ServerPluginExecutor -> PluginFunction: 调用函数
    PluginFunction --> ServerPluginExecutor: ActionResponse
    
else tool_type == DEVICE_IOT
    ToolManager -> DeviceIoTExecutor: execute(conn, tool_name, arguments)
    DeviceIoTExecutor -> DeviceIoTExecutor: 查找IoT设备描述符
    DeviceIoTExecutor -> PluginFunction: 调用IoT控制函数
    PluginFunction --> DeviceIoTExecutor: ActionResponse
    
else tool_type == DEVICE_MCP
    ToolManager -> DeviceMCPExecutor: execute(conn, tool_name, arguments)
    DeviceMCPExecutor -> MCPClient: 调用MCP工具
    MCPClient --> DeviceMCPExecutor: 结果
    DeviceMCPExecutor -> DeviceMCPExecutor: 转换为ActionResponse
    
else tool_type == SERVER_MCP
    ToolManager -> ServerMCPExecutor: execute(conn, tool_name, arguments)
    ServerMCPExecutor -> MCPClient: 调用MCP工具
    MCPClient --> ServerMCPExecutor: 结果
    ServerMCPExecutor -> ServerMCPExecutor: 转换为ActionResponse
    
else tool_type == MCP_ENDPOINT
    ToolManager -> MCPEndpointExecutor: execute(conn, tool_name, arguments)
    MCPEndpointExecutor -> MCPEndpointExecutor: 通过WebSocket调用MCP接入点
    MCPEndpointExecutor --> MCPEndpointExecutor: 结果
end

ToolExecutor --> ToolManager: ActionResponse
ToolManager --> UnifiedToolHandler: ActionResponse

alt Action == REQLLM
    UnifiedToolHandler --> ConnectionHandler: 工具执行结果
    ConnectionHandler -> ConnectionHandler: 添加到对话历史
    ConnectionHandler -> LLM: chat(depth+1) 递归调用
    LLM --> ConnectionHandler: 最终回复
    
else Action == RESPONSE
    UnifiedToolHandler --> ConnectionHandler: 直接回复文本
    ConnectionHandler -> ConnectionHandler: 通过TTS回复用户
    
else Action == ERROR
    UnifiedToolHandler --> ConnectionHandler: 错误信息
    ConnectionHandler -> ConnectionHandler: 错误处理
end

@enduml
```

### 2.4 自定义插件加载流程序列图

> **独立文件**：`docs/uml/05_custom_plugin_loading.puml`

```plantuml
@startuml 自定义插件加载流程
!theme plain

participant app
participant WebSocketServer
participant ConnectionHandler
participant UnifiedToolHandler
participant loadplugins
participant FunctionRegistry
participant CustomPlugin as "custom/functions/my_custom_plugin.py"

app -> WebSocketServer: 启动服务器
WebSocketServer -> WebSocketServer: 初始化核心模块

WebSocketServer -> ConnectionHandler: 创建连接处理器
ConnectionHandler -> UnifiedToolHandler: 创建工具处理器
UnifiedToolHandler -> UnifiedToolHandler: _initialize()

note right of UnifiedToolHandler
  1. 先加载系统插件
  2. 再加载自定义插件
end note

UnifiedToolHandler -> loadplugins: auto_import_modules("plugins_func.functions")
loadplugins -> loadplugins: 扫描plugins_func/functions目录
loadplugins -> loadplugins: 导入所有Python模块

UnifiedToolHandler -> loadplugins: auto_import_modules("custom.functions")
loadplugins -> loadplugins: 扫描custom/functions目录
loadplugins -> CustomPlugin: 导入my_custom_plugin.py

CustomPlugin -> FunctionRegistry: @register_function装饰器
note right of CustomPlugin
  注册函数:
  - get_system_info
  - calculate
  - process_text
end note

FunctionRegistry -> FunctionRegistry: 添加到all_function_registry

UnifiedToolHandler -> UnifiedToolHandler: 初始化各类执行器
UnifiedToolHandler -> ServerPluginExecutor: 注册到ToolManager
ServerPluginExecutor -> FunctionRegistry: get_tools()
FunctionRegistry --> ServerPluginExecutor: 所有注册的函数(包括自定义)

UnifiedToolHandler -> UnifiedToolHandler: 输出当前支持的所有工具列表

@enduml
```

## 三、活动图

### 3.1 意图识别决策流程活动图

> **独立文件**：`docs/uml/06_intent_decision_activity.puml`

```plantuml
@startuml 意图识别决策流程
!theme plain

start

:用户输入文本;

if (intent_type == "function_call"?) then (是)
    :直接进入LLM对话流程;
    :LLM自动决定是否调用工具;
    stop
else (否)
    :进入意图识别流程;
    
    if (intent_type == "intent_llm"?) then (是)
        :使用独立的LLM进行意图识别;
        :分析用户意图;
        
        if (识别到需要调用工具?) then (是)
            :返回function_call JSON;
            :执行工具;
            
            if (Action == REQLLM?) then (是)
                :使用主LLM生成回复;
            else (否)
                :直接回复用户;
            endif
        else (否)
            :返回continue_chat;
            :进入常规对话流程;
        endif
    else (否, nointent)
        :不使用意图识别;
        :直接进入常规对话流程;
    endif
endif

stop

@enduml
```

### 3.2 工具调用决策流程活动图

> **独立文件**：`docs/uml/07_tool_call_decision.puml`

```plantuml
@startuml 工具调用决策流程
!theme plain

start

:收到Function Call请求;

:解析function_name和arguments;

:查找工具类型;

if (工具类型?) then
    if (SERVER_PLUGIN?) then (是)
        :ServerPluginExecutor执行;
        :从FunctionRegistry获取函数;
        :调用插件函数;
    elseif (DEVICE_IOT?) then (是)
        :DeviceIoTExecutor执行;
        :查找IoT设备描述符;
        :调用IoT控制函数;
    elseif (DEVICE_MCP?) then (是)
        :DeviceMCPExecutor执行;
        :通过MCP客户端调用;
    elseif (SERVER_MCP?) then (是)
        :ServerMCPExecutor执行;
        :通过MCP客户端调用;
    elseif (MCP_ENDPOINT?) then (是)
        :MCPEndpointExecutor执行;
        :通过WebSocket调用MCP接入点;
    else (未找到)
        :返回NOTFOUND;
        stop
    endif
else (未找到)
    :返回NOTFOUND;
    stop
endif

:执行工具函数;

if (执行成功?) then (是)
    if (Action == REQLLM?) then (是)
        :将结果添加到对话历史;
        :递归调用chat(depth+1);
        :LLM生成最终回复;
    elseif (Action == RESPONSE?) then (是)
        :直接通过TTS回复用户;
    else (其他)
        :根据Action类型处理;
    endif
else (否)
    :返回ERROR;
    :错误处理;
endif

stop

@enduml
```

### 3.3 音频处理流程活动图

> **独立文件**：`docs/uml/08_audio_processing.puml`

```plantuml
@startuml 音频处理流程
!theme plain

start

:接收音频数据(bytes);

:VAD检测;

if (检测到语音?) then (是)
    :更新活动时间;
    
    if (正在播放TTS?) then (是)
        if (listen_mode == "manual"?) then (是)
            :不中断;
        else (否)
            :中断当前播放;
        endif
    endif
    
    :将音频加入ASR队列;
    
    if (ASR类型?) then
        if (流式ASR?) then (是)
            :实时识别;
            :部分结果回调;
        else (非流式ASR?) then (是)
            :等待完整音频;
            :一次性识别;
        endif
    endif
    
    :ASR识别完成;
    :获取识别文本;
    
    :进入对话流程;
else (否)
    :检查超时;
    
    if (超时?) then (是)
        :发送结束提示;
        :关闭连接;
        stop
    else (否)
        :继续等待;
    endif
endif

stop

@enduml
```

## 四、组件图

### 4.1 系统组件关系图

> **独立文件**：`docs/uml/09_component_diagram.puml`

```plantuml
@startuml 系统组件关系图
!theme plain

package "客户端层" {
    [ESP32设备]
}

package "网络层" {
    [WebSocket服务器]
    [HTTP服务器]
}

package "应用层" {
    [连接管理器]
    [消息路由器]
}

package "核心服务层" {
    package "语音处理" {
        [VAD服务]
        [ASR服务]
        [TTS服务]
    }
    
    package "AI服务" {
        [LLM服务]
        [意图识别服务]
        [记忆服务]
    }
}

package "工具层" {
    [统一工具处理器]
    [工具管理器]
    [工具执行器]
}

package "插件层" {
    [系统插件]
    [自定义插件]
    [IoT插件]
    [MCP插件]
}

package "数据层" {
    [对话历史]
    [记忆存储]
    [配置管理]
    [缓存管理]
}

[ESP32设备] --> [WebSocket服务器]
[WebSocket服务器] --> [连接管理器]
[连接管理器] --> [消息路由器]

[消息路由器] --> [VAD服务]
[消息路由器] --> [ASR服务]
[消息路由器] --> [LLM服务]
[消息路由器] --> [意图识别服务]
[消息路由器] --> [TTS服务]

[LLM服务] --> [统一工具处理器]
[意图识别服务] --> [统一工具处理器]
[统一工具处理器] --> [工具管理器]
[工具管理器] --> [工具执行器]

[工具执行器] --> [系统插件]
[工具执行器] --> [自定义插件]
[工具执行器] --> [IoT插件]
[工具执行器] --> [MCP插件]

[连接管理器] --> [对话历史]
[记忆服务] --> [记忆存储]
[连接管理器] --> [配置管理]
[统一工具处理器] --> [缓存管理]

@enduml
```

## 五、状态图

### 5.1 连接状态转换图

> **独立文件**：`docs/uml/10_connection_state.puml`

```plantuml
@startuml 连接状态转换
!theme plain

[*] --> 等待连接

等待连接 --> 已连接 : WebSocket连接
已连接 --> 初始化中 : 开始初始化
初始化中 --> 就绪 : 初始化完成

就绪 --> 处理音频 : 收到音频数据
就绪 --> 处理文本 : 收到文本消息

处理音频 --> VAD检测 : 音频数据
VAD检测 --> ASR识别 : 检测到语音
VAD检测 --> 检查超时 : 未检测到语音
检查超时 --> 就绪 : 未超时
检查超时 --> 关闭连接 : 超时

ASR识别 --> 意图识别 : 识别完成
处理文本 --> 意图识别 : 文本消息

意图识别 --> LLM处理 : 需要LLM处理
意图识别 --> 工具调用 : 需要调用工具
意图识别 --> 直接回复 : 直接回复

工具调用 --> LLM处理 : Action=REQLLM
工具调用 --> 直接回复 : Action=RESPONSE

LLM处理 --> TTS合成 : 生成文本
直接回复 --> TTS合成 : 回复文本

TTS合成 --> 发送音频 : 合成完成
发送音频 --> 就绪 : 发送完成

就绪 --> 关闭连接 : 用户退出/超时/错误
关闭连接 --> [*] : 清理完成

@enduml
```

## 六、intent_llm 与 function_call 详细对比

### 6.1 核心区别

| 特性 | intent_llm | function_call |
|------|-----------|---------------|
| **工作原理** | 使用独立的LLM先进行意图识别，再决定是否调用工具 | 主LLM在对话过程中自动决定是否调用工具 |
| **处理流程** | 意图识别 → 工具调用 → LLM生成回复 | LLM对话 → 工具调用 → LLM继续对话 |
| **LLM调用次数** | 2次（意图识别LLM + 主LLM） | 1次或多次（主LLM递归调用） |
| **响应速度** | 较慢（需要额外的意图识别步骤） | 较快（无需额外步骤） |
| **成本** | 较高（需要额外的LLM调用） | 较低（只需主LLM调用） |
| **通用性** | 高（可以处理复杂的意图识别逻辑） | 中（依赖LLM的function calling能力） |
| **灵活性** | 高（可以自定义意图识别逻辑） | 中（依赖LLM的function calling实现） |
| **适用场景** | 需要复杂意图识别、需要独立控制意图识别逻辑 | LLM支持function calling、追求响应速度 |

### 6.2 使用场景建议

#### 使用 intent_llm 的场景：

1. **需要复杂的意图识别逻辑**
   - 需要根据对话历史、上下文进行复杂判断
   - 需要自定义意图识别的提示词和规则

2. **需要独立的意图识别模型**
   - 主LLM不支持function calling
   - 希望使用更轻量级的模型进行意图识别以节省成本

3. **需要精确控制工具调用时机**
   - 需要根据特定规则决定是否调用工具
   - 需要处理特殊的意图识别逻辑（如result_for_context）

4. **需要支持多函数并行调用**
   - intent_llm可以返回多个function_call的数组
   - 适合"打开灯并且调高音量"这样的复合指令

#### 使用 function_call 的场景：

1. **LLM支持function calling**
   - 使用的LLM（如ChatGLM、Doubao等）支持function calling功能
   - 希望利用LLM的原生function calling能力

2. **追求响应速度**
   - 希望减少延迟，提高响应速度
   - 不需要额外的意图识别步骤

3. **简化架构**
   - 希望简化系统架构，减少组件
   - 不需要独立的意图识别逻辑

4. **成本敏感**
   - 希望减少LLM调用次数以降低成本
   - 充分利用主LLM的能力

### 6.3 配置示例

#### intent_llm 配置：

```yaml
selected_module:
  Intent: intent_llm

Intent:
  intent_llm:
    type: intent_llm
    llm: ChatGLMLLM  # 独立的意图识别LLM
    functions:
      - get_weather
      - play_music
      - get_system_info
```

#### function_call 配置：

```yaml
selected_module:
  Intent: function_call

Intent:
  function_call:
    type: function_call
    functions:
      - get_weather
      - play_music
      - get_system_info
      - calculate
      - process_text
```

### 6.4 性能对比

```plantuml
@startuml 性能对比
!theme plain

|intent_llm模式|
start
:用户输入;
:意图识别LLM调用 (200-500ms);
:工具执行 (100-1000ms);
:主LLM生成回复 (500-2000ms);
:总耗时: 800-3500ms;
stop

|function_call模式|
start
:用户输入;
:主LLM处理 (可能包含工具调用) (500-2000ms);
if (需要工具?) then (是)
    :工具执行 (100-1000ms);
    :主LLM继续处理 (500-2000ms);
else (否)
endif
:总耗时: 500-3000ms (通常更快);
stop

@enduml
```

## 七、MCP调用流程序列图

> **独立文件**：`docs/uml/11_mcp_call_sequence.puml`

```plantuml
@startuml MCP调用流程
!theme plain

participant LLM
participant ConnectionHandler
participant UnifiedToolHandler
participant ToolManager
participant MCPExecutor as "MCP执行器"
participant MCPClient as "MCP客户端"
participant MCPServer as "MCP服务器"

== 设备MCP调用 ==

LLM -> ConnectionHandler: Function Call (device_mcp工具)
ConnectionHandler -> UnifiedToolHandler: handle_llm_function_call()
UnifiedToolHandler -> ToolManager: execute_tool()
ToolManager -> DeviceMCPExecutor: execute()

DeviceMCPExecutor -> MCPClient: 调用MCP工具
MCPClient -> MCPServer: MCP协议调用
MCPServer --> MCPClient: 工具执行结果
MCPClient --> DeviceMCPExecutor: 结果
DeviceMCPExecutor --> ToolManager: ActionResponse

== 服务端MCP调用 ==

LLM -> ConnectionHandler: Function Call (server_mcp工具)
ConnectionHandler -> UnifiedToolHandler: handle_llm_function_call()
UnifiedToolHandler -> ToolManager: execute_tool()
ToolManager -> ServerMCPExecutor: execute()

ServerMCPExecutor -> MCPClient: 调用MCP工具
MCPClient -> MCPServer: MCP协议调用
MCPServer --> MCPClient: 工具执行结果
MCPClient --> ServerMCPExecutor: 结果
ServerMCPExecutor --> ToolManager: ActionResponse

== MCP接入点调用 ==

LLM -> ConnectionHandler: Function Call (mcp_endpoint工具)
ConnectionHandler -> UnifiedToolHandler: handle_llm_function_call()
UnifiedToolHandler -> ToolManager: execute_tool()
ToolManager -> MCPEndpointExecutor: execute()

MCPEndpointExecutor -> MCPEndpointExecutor: 通过WebSocket调用MCP接入点
note right of MCPEndpointExecutor
  MCP接入点是一个WebSocket服务
  可以连接到外部的MCP服务器
end note
MCPEndpointExecutor --> ToolManager: ActionResponse

ToolManager --> UnifiedToolHandler: ActionResponse
UnifiedToolHandler --> ConnectionHandler: ActionResponse

alt Action == REQLLM
    ConnectionHandler -> LLM: chat(depth+1)
    LLM --> ConnectionHandler: 最终回复
end

@enduml
```

## 八、自定义插件开发流程活动图

> **独立文件**：`docs/uml/12_custom_plugin_dev.puml`

```plantuml
@startuml 自定义插件开发流程
!theme plain

start

:在custom/functions/目录创建插件文件;

:定义函数描述(FUNCTION_DESC);

:使用@register_function装饰器注册函数;

:实现函数逻辑;

if (需要conn参数?) then (是)
    :使用ToolType.SYSTEM_CTL或IOT_CTL;
else (否)
    :使用ToolType.WAIT或其他;
endif

:在config.yaml中添加函数名;

:重启服务器;

if (插件加载成功?) then (是)
    :查看日志确认;
    :测试功能;
    
    if (功能正常?) then (是)
        :开发完成;
        stop
    else (否)
        :调试问题;
        :修改代码;
        :重新测试;
    endif
else (否)
    :检查错误日志;
    :修复问题;
    :重新加载;
endif

@enduml
```

## 九、快速访问独立 UML 文件

所有 UML 图已拆分为独立文件，位于 `docs/uml/` 目录：

| 文件 | 说明 | 类型 |
|------|------|------|
| `01_core_class_diagram.puml` | 核心类图 | 类图 |
| `02_complete_dialogue_sequence.puml` | 完整对话流程 | 序列图 |
| `03_intent_comparison.puml` | 意图识别对比 | 序列图 |
| `04_tool_call_sequence.puml` | 工具调用流程 | 序列图 |
| `05_custom_plugin_loading.puml` | 自定义插件加载 | 序列图 |
| `06_intent_decision_activity.puml` | 意图识别决策 | 活动图 |
| `07_tool_call_decision.puml` | 工具调用决策 | 活动图 |
| `08_audio_processing.puml` | 音频处理流程 | 活动图 |
| `09_component_diagram.puml` | 系统组件关系 | 组件图 |
| `10_connection_state.puml` | 连接状态转换 | 状态图 |
| `11_mcp_call_sequence.puml` | MCP调用流程 | 序列图 |
| `12_custom_plugin_dev.puml` | 自定义插件开发 | 活动图 |

**查看方法**：
1. 在线查看：访问 [PlantUML 在线服务器](http://www.plantuml.com/plantuml/uml/)，复制文件内容查看
2. VS Code：安装 PlantUML 插件，打开 `.puml` 文件按 `Alt+D` 预览
3. 本地工具：`brew install plantuml` 或使用 Java jar 包

详细说明请查看：`docs/uml/README.md`

## 总结

本文档使用UML图全面描述了小智服务器的架构和流程：

1. **类图**: 展示了系统的核心类和它们之间的关系
2. **序列图**: 详细描述了各种交互流程
3. **活动图**: 展示了决策和处理流程
4. **组件图**: 展示了系统组件之间的关系
5. **状态图**: 展示了连接状态转换

### intent_llm vs function_call 总结

- **intent_llm**: 适合需要复杂意图识别、需要独立控制、可以接受稍慢响应的场景
- **function_call**: 适合LLM支持function calling、追求速度、希望简化架构的场景

选择建议：
- 如果您的LLM支持function calling（如ChatGLM、Doubao），推荐使用`function_call`
- 如果需要复杂的意图识别逻辑或使用不支持function calling的LLM，使用`intent_llm`
- 如果对响应速度要求高，优先考虑`function_call`
- 如果需要精确控制工具调用时机，使用`intent_llm`

