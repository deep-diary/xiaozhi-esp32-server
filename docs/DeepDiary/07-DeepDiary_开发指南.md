# DeepDiary 开发指南

## 一、开发环境搭建

### 1.1 环境要求

- **Python**：3.10+
- **Node.js**：18+（可选，用于前端开发）
- **Git**：2.0+
- **IDE**：推荐 VS Code 或 PyCharm

### 1.2 项目结构

```
xiaozhi-esp32-server/
├── main/
│   └── xiaozhi-server/
│       ├── core/
│       │   ├── api/          # API接口
│       │   ├── handle/       # 消息处理
│       │   ├── providers/    # 服务提供者
│       │   └── utils/        # 工具类
│       ├── config/           # 配置文件
│       └── app.py            # 主程序
├── docs/
│   └── DeepDiary/           # 项目文档
└── requirements.txt         # 依赖列表
```

### 1.3 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.4 配置开发环境

创建 `data/.config.yaml`：

```yaml
# 开发环境配置
debug: true
log_level: DEBUG

# 服务配置
server:
  websocket_port: 8000
  vision_port: 8003
```

## 二、代码规范

### 2.1 Python 代码规范

**遵循 PEP 8 规范：**

- 使用 4 个空格缩进
- 行长度不超过 100 字符
- 使用有意义的变量名
- 添加类型注解

**示例：**

```python
from typing import List, Optional, Dict

async def retrieve_memories(
    person_id: str,
    keywords: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """检索记忆

    Args:
        person_id: 人物ID
        keywords: 关键词（可选）
        limit: 返回数量限制

    Returns:
        记忆列表
    """
    pass
```

### 2.2 文件命名规范

- **Python 文件**：使用小写字母和下划线，如 `memory_service.py`
- **类名**：使用驼峰命名，如 `MemoryService`
- **函数名**：使用小写字母和下划线，如 `retrieve_memories`

### 2.3 注释规范

**模块注释：**

```python
"""
记忆追溯服务模块

提供记忆检索、格式化等功能
"""
```

**函数注释：**

```python
async def retrieve_memories(person_id: str) -> List[Dict]:
    """检索指定人物的记忆

    Args:
        person_id: 人物ID

    Returns:
        记忆列表，每个记忆包含id、type、content等字段

    Raises:
        ValueError: 当person_id为空时
    """
    pass
```

## 三、核心模块开发

### 3.1 记忆追溯服务开发

**创建新模块：**

```python
# core/services/memory_tracing_service.py
from typing import List, Dict, Optional
from datetime import datetime

class MemoryTracingService:
    """记忆追溯服务"""

    def __init__(self, config: dict):
        self.config = config
        self.vector_db = self._init_vector_db()
        self.immich_client = self._init_immich_client()

    async def trace_by_timeline(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 20
    ) -> List[Dict]:
        """时间线追溯"""
        # 实现逻辑
        pass
```

### 3.2 资源追溯服务开发

**创建新模块：**

```python
# core/services/resource_tracing_service.py
class ResourceTracingService:
    """资源追溯服务"""

    async def register_resource(
        self,
        person_id: str,
        resource_data: dict
    ) -> str:
        """注册资源"""
        # 1. 验证数据
        # 2. 向量化
        # 3. 存储
        pass
```

### 3.3 WebSocket 消息处理

**扩展消息类型：**

```python
# core/handle/textHandler/memoryMessageHandler.py
from core.handle.textHandler.base import TextMessageHandler

class MemoryMessageHandler(TextMessageHandler):
    """记忆消息处理器"""

    async def handle(self, conn, msg_json: dict):
        """处理记忆消息"""
        message_type = msg_json.get("type")

        if message_type == "memory_query":
            await self.handle_memory_query(conn, msg_json)

    async def handle_memory_query(self, conn, msg_json: dict):
        """处理记忆查询"""
        # 实现查询逻辑
        pass
```

## 四、测试

### 4.1 单元测试

**创建测试文件：**

```python
# tests/test_memory_tracing.py
import pytest
from core.services.memory_tracing_service import MemoryTracingService

@pytest.mark.asyncio
async def test_trace_by_person():
    """测试人物追溯"""
    service = MemoryTracingService(config={})
    result = await service.trace_by_person("person_123")
    assert len(result) > 0
```

