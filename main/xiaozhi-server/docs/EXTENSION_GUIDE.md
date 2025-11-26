# 扩展开发快速指南

## 概述

本文档提供了在小智服务器中进行自定义开发的快速指南。项目已经为您准备好了独立的扩展目录，您可以在不影响原项目的情况下进行开发。

## 目录结构

```
xiaozhi-server/
├── core/                    # 核心代码（开源项目）
├── plugins_func/            # 系统插件（开源项目）
├── custom/                  # 自定义扩展目录（您的代码）
│   ├── functions/           # 自定义插件函数
│   │   ├── __init__.py
│   │   ├── example.py      # 示例插件
│   │   └── your_plugin.py  # 您的插件
│   ├── README.md           # 详细开发文档
│   └── .gitignore          # Git 忽略文件
└── docs/                   # 文档目录
    ├── ARCHITECTURE.md     # 架构分析文档
    ├── DATA_FLOW.md        # 数据流分析文档
    └── EXTENSION_GUIDE.md  # 本文件
```

## 快速开始

### 1. 创建您的第一个插件

在 `custom/functions/` 目录下创建文件 `my_plugin.py`:

```python
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

MY_PLUGIN_DESC = {
    "type": "function",
    "function": {
        "name": "my_plugin",
        "description": "这是我的第一个插件",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "输入参数",
                },
            },
            "required": ["input"],
        },
    },
}

@register_function("my_plugin", MY_PLUGIN_DESC, ToolType.SYSTEM_CTL)
def my_plugin(conn, input: str):
    """我的插件函数"""
    logger.bind(tag=TAG).info(f"收到输入: {input}")
    result = f"处理结果: {input}"
    return ActionResponse(Action.REQLLM, result, None)
```

### 2. 配置插件

在 `config.yaml` 中添加：

```yaml
Intent:
  Intent_function_call:
    functions:
      - my_plugin  # 添加您的函数名
```

### 3. 重启服务器

```bash
python app.py
```

### 4. 测试

查看日志，确认插件已加载：
```
函数 'my_plugin' 已加载，可以注册使用
```

## 核心概念

### 插件注册

使用 `@register_function` 装饰器注册插件：

```python
@register_function(
    "function_name",      # 函数名（LLM调用时使用）
    FUNCTION_DESC,        # 函数描述（JSON Schema格式）
    ToolType.SYSTEM_CTL   # 工具类型
)
def function_name(conn, param1: str):
    # 函数实现
    return ActionResponse(Action.REQLLM, result, None)
```

### 工具类型 (ToolType)

- `SYSTEM_CTL`: 系统控制（需要 `conn` 参数）
- `IOT_CTL`: IoT 控制（需要 `conn` 参数）
- `WAIT`: 等待返回结果
- `CHANGE_SYS_PROMPT`: 修改系统提示词
- `NONE`: 调用后不做其他操作

### 返回值 (ActionResponse)

- `Action.REQLLM`: 返回结果给 LLM 继续处理（推荐）
- `Action.RESPONSE`: 直接回复用户，不经过 LLM
- `Action.ERROR`: 执行出错

## 常用操作

### 访问连接信息

```python
def my_function(conn, param: str):
    # 设备ID
    device_id = conn.device_id
    
    # 客户端IP
    client_ip = conn.client_ip
    
    # 配置
    config = conn.config
    
    # 对话历史
    dialogue = conn.dialogue
    
    # LLM实例
    llm = conn.llm
    
    # TTS实例
    tts = conn.tts
```

### 发送消息到客户端

```python
from core.handle.sendAudioHandle import send_stt_message

# 发送文本消息
await send_stt_message(conn, "消息内容")

# 通过TTS发送
from core.providers.tts.dto.dto import ContentType
conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail="文本内容")
```

### 使用缓存

```python
from core.utils.cache.manager import cache_manager, CacheType

# 设置缓存
cache_manager.set(CacheType.WEATHER, "key", "value")

# 获取缓存
value = cache_manager.get(CacheType.WEATHER, "key")
```

## 参考文档

1. **架构分析**: `docs/ARCHITECTURE.md` - 完整的系统架构说明
2. **数据流分析**: `docs/DATA_FLOW.md` - 详细的数据流处理过程
3. **扩展开发**: `custom/README.md` - 详细的扩展开发文档
4. **系统插件示例**: `plugins_func/functions/` - 参考系统插件的实现

## 最佳实践

1. **函数命名**: 使用清晰、描述性的函数名，避免与系统插件冲突
2. **错误处理**: 始终使用 try-except 处理异常
3. **日志记录**: 使用 logger 记录关键信息，便于调试
4. **配置管理**: 敏感信息放在配置文件中，不要硬编码
5. **性能考虑**: 避免耗时操作，考虑使用异步或线程

## 版本控制

建议将 `custom/` 目录添加到项目根目录的 `.gitignore`:

```gitignore
# 自定义扩展目录
main/xiaozhi-server/custom/
```

然后在您自己的 Git 仓库中单独管理 `custom/` 目录。

## 更新开源项目

当需要更新开源项目代码时：

1. 确保 `custom/` 目录已添加到 `.gitignore`
2. 正常执行 `git pull` 更新开源代码
3. 您的自定义代码不会受到影响

## 获取帮助

- 查看系统插件示例: `plugins_func/functions/get_weather.py`
- 查看架构文档: `docs/ARCHITECTURE.md`
- 查看数据流文档: `docs/DATA_FLOW.md`
- 查看详细开发文档: `custom/README.md`

祝您开发愉快！

