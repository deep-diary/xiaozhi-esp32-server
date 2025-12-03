# DeepDiary 技术实现文档

## 一、技术栈

### 1.1 后端技术

- **Python 3.10+**：主要开发语言
- **aiohttp**：异步 HTTP 服务器
- **websockets**：WebSocket 服务器
- **asyncio**：异步编程框架
- **SQLAlchemy**：ORM 框架
- **Redis**：缓存和消息队列

### 1.2 AI 技术

- **LLM**：支持 OpenAI、Claude、本地模型等
- **VAD**：SileroVAD
- **ASR**：FunASR、Doubao ASR
- **TTS**：多种 TTS 提供商
- **VLLM**：视觉大语言模型

### 1.3 数据存储

- **MySQL 8.0+**：关系数据库
- **Redis 6.0+**：缓存数据库
- **Milvus/Pinecone**：向量数据库

### 1.4 前端技术

- **Gradio**：Web 界面框架
- **WebSocket Client**：实时通信

## 二、核心模块实现

### 2.1 记忆追溯服务实现

#### 2.1.1 数据采集模块

```python
class DataCollector:
    """数据采集器"""
    
    async def collect_diary(self, content, metadata):
        """采集日记数据"""
        # 存储到MySQL
        # 向量化存储
        pass
    
    async def collect_photo(self, photo_data, metadata):
        """采集照片数据"""
        # 上传到Immich
        # 提取元数据
        # 向量化存储
        pass
    
    async def collect_gps(self, location_data):
        """采集GPS数据"""
        # 存储轨迹数据
        # 关联照片和记忆
        pass
    
    async def collect_chat(self, chat_data):
        """采集聊天数据"""
        # 存储对话记录
        # 提取关键信息
        # 关联到人物
        pass
```

#### 2.1.2 记忆检索模块

```python
class MemoryRetrieval:
    """记忆检索"""
    
    def __init__(self):
        self.vector_db = VectorDatabase()
        self.immich_client = ImmichClient()
        self.mem0_client = Mem0Client()
        self.ragflow_client = RAGFlowClient()
    
    async def retrieve_by_timeline(self, start_date, end_date):
        """时间线检索"""
        # 从MySQL查询时间范围内的记录
        # 关联照片、GPS、聊天记录
        # 格式化返回
        pass
    
    async def retrieve_by_person(self, person_id):
        """人物检索"""
        # 从Immich获取人物照片
        # 从mem0ai获取相关记忆
        # 从RAGFlow获取相关知识
        # 向量检索相关记忆
        pass
    
    async def retrieve_by_location(self, location):
        """地点检索"""
        # GPS轨迹查询
        # 照片位置查询
        # 关联记忆
        pass
    
    async def retrieve_by_event(self, keywords):
        """事件检索"""
        # 关键词向量化
        # 向量数据库检索
        # 多源结果聚合
        pass
```

### 2.2 资源追溯服务实现

#### 2.2.1 资源管理模块

```python
class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.vector_db = VectorDatabase()
        self.db = Database()
    
    async def register_resource(self, person_id, resource_data):
        """注册资源"""
        # 1. 验证资源数据
        resource = self.validate_resource(resource_data)
        
        # 2. 向量化资源
        vector = await self.vectorize_resource(resource)
        
        # 3. 存储到数据库
        await self.db.save_resource(person_id, resource, vector)
        
        # 4. 存储到向量数据库
        await self.vector_db.insert_resource(vector, metadata={
            "person_id": person_id,
            "resource_type": resource.type,
            "resource_id": resource.id
        })
        
        return resource.id
    
    async def vectorize_resource(self, resource):
        """向量化资源"""
        # 使用embedding模型向量化
        text = f"{resource.name} {resource.description} {' '.join(resource.tags)}"
        vector = await self.embedding_model.encode(text)
        return vector
```

#### 2.2.2 匹配引擎模块