**运行测试：**

```bash
pytest tests/
```

### 4.2 集成测试

**测试 WebSocket 连接：**

```python
# tests/test_websocket.py
import pytest
import websockets
import json

@pytest.mark.asyncio
async def test_websocket_connection():
    """测试WebSocket连接"""
    uri = "ws://localhost:8000/xiaozhi/v1/"
    async with websockets.connect(uri) as websocket:
        message = {"type": "hello", "content": "test"}
        await websocket.send(json.dumps(message))
        response = await websocket.recv()
        assert response is not None
```

## 五、调试技巧

### 5.1 日志调试

**使用日志：**

```python
from config.logger import setup_logging

logger = setup_logging()

async def my_function():
    logger.info("开始执行")
    try:
        result = await some_operation()
        logger.debug(f"操作结果: {result}")
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
```

### 5.2 断点调试

**VS Code 调试配置：**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: 当前文件",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### 5.3 性能分析

**使用 cProfile：**

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 执行代码
await my_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

## 六、Git 工作流

### 6.1 分支管理

- **main**：主分支，稳定版本
- **develop**：开发分支
- **feature/xxx**：功能分支
- **bugfix/xxx**：修复分支

### 6.2 提交规范

**提交消息格式：**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型：**

- `feat`：新功能
- `fix`：修复 bug
- `docs`：文档更新
- `style`：代码格式
- `refactor`：重构
- `test`：测试
- `chore`：构建/工具

**示例：**

```
feat(memory): 添加记忆时间线检索功能

实现了按时间范围检索记忆的功能
支持时间范围过滤和分页

Closes #123
```

## 七、贡献指南

### 7.1 贡献流程

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request
5. 代码审查
6. 合并代码

### 7.2 代码审查标准

- 代码符合规范
- 有适当的测试
- 有文档更新
- 通过 CI 检查

## 八、常见问题

### 8.1 导入错误

**问题：** 模块导入失败

**解决：** 检查 Python 路径和模块结构

### 8.2 异步问题

**问题：** 异步函数调用错误

**解决：** 确保使用 `await` 调用异步函数

### 8.3 数据库连接问题

**问题：** 数据库连接失败

**解决：** 检查数据库配置和连接池设置

## 九、开发工具推荐

### 9.1 IDE 插件

- **Python**：Python 扩展
- **Pylance**：类型检查
- **Black**：代码格式化
- **isort**：导入排序

### 9.2 调试工具

- **pdb**：Python 调试器
- **ipdb**：增强版调试器
- **pytest-debugging**：pytest 调试插件

### 9.3 代码质量工具

- **pylint**：代码检查
- **mypy**：类型检查
- **black**：代码格式化
- **isort**：导入排序

## 十、最佳实践

### 10.1 异步编程

#### 10.1.1 async/await vs 回调

**回调方式（不推荐）：**

```python
# 回调地狱示例
def fetch_data(callback):
    """使用回调的方式"""
    def on_success(data):
        def on_process(processed):
            def on_save(saved):
                callback(saved)
            save_data(processed, on_save)
        process_data(data, on_process)
    get_data(on_success)

# 调用
fetch_data(lambda result: print(f"结果: {result}"))
```

**问题：**

- 嵌套层级深，难以阅读和维护
- 错误处理复杂
- 难以控制执行流程

**async/await 方式（推荐）：**

```python
# 使用async/await
async def fetch_data():
    """使用async/await的方式"""
    data = await get_data()           # 等待数据获取
    processed = await process_data(data)  # 等待数据处理
    result = await save_data(processed)  # 等待数据保存
    return result

# 调用
result = await fetch_data()
print(f"结果: {result}")
```

**优势：**

- 代码结构清晰，类似同步代码
- 错误处理简单（使用 try/except）
- 易于理解和维护
- 支持并发执行

**对比示例：**

