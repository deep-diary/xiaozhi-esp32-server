# MCP 方法如何获取设备信息 - 详细教程

本教程将详细指导你如何使用MCP方法获取设备信息，特别是第五步的具体操作位置。

## 前置说明

在开始之前，你需要了解：
- **MCP方法**：指的是通过MCP（Model Context Protocol）协议定义的工具函数
- **设备ID**：每个连接到xiaozhi-server的设备都有一个唯一的设备ID（device_id）
- **参数定义位置**：取决于你使用的MCP类型（设备端MCP、MCP接入点、服务端MCP）

---

## 第一步：自定义你的`agent-base-prompt.txt`文件

### 操作步骤：

1. **找到源文件**：
   - 源文件位置：`xiaozhi-server/agent-base-prompt.txt`
   - 目标位置：`xiaozhi-server/data/.agent-base-prompt.txt`

2. **复制文件**：
   ```bash
   # 在xiaozhi-server目录下执行
   cp agent-base-prompt.txt data/.agent-base-prompt.txt
   ```

3. **验证文件**：
   确保 `data/.agent-base-prompt.txt` 文件已创建成功。

---

## 第二步：修改`data/.agent-base-prompt.txt`文件

### 操作步骤：

1. **打开文件**：
   使用文本编辑器打开 `data/.agent-base-prompt.txt`

2. **找到`<context>`标签**：
   在文件中搜索 `<context>`，找到类似以下内容的位置：
   ```
   <context>
   【重要！以下信息已实时提供，无需调用工具查询，请直接使用：】
   - **当前时间：** {{current_time}}
   - **今天日期：** {{today_date}} ({{today_weekday}})
   - **今天农历：** {{lunar_date}}
   - **用户所在城市：** {{local_address}}
   - **当地未来7天天气：** {{weather_info}}
   </context>
   ```

3. **添加设备ID信息**：
   在 `<context>` 标签内的第一行（或合适位置）添加：
   ```
   - **设备ID：** {{device_id}}
   ```

4. **最终效果**：
   添加完成后，`<context>` 标签内容应该如下：
   ```
   <context>
   【重要！以下信息已实时提供，无需调用工具查询，请直接使用：】
   - **设备ID：** {{device_id}}
   - **当前时间：** {{current_time}}
   - **今天日期：** {{today_date}} ({{today_weekday}})
   - **今天农历：** {{lunar_date}}
   - **用户所在城市：** {{local_address}}
   - **当地未来7天天气：** {{weather_info}}
   </context>
   ```

### 说明：
- `{{device_id}}` 是一个模板变量，系统会在运行时自动替换为实际的设备ID
- 这个信息会显示在LLM的系统提示词中，让LLM知道当前设备的ID

---

## 第三步：修改`data/.config.yaml`文件

### 操作步骤：

1. **打开配置文件**：
   使用文本编辑器打开 `data/.config.yaml`

2. **找到`prompt_template`配置**：
   搜索 `prompt_template`，找到类似以下内容：
   ```yaml
   prompt_template: agent-base-prompt.txt
   ```

3. **修改配置**：
   将配置修改为：
   ```yaml
   prompt_template: data/.agent-base-prompt.txt
   ```

### 说明：
- 这个配置告诉系统使用自定义的提示词模板文件
- 修改后，系统会从 `data/.agent-base-prompt.txt` 读取提示词模板

---

## 第四步：重启xiaozhi-server服务

### 操作步骤：

1. **停止服务**：
   - 如果使用命令行运行：按 `Ctrl+C` 停止
   - 如果使用systemd：`sudo systemctl stop xiaozhi-server`
   - 如果使用Docker：`docker restart xiaozhi-server`

2. **启动服务**：
   - 命令行：`python app.py`
   - systemd：`sudo systemctl start xiaozhi-server`
   - Docker：`docker start xiaozhi-server`

3. **验证启动**：
   查看日志，确认服务正常启动，没有报错。

---

## 第五步：在你的MCP方法中添加`device_id`参数 ⭐（重点）

**这是最关键的一步，也是最容易混淆的地方。**

### 重要说明：

MCP方法的参数定义位置取决于你使用的MCP类型：

#### 情况A：如果你使用的是**MCP接入点**（MCP Endpoint）

如果你按照 [mcp-endpoint-integration.md](./mcp-endpoint-integration.md) 教程，使用MCP接入点方式，那么参数是在**你的MCP服务器代码**中定义的。

**操作步骤：**

1. **找到你的MCP服务器代码**：
   例如，如果你使用的是 `mcp-calculator` 项目，找到定义工具的文件（通常是 `calculator.py` 或类似文件）

2. **找到工具定义位置**：
   在代码中找到类似以下格式的工具定义：
   ```python
   @server.list_tools()
   async def handle_list_tools() -> list[Tool]:
       return [
           Tool(
               name="your_tool_name",
               description="工具描述",
               inputSchema={
                   "type": "object",
                   "properties": {
                       # 这里定义参数
                   },
                   "required": []
               }
           )
       ]
   ```

3. **添加`device_id`参数**：
   在 `inputSchema` 的 `properties` 中添加 `device_id` 参数：
   ```python
   Tool(
       name="your_tool_name",
       description="工具描述",
       inputSchema={
           "type": "object",
           "properties": {
               "device_id": {
                   "type": "string",
                   "description": "设备ID"
               },
               # 你的其他参数...
           },
           "required": ["device_id"]  # 如果device_id是必需的
       }
   )
   ```

4. **在工具实现中使用参数**：
   在你的工具函数中，可以通过参数获取 `device_id`：
   ```python
   @server.call_tool()
   async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
       if name == "your_tool_name":
           device_id = arguments.get("device_id")
           # 使用device_id进行你的业务逻辑
           return [TextContent(type="text", text=f"设备ID: {device_id}")]
   ```