```python
class MatchingEngine:
    """匹配引擎"""
    
    def __init__(self):
        self.vector_db = VectorDatabase()
        self.db = Database()
    
    async def match_resources_to_demand(self, demand_id, top_k=5):
        """根据需求匹配资源"""
        # 1. 获取需求信息
        demand = await self.db.get_demand(demand_id)
        
        #  _id)
        
        # 2. 向量检索相似资源
        similar_resources = await self.vector_db.search(
            query_vector=demand.vector,
            filter={"type": "resource", "status": "available"},
            top_k=top_k * 2  # 多检索一些用于过滤
        )
        
        # 3. 多维度评分
        matches = []
        for resource in similar_resources:
            score = await self.calculate_match_score(demand, resource)
            if score > 0.6:  # 阈值过滤
                matches.append({
                    "resource": resource,
                    "score": score,
                    "reason": self.generate_match_reason(demand, resource)
                })
        
        # 4. 排序并返回top_k
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_k]
    
    async def calculate_match_score(self, demand, resource):
        """计算匹配度分数"""
        scores = {
            "semantic": self.cosine_similarity(demand.vector, resource.vector),
            "temporal": self.temporal_compatibility(demand, resource),
            "trust": await self.trust_score(demand.person_id, resource.person_id),
            "success_rate": await self.historical_success_rate(resource, demand)
        }
        
        # 加权计算
        weights = {"semantic": 0.5, "temporal": 0.2, "trust": 0.2, "success_rate": 0.1}
        final_score = sum(scores[k] * weights[k] for k in scores)
        return final_score
```

### 2.3 新朋友识别实现

#### 2.3.1 识别流程模块

```python
class NewFriendRecognition:
    """新朋友识别"""
    
    def __init__(self):
        self.immich_client = ImmichClient()
        self.voiceprint_client = VoiceprintClient()
        self.mem0_client = Mem0Client()
        self.llm = LLMClient()
    
    async def process_new_friend(self, image_data, conn):
        """处理新朋友识别流程"""
        # 1. 识别人脸
        face_result = await self.immich_client.recognize_face(image_data)
        
        if face_result.get("person_id"):
            # 已识别，触发记忆检索
            return await self.handle_known_person(face_result["person_id"], conn)
        else:
            # 未识别，启动新朋友流程
            return await self.handle_new_person(image_data, conn)
    
    async def handle_new_person(self, image_data, conn):
        """处理新朋友"""
        # 1. 启动对话引导
        conversation = ConversationGuide()
        
        # 2. 引导确认姓名
        name = await conversation.guide_name_confirmation(conn)
        
        # 3. 调用Immich API自动命名
        person_id = await self.immich_client.create_person(
            name=name,
            face_image=image_data
        )
        
        # 4. 检查并注册声纹
        voiceprint_id = await self.check_and_register_voiceprint(conn, person_id)
        
        # 5. 关联聊天信息
        await self.mem0_client.associate_chat(person_id, conn.session_id)
        
        # 6. 启动资源追溯流程
        await self.start_resource_tracing(conn, person_id)
        
        return person_id
```

#### 2.3.2 对话引导模块

```python
class ConversationGuide:
    """对话引导"""
    
    def __init__(self):
        self.llm = LLMClient()
        self.conversation_state = {}
    
    async def guide_name_confirmation(self, conn):
        """引导姓名确认"""
        questions = [
            "你好，是不是主人的新朋友？",
            "很高兴认识你，怎么称呼？",
            "{name}，是{name_breakdown}吗？"
        ]
        
        name = None
        for question_template in questions:
            if "{name}" in question_template and name:
                question = question_template.format(
                    name=name,
                    name_breakdown=self.breakdown_name(name)
                )
            else:
                question = question_template
            
            # 发送问题
            await conn.send_message({"type": "llm", "text": question})
            
            # 等待回答
            answer = await conn.wait_for_response(timeout=30)
            
            # 提取姓名
            if not name:
                name = self.extract_name(answer)
            else:
                # 确认姓名
                if self.confirm_name(answer):
                    break
        
        return name
    
    async def guide_resource_collection(self, conn, person_id):
        """引导资源收集"""
        questions = {
            "resources": "能告诉我你的三大资源吗？比如技能、人脉、资产等",
            "demands": "那你的三大需求是什么呢？"
        }
        
        collected_info = {}
        for key, question in questions.items():
            await conn.send_message({"type": "llm", "text": question})
            answer = await conn.wait_for_response(timeout=60)
            collected_info[key] = self.extract_info(answer, key)
        
        return collected_info
```

### 2.4 WebSocket 消息推送实现

