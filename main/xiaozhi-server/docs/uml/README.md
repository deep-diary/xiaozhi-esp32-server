# UML 图文件说明

本目录包含小智服务器的所有 UML 架构图，每个文件对应一个独立的 UML 图，方便单独查看和编辑。

## 文件列表

### 类图
- **01_core_class_diagram.puml** - 核心类图，展示系统主要类和关系

### 序列图
- **02_complete_dialogue_sequence.puml** - 完整对话流程序列图
- **03_intent_comparison.puml** - intent_llm 与 function_call 对比序列图
- **04_tool_call_sequence.puml** - 工具调用流程序列图
- **05_custom_plugin_loading.puml** - 自定义插件加载流程序列图
- **11_mcp_call_sequence.puml** - MCP 调用流程序列图

### 活动图
- **06_intent_decision_activity.puml** - 意图识别决策流程活动图
- **07_tool_call_decision.puml** - 工具调用决策流程活动图
- **08_audio_processing.puml** - 音频处理流程活动图
- **12_custom_plugin_dev.puml** - 自定义插件开发流程活动图

### 组件图
- **09_component_diagram.puml** - 系统组件关系图

### 状态图
- **10_connection_state.puml** - 连接状态转换图

## 使用方法

### 方法1：在线查看（推荐）

1. 访问 [PlantUML 在线服务器](http://www.plantuml.com/plantuml/uml/)
2. 打开对应的 `.puml` 文件
3. 复制文件内容到在线编辑器
4. 点击生成图片

### 方法2：VS Code 插件

1. 安装 VS Code 插件：`PlantUML`
2. 打开 `.puml` 文件
3. 按 `Alt+D` 预览图片

### 方法3：本地工具

1. 安装 PlantUML：
   ```bash
   # macOS
   brew install plantuml
   
   # 或使用 Java
   java -jar plantuml.jar *.puml
   ```

2. 生成图片：
   ```bash
   plantuml *.puml
   ```

### 方法4：使用 MCP 工具（如果配置了）

如果您的环境配置了 PlantUML MCP 工具，可以直接查看。

## 查看顺序建议

1. **01_core_class_diagram.puml** - 先了解整体架构
2. **09_component_diagram.puml** - 了解组件关系
3. **02_complete_dialogue_sequence.puml** - 了解完整对话流程
4. **03_intent_comparison.puml** - 理解 intent_llm 和 function_call 的区别
5. **04_tool_call_sequence.puml** - 了解工具调用机制
6. **11_mcp_call_sequence.puml** - 了解 MCP 调用流程
7. 其他活动图和状态图根据需要查看

## 注意事项

- 每个 `.puml` 文件都是独立的，可以单独查看
- 文件大小已优化，适合在线查看
- 如果遇到问题，可以尝试使用本地 PlantUML 工具

## 相关文档

- 架构分析：`../ARCHITECTURE.md`
- 数据流分析：`../DATA_FLOW.md`
- intent_llm vs function_call：`../INTENT_VS_FUNCTION_CALL.md`
- UML 架构图（汇总）：`../UML_ARCHITECTURE.md`