```python
# ========== 回调方式 ==========
def get_user_info(user_id, callback):
    """获取用户信息（回调方式）"""
    def on_user(user):
        def on_profile(profile):
            def on_resources(resources):
                callback({
                    "user": user,
                    "profile": profile,
                    "resources": resources
                })
            get_resources(user_id, on_resources)
        get_profile(user_id, on_profile)
    get_user(user_id, on_user)

# 调用（回调地狱）
get_user_info("user_123", lambda result:
    print(f"用户信息: {result}"))

# ========== async/await方式 ==========
async def get_user_info(user_id):
    """获取用户信息（async/await方式）"""
    user = await get_user(user_id)
    profile = await get_profile(user_id)
    resources = await get_resources(user_id)
    return {
        "user": user,
        "profile": profile,
        "resources": resources
    }

# 调用（清晰简洁）
result = await get_user_info("user_123")
print(f"用户信息: {result}")
```

**并行执行对比：**

```python
# ========== 回调方式（难以并行）==========
def fetch_multiple_data(callback):
    results = []
    count = 0

    def check_complete():
        if len(results) == 3:
            callback(results)

    get_data1(lambda r: results.append(r) or check_complete())
    get_data2(lambda r: results.append(r) or check_complete())
    get_data3(lambda r: results.append(r) or check_complete())

# ========== async/await方式（易于并行）==========
async def fetch_multiple_data():
    # 并行执行多个异步操作
    results = await asyncio.gather(
        get_data1(),
        get_data2(),
        get_data3()
    )
    return results
```

**错误处理对比：**

```python
# ========== 回调方式（错误处理复杂）==========
def fetch_data_with_error(callback, error_callback):
    def on_success(data):
        def on_error(err):
            error_callback(err)
        try:
            process_data(data, callback)
        except Exception as e:
            on_error(e)
    get_data(on_success)

# ========== async/await方式（错误处理简单）==========
async def fetch_data_with_error():
    try:
        data = await get_data()
        result = await process_data(data)
        return result
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise
```

**在 DeepDiary 项目中的应用：**

```python
# 记忆检索服务中的实际应用
class MemoryRetrievalService:
    async def retrieve_memories(self, people, keywords):
        """检索记忆（使用async/await）"""
        # 并行检索多个数据源
        results = await asyncio.gather(
            self._retrieve_immich_photos(people),  # 并行执行
            self._retrieve_mem0_memories(keywords),  # 并行执行
            self._retrieve_ragflow_knowledge(keywords),  # 并行执行
            return_exceptions=True  # 即使某个失败也继续
        )

        # 处理结果
        return self._aggregate_results(results)

    # 如果使用回调方式，代码会变成：
    # def retrieve_memories(self, people, keywords, callback):
    #     def on_photos(photos):
    #         def on_memories(memories):
    #             def on_knowledge(knowledge):
    #                 callback(aggregate(photos, memories, knowledge))
    #             self._retrieve_ragflow_knowledge(keywords, on_knowledge)
    #         self._retrieve_mem0_memories(keywords, on_memories)
    #     self._retrieve_immich_photos(people, on_photos)
```

**总结：**

| 特性           | 回调方式                  | async/await 方式            |
| -------------- | ------------------------- | --------------------------- |
| **代码可读性** | ❌ 嵌套深，难以阅读       | ✅ 类似同步代码，清晰       |
| **错误处理**   | ❌ 复杂，需要多层错误回调 | ✅ 简单，使用 try/except    |
| **并行执行**   | ❌ 难以实现               | ✅ 使用 asyncio.gather 简单 |
| **调试难度**   | ❌ 难以调试               | ✅ 易于调试                 |
| **代码维护**   | ❌ 难以维护               | ✅ 易于维护                 |

**最佳实践：**

- ✅ **优先使用 async/await**：代码更清晰、易维护
- ✅ **避免回调嵌套**：超过 2 层嵌套就应该考虑重构
- ✅ **使用 asyncio.gather**：并行执行多个异步操作
- ✅ **合理使用 await**：只在需要等待结果时使用

#### 10.1.2 其他异步编程要点

- 避免阻塞操作
- 合理使用 `asyncio.gather` 并行执行

### 10.2 错误处理

- 使用具体的异常类型
- 记录详细的错误信息
- 提供有意义的错误消息

### 10.3 性能优化

- 使用缓存减少重复计算
- 批量处理数据
- 使用连接池管理数据库连接

### 10.4 安全性

- 验证所有输入
- 使用参数化查询
- 加密敏感数据
- 实施访问控制