```python
class WebSocketBroadcaster:
    """WebSocket广播器"""
    
    def __init__(self):
        self.gradio_clients = set()
        self.device_clients = {}
    
    async def register_gradio_client(self, websocket):
        """注册Gradio客户端"""
        self.gradio_clients.add(websocket)
    
    async def broadcast_to_gradio(self, message):
        """广播消息到Gradio客户端"""
        disconnected = set()
        for client in self.gradio_clients:
            try:
                await client.send(json.dumps(message))
            except:
                disconnected.add(client)
        
        # 清理断开的连接
        self.gradio_clients -= disconnected
    
    async def push_memory_markdown(self, markdown_content, session_id=None):
        """推送记忆Markdown"""
        await self.broadcast_to_gradio({
            "type": "memory_markdown",
            "content": markdown_content,
            "session_id": session_id
        })
    
    async def push_resource_match(self, match_result, session_id=None):
        """推送资源匹配结果"""
        await self.broadcast_to_gradio({
            "type": "resource_match",
            "matches": match_result,
            "session_id": session_id
        })
```

## 三、向量化实现

### 3.1 Embedding 模型选择

**推荐方案：**

- **中文场景**：text2vec-large-chinese、bge-large-zh
- **多语言场景**：multilingual-e5-large
- **本地部署**：sentence-transformers

### 3.2 向量化流程

```python
class VectorizationService:
    """向量化服务"""
    
    def __init__(self):
        self.embedding_model = self.load_embedding_model()
    
    async def vectorize_text(self, text):
        """文本向量化"""
        return await self.embedding_model.encode(text)
    
    async def vectorize_resource(self, resource):
        """资源向量化"""
        text = self.build_resource_text(resource)
        return await self.vectorize_text(text)
    
    async def vectorize_demand(self, demand):
        """需求向量化"""
        text = self.build_demand_text(demand)
        return await self.vectorize_text(text)
    
    def build_resource_text(self, resource):
        """构建资源文本"""
        parts = [
            resource.name,
            resource.description,
            f"类型：{resource.type}",
            f"标签：{', '.join(resource.tags)}"
        ]
        return " ".join(parts)
```

## 四、数据库设计

### 4.1 记忆表设计

```sql
CREATE TABLE memories (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    person_id VARCHAR(255),
    memory_type ENUM('diary', 'photo', 'gps', 'chat'),
    content TEXT,
    metadata JSON,
    vector_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_person (person_id),
    INDEX idx_type (memory_type),
    INDEX idx_created (created_at)
);
```

### 4.2 资源表设计

```sql
CREATE TABLE resources (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    person_id VARCHAR(255) NOT NULL,
    resource_type ENUM('skill', 'network', 'asset'),
    name VARCHAR(255),
    description TEXT,
    tags JSON,
    availability ENUM('available', 'busy', 'unavailable'),
    vector_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_person (person_id),
    INDEX idx_type (resource_type),
    INDEX idx_availability (availability)
);
```

### 4.3 需求表设计

```sql
CREATE TABLE demands (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    person_id VARCHAR(255) NOT NULL,
    demand_type ENUM('learning', 'social', 'material'),
    name VARCHAR(255),
    description TEXT,
    tags JSON,
    priority INT DEFAULT 3,
    status ENUM('active', 'fulfilled', 'cancelled'),
    vector_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_person (person_id),
    INDEX idx_type (demand_type),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
);
```

## 五、性能优化

### 5.1 缓存策略

- **记忆检索结果缓存**：Redis 缓存常用查询结果
- **向量检索缓存**：缓存向量检索结果
- **匹配结果缓存**：缓存资源匹配结果

### 5.2 异步处理

- **批量向量化**：批量处理向量化任务
- **异步匹配**：异步执行匹配计算
- **后台任务**：使用任务队列处理耗时任务

### 5.3 数据库优化

- **索引优化**：合理设计数据库索引
- **查询优化**：优化 SQL 查询语句
- **分页查询**：大数据量使用分页

## 六、错误处理

### 6.1 异常处理策略

```python
class ErrorHandler:
    """错误处理器"""
    
    async def handle_service_error(self, service_name, error):
        """处理服务错误"""
        # 记录错误日志
        logger.error(f"{service_name} error: {error}")
        
        # 降级处理
        if service_name == "immich":
            return await self.fallback_photo_search()
        elif service_name == "mem0ai":
            return await self.fallback_memory_search()
        
        # 返回默认值
        return None
```

### 6.2 重试机制

```python
async def retry_with_backoff(func, max_retries=3):
    """重试机制"""
    for i in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if i == max_retries - 1:
                raise
            await asyncio.sleep(2 ** i)  # 指数退避
```