#### 情况B：如果你使用的是**设备端MCP**（Device MCP）

如果你使用的是设备端MCP，参数定义在设备端发送的工具列表中。

**操作步骤：**

1. **找到设备端MCP工具定义**：
   设备端MCP工具通常通过WebSocket消息发送，格式为JSON

2. **在工具定义中添加参数**：
   在发送给服务器的工具列表中，找到你的工具定义，添加 `device_id` 参数：
   ```json
   {
       "name": "your_tool_name",
       "description": "工具描述",
       "inputSchema": {
           "type": "object",
           "properties": {
               "device_id": {
                   "type": "string",
                   "description": "设备ID"
               }
           },
           "required": ["device_id"]
       }
   }
   ```

#### 情况C：如果你使用的是**服务端MCP**（Server MCP）

如果你使用的是服务端MCP，参数定义在服务端MCP服务器的工具定义中。

**操作步骤：**

1. **找到服务端MCP工具定义**：
   在服务端MCP服务器的代码中找到工具定义

2. **添加参数**：
   在工具定义的 `inputSchema` 中添加 `device_id` 参数（格式同情况A）

### 参数定义格式说明：

无论使用哪种MCP类型，参数定义都遵循JSON Schema格式：

```json
{
    "device_id": {
        "type": "string",        // 参数类型：string（字符串）
        "description": "设备ID"  // 参数描述：告诉LLM这个参数的作用
    }
}
```

**参数说明：**
- **名称（name）**：`device_id` - 这是参数的名称，LLM调用时会使用这个名称
- **类型（type）**：`string` - 参数的数据类型，设备ID是字符串类型
- **描述（description）**：`设备ID` - 参数的描述，帮助LLM理解何时需要传递这个参数
- **必需（required）**：如果 `device_id` 是必需的，需要将其添加到 `required` 数组中

### 完整示例（MCP接入点方式）：

假设你有一个名为 `get_device_info` 的工具，完整定义如下：

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("your-server-name")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_device_info",
            description="获取设备信息，需要提供设备ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "设备ID，用于标识具体的设备"
                    },
                    "info_type": {
                        "type": "string",
                        "description": "要获取的信息类型，如：status、config等"
                    }
                },
                "required": ["device_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_device_info":
        device_id = arguments.get("device_id")
        info_type = arguments.get("info_type", "status")
        
        # 使用device_id进行业务逻辑处理
        result = f"设备 {device_id} 的 {info_type} 信息：..."
        
        return [TextContent(type="text", text=result)]
```

---

## 第六步：测试MCP方法

### 操作步骤：

1. **重启服务**（如果修改了MCP服务器代码）：
   - 重启你的MCP服务器
   - 重启xiaozhi-server（如果需要）

2. **唤醒小智**：
   通过语音或文本唤醒小智

3. **测试调用**：
   尝试让LLM调用你的MCP方法，例如：
   - "调用get_device_info方法"
   - "获取设备信息"
   - 或者根据你的工具描述，用自然语言描述需求

4. **查看日志**：
   查看xiaozhi-server的日志，确认：
   - MCP工具是否成功加载
   - 工具调用时是否传递了 `device_id` 参数
   - 工具是否成功执行

5. **验证结果**：
   检查MCP方法的返回结果，确认是否成功获取到了设备ID

### 日志示例：

成功的日志应该类似：
```
INFO - MCP接入点支持的工具数量: 1
INFO - 工具缓存已刷新
INFO - 当前支持的函数列表: [..., 'get_device_info', ...]
INFO - 发送MCP接入点工具调用请求: get_device_info，参数: {"device_id": "11:22:33:44:55:66", "info_type": "status"}
INFO - MCP接入点工具调用 get_device_info 成功
```

---

## 常见问题

### Q1: 我不知道我使用的是哪种MCP类型？

**A:** 查看你的配置文件 `data/.config.yaml`：
- 如果有 `mcp_endpoint` 配置 → 使用的是**MCP接入点**
- 如果设备通过WebSocket发送MCP工具列表 → 使用的是**设备端MCP**
- 如果使用manager-api管理 → 可能是**服务端MCP**

### Q2: LLM没有传递device_id参数？

**A:** 检查以下几点：
1. 确认第二步中已正确添加了 `{{device_id}}` 到提示词模板
2. 确认第三步中已正确配置了 `prompt_template`
3. 确认第四步中已重启服务
4. 确认第五步中参数定义正确，特别是 `description` 字段要清晰说明需要设备ID

### Q3: 参数定义在哪里找不到？

**A:** 
- 如果是MCP接入点：在你的MCP服务器项目代码中查找 `@server.list_tools()` 或类似装饰器
- 如果是设备端MCP：在设备端代码中查找发送工具列表的地方
- 如果不确定：查看xiaozhi-server启动日志，找到MCP工具加载的相关信息

### Q4: 如何确认device_id是否正确传递？

**A:** 
1. 查看xiaozhi-server日志，找到工具调用的日志
2. 日志中会显示传递的参数，例如：`参数: {"device_id": "11:22:33:44:55:66"}`
3. 在你的MCP方法中添加日志输出，打印接收到的参数

---

## 总结

获取设备ID的完整流程：

1. ✅ 在提示词模板中添加 `{{device_id}}` 变量
2. ✅ 配置使用自定义提示词模板
3. ✅ 重启服务使配置生效
4. ✅ **在MCP方法定义中添加 `device_id` 参数**（关键步骤）
5. ✅ 测试验证功能

**关键点：**
- `{{device_id}}` 在提示词中让LLM知道设备ID
- MCP方法参数定义让LLM知道需要传递设备ID
- 两者配合，LLM才能正确调用MCP方法并传递设备ID

