# UML 图查看指南

## 问题：VS Code PlantUML 插件需要 Java

如果您在使用 VS Code 的 PlantUML 插件时遇到 "Unable to locate a Java Runtime" 错误，请按照以下方法解决。

## 解决方案

### 方案1：安装 Java（推荐）

#### 方法A：使用 Homebrew 安装（最简单）

```bash
# 安装 OpenJDK
brew install openjdk

# 或者安装 Oracle JDK
brew install --cask oracle-jdk
```

安装后，重启 VS Code，再次按 `Alt+D` 预览。

#### 方法B：下载安装 Oracle JDK

1. 访问 [Oracle JDK 下载页面](https://www.oracle.com/java/technologies/downloads/)
2. 下载 macOS 版本的 JDK
3. 安装后重启 VS Code

#### 方法C：使用 Adoptium（推荐，免费）

```bash
# 使用 Homebrew 安装 Adoptium OpenJDK
brew install --cask temurin
```

### 方案2：配置 VS Code PlantUML 插件使用本地 Java

如果已安装 Java 但插件找不到，可以手动配置：

1. 打开 VS Code 设置（`Cmd + ,`）
2. 搜索 `plantuml`
3. 找到 `PlantUML: Java` 设置
4. 填入 Java 路径，例如：
   ```
   /usr/local/bin/java
   ```
   或
   ```
   /Library/Java/JavaVirtualMachines/jdk-xx.jdk/Contents/Home/bin/java
   ```

查找 Java 路径：
```bash
which java
# 或
/usr/libexec/java_home -V
```

### 方案3：使用在线工具（无需安装）

如果不想安装 Java，可以使用在线工具：

#### 方法A：PlantUML 官方在线服务器

1. 打开任意 `.puml` 文件
2. 复制全部内容
3. 访问：http://www.plantuml.com/plantuml/uml/
4. 粘贴内容，自动生成图片

#### 方法B：使用 Mermaid（如果支持）

部分 Markdown 查看器支持 Mermaid 格式，我可以帮您转换为 Mermaid 格式。

### 方案4：使用本地 PlantUML 命令行工具

```bash
# 安装 PlantUML（需要 Java）
brew install plantuml

# 生成图片
cd docs/uml
plantuml *.puml

# 会生成对应的 PNG 或 SVG 文件
```

### 方案5：使用 Docker（如果已安装 Docker）

```bash
# 使用 Docker 运行 PlantUML（无需本地安装 Java）
docker run --rm -v "$PWD/docs/uml:/work" plantuml/plantuml:latest *.puml
```

## 快速检查 Java 安装

运行以下命令检查 Java 是否已安装：

```bash
java -version
```

如果显示版本信息，说明已安装。如果显示 "command not found"，需要安装。

## 推荐方案

**推荐方案**：使用在线工具（方案3-A）

优点：
- 无需安装任何软件
- 即开即用
- 支持所有 PlantUML 功能

步骤：
1. 打开 `docs/uml/` 目录下的任意 `.puml` 文件
2. 全选复制（`Cmd + A`, `Cmd + C`）
3. 访问 http://www.plantuml.com/plantuml/uml/
4. 粘贴内容，自动生成图片

## 文件列表

所有 UML 图文件位于 `docs/uml/` 目录：

- `01_core_class_diagram.puml` - 核心类图
- `02_complete_dialogue_sequence.puml` - 完整对话流程
- `03_intent_comparison.puml` - 意图识别对比
- `04_tool_call_sequence.puml` - 工具调用流程
- `05_custom_plugin_loading.puml` - 自定义插件加载
- `06_intent_decision_activity.puml` - 意图识别决策
- `07_tool_call_decision.puml` - 工具调用决策
- `08_audio_processing.puml` - 音频处理流程
- `09_component_diagram.puml` - 系统组件关系
- `10_connection_state.puml` - 连接状态转换
- `11_mcp_call_sequence.puml` - MCP调用流程
- `12_custom_plugin_dev.puml` - 自定义插件开发

## 其他工具推荐

### VS Code 插件替代方案

如果不想安装 Java，可以考虑：

1. **Markdown Preview Mermaid Support** - 如果转换为 Mermaid 格式
2. **Draw.io Integration** - 使用 Draw.io 查看（需要手动转换）
3. **直接在浏览器中查看** - 使用在线工具

### 在线 PlantUML 服务器列表

1. **官方服务器**：http://www.plantuml.com/plantuml/uml/
2. **备用服务器**：https://www.plantuml.com/plantuml/svg/（SVG格式）
3. **本地服务器**：如果安装了 PlantUML，可以运行本地服务器

## 需要帮助？

如果以上方法都无法解决，可以：
1. 告诉我您想查看哪个 UML 图，我可以帮您生成图片
2. 我可以将 PlantUML 转换为其他格式（如 Mermaid）
3. 我可以提供更详细的安装指导

