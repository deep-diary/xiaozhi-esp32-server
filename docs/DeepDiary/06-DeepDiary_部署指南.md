# DeepDiary 部署指南

## 一、环境要求

### 1.1 硬件要求

- **CPU**：4 核以上
- **内存**：8GB 以上
- **存储**：100GB 以上可用空间
- **网络**：稳定的网络连接

### 1.2 软件要求

- **操作系统**：Linux (Ubuntu 20.04+) / Windows 10+ / macOS
- **Python**：3.10+
- **Docker**：20.10+（可选）
- **Docker Compose**：2.0+（可选）

### 1.3 依赖服务

- **MySQL**：8.0+
- **Redis**：6.0+
- **向量数据库**：Milvus 2.3+ 或 Pinecone（云服务）

## 二、依赖服务部署

### 2.1 MySQL 部署

**Docker 部署：**

```bash
docker run -d \
  --name deepdiary-mysql \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -e MYSQL_DATABASE=deepdiary \
  -p 3306:3306 \
  mysql:8.0
```

**初始化数据库：**

```sql
CREATE DATABASE deepdiary CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2.2 Redis 部署

**Docker 部署：**

```bash
docker run -d \
  --name deepdiary-redis \
  -p 6379:6379 \
  redis:6.2-alpine
```

### 2.3 向量数据库部署

#### 方案一：Milvus（本地部署）

```bash
# 使用Docker Compose部署
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

#### 方案二：Pinecone（云服务）

1. 注册 Pinecone 账号
2. 创建索引
3. 获取 API Key

### 2.4 Immich 部署

参考 [Immich 官方文档](https://immich.app/docs/install/docker-compose)

### 2.5 mem0ai 部署

参考 mem0ai 官方文档或使用云服务

### 2.6 RAGFlow 部署

参考 [RAGFlow 官方文档](https://ragflow.io/docs/install)

## 三、xiaozhi-server 部署

### 3.1 源码部署

**1. 克隆项目**

```bash
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server.git
cd xiaozhi-esp32-server
```

**2. 安装依赖**

```bash
cd main/xiaozhi-server
pip install -r requirements.txt
```

**3. 配置环境**

创建 `.env` 文件：

```env
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=deepdiary

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 向量数据库配置
VECTOR_DB_TYPE=milvus  # 或 pinecone
MILVUS_HOST=localhost
MILVUS_PORT=19530
PINECONE_API_KEY=your_api_key
PINECONE_ENVIRONMENT=your_environment

# Immich配置
IMMICH_URL=http://localhost:2283
IMMICH_API_KEY=your_api_key

# mem0ai配置
MEM0_API_URL=http://localhost:8005
MEM0_API_KEY=your_api_key

# RAGFlow配置
RAGFLOW_URL=http://localhost:8008
RAGFLOW_API_KEY=your_api_key
```

**4. 配置文件**

编辑 `data/.config.yaml`：

```yaml
server:
  websocket_port: 8000
  vision_port: 8003
  ota_port: 8002

# 记忆追溯配置
memory_tracing:
  enabled: true
  vector_db_type: milvus

# 资源追溯配置
resource_tracing:
  enabled: true
  vector_db_type: milvus
```

**5. 启动服务**

```bash
python app.py
```

### 3.2 Docker 部署

**1. 构建镜像**

```bash
docker build -t deepdiary-server .
```

**2. 运行容器**

```bash
docker run -d \
  --name deepdiary-server \
  -p 8000:8000 \
  -p 8003:8003 \
  -p 8002:8002 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env \
  deepdiary-server
```

### 3.3 Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  deepdiary-server:
    build: .
    ports:
      - "8000:8000"
      - "8003:8003"
      - "8002:8002"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    depends_on:
      - mysql
      - redis
    environment:
      - MYSQL_HOST=mysql
      - REDIS_HOST=redis

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: deepdiary
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"

volumes:
  mysql_data:
```

启动服务：

```bash
docker-compose up -d
```

## 四、Gradio Web 界面部署

### 4.1 安装依赖

```bash
pip install gradio websockets requests
```

### 4.2 配置连接

编辑 `gradio_app.py`：

```python
WEBSOCKET_URL = "ws://your-server:8000/xiaozhi/v1/"
VISION_API_URL = "http://your-server:8003/mcp/vision/explain"
```

### 4.3 启动服务

```bash
python gradio_app.py
```

访问：`http://localhost:7860`

### 4.4 生产环境部署

**使用 Gunicorn：**

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:7860 gradio_app:app
```

**使用 Nginx 反向代理：**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 五、MQTT 网关部署

参考 [MQTT 网关部署文档](../mqtt-gateway-integration.md)

## 六、验证部署

### 6.1 检查服务状态

```bash
# 检查WebSocket服务
curl http://localhost:8000/health

# 检查视觉服务
curl http://localhost:8003/mcp/vision/explain

# 检查数据库连接
mysql -h localhost -u root -p -e "SHOW DATABASES;"
```

### 6.2 测试 WebSocket 连接

使用测试工具连接 WebSocket：

```bash
wscat -c ws://localhost:8000/xiaozhi/v1/ \
  -H "Authorization: Bearer your_token" \
  -H "Device-Id: test_device"
```

### 6.3 测试 API 接口

```bash
# 测试视觉识别
curl -X POST http://localhost:8003/mcp/vision/explain \
  -H "Authorization: Bearer your_token" \
  -F "file=@test.jpg" \
  -F "question=描述这张图片"

# 测试记忆检索
curl http://localhost:8000/api/memory/timeline \
  -H "Authorization: Bearer your_token"
```

## 七、常见问题

### 7.1 端口冲突

如果端口被占用，修改配置文件中的端口号。

### 7.2 数据库连接失败

检查数据库配置和网络连接。

### 7.3 向量数据库连接失败

检查向量数据库服务状态和配置。

### 7.4 WebSocket 连接失败

检查防火墙设置和认证配置。

## 八、性能优化

### 8.1 数据库优化

- 合理设计索引
- 定期优化表
- 使用连接池

### 8.2 缓存优化

- 启用 Redis 缓存
- 设置合理的过期时间
- 使用缓存预热

### 8.3 向量检索优化

- 合理设置索引参数
- 使用批量检索
- 缓存常用查询

