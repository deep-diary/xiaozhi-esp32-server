# Immich 集成开发文档

## 📋 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [API 层实现](#api-层实现)
4. [业务逻辑层实现](#业务逻辑层实现)
5. [人脸识别功能实现](#人脸识别功能实现)
6. [使用示例](#使用示例)
7. [测试指南](#测试指南)
8. [注意事项与最佳实践](#注意事项与最佳实践)
9. [未来扩展](#未来扩展)

---

## 概述

本文档描述了基于 `immich_python_sdk` 的 Immich 集成实现，包括：

- **API 层** (`immich_api.py`): 封装单个 Immich API 调用
- **业务逻辑层** (`immich_logic.py`): 组合多个 API 调用实现复杂业务场景
- **功能插件** (`search_from_immich.py`): 提供自然语言搜索功能

### 核心功能

- ✅ 资产查询和管理（获取、上传、下载）
- ✅ 智能搜索（文本、人物、时间、地点等）
- ✅ 人物搜索和管理
- ✅ 缩略图批量下载
- ✅ 人脸识别和人物照片检索（规划中）

---

## 架构设计

### 分层架构

```
业务代码/Handler
    ↓
业务逻辑层 (immich_logic.py)
    ↓
API 层 (immich_api.py)
    ↓
SDK (immich_python_sdk)
    ↓
Immich 服务器
```

### 1. API 层 (`immich_api.py`)

**职责**: 封装单个 API 调用，提供基础的 API 访问能力

**特点**:

- ✅ 每个方法对应一个 Immich API 端点
- ✅ 处理 API 调用、错误处理、日志记录
- ✅ 不包含业务逻辑，保持职责单一
- ✅ 返回原始 API 响应数据（转换为字典）
- ✅ 使用 `immich_python_sdk` 官方 SDK，类型安全

**主要方法**:

- `get_asset(asset_id)` - 获取资产详情
- `search_smart(query, ...)` - 智能搜索
- `search_person(name, ...)` - 搜索人物
- `download_asset(asset_id)` - 下载原始文件
- `view_asset(asset_id, size)` - 下载缩略图/预览图
- `view_asset_with_info(asset_id, size)` - 下载缩略图并返回元信息
- `upload_asset(file_path, ...)` - 上传资产

### 2. 业务逻辑层 (`immich_logic.py`)

**职责**: 组合多个 API 调用，实现复杂的业务场景

**特点**:

- ✅ 依赖 API 层，不直接调用 SDK
- ✅ 实现业务逻辑，组合多个 API 调用
- ✅ 处理业务相关的数据转换和流程控制
- ✅ 提供高级功能接口

**主要方法**:

- `search_person_by_name(person_name)` - 通过人物名称搜索人物 ID 列表
- `search_and_download_thumbnails(...)` - 搜索资产并批量下载缩略图
- `batch_download_thumbnails(...)` - 批量下载指定资产的缩略图

### 3. 设计原则

#### 单一职责原则

- API 层：只负责 API 调用
- 业务逻辑层：只负责业务逻辑组合

#### 依赖倒置原则

- 业务逻辑层依赖 API 层的抽象（接口），而不是具体实现
- 便于测试和替换

#### 开闭原则

- API 层：对扩展开放（可以添加新 API 方法）
- 业务逻辑层：对扩展开放（可以添加新业务功能）

#### 关注点分离

- API 层关注：如何调用 API、错误处理、数据转换
- 业务逻辑层关注：业务流程、数据组合、业务规则

---

## API 层实现

### 初始化

```python
from core.utils.immich_api import ImmichAPI

config = {
    "api_url": "http://127.0.0.1:2283/api",
    "api_key": "your-api-key",
    "timeout": 30
}

immich_api = ImmichAPI(config)
```

### 核心方法

#### 1. 获取资产信息

```python
asset = await immich_api.get_asset(asset_id)
# 返回: Dict 包含资产的所有信息（id, type, people, faces, exifInfo等）
```

#### 2. 智能搜索

```python
from immich_python_sdk.models.asset_visibility import AssetVisibility
from datetime import datetime

results = await immich_api.search_smart(
    query="travel by bike",
    page=1,
    size=10,
    with_exif=True,
    language="zh-CN",
    person_ids=["person-id-1"],
    taken_after=datetime(2012, 1, 18),
    taken_before=datetime(2025, 12, 17),
    visibility=AssetVisibility.TIMELINE,
    city="Dawsonville"
)
# 返回: Dict 包含 assets 和 albums 搜索结果
```

#### 3. 搜索人物

```python
persons = await immich_api.search_person(name="Jason", with_hidden=False)
# 返回: List[Dict] 人物列表，每个包含 id, name, thumbnailPath 等
```

#### 4. 下载原始文件

```python
asset_data = await immich_api.download_asset(asset_id)
# 返回: bytes 原始文件的二进制数据
```

#### 5. 下载缩略图/预览图

```python
from immich_python_sdk.models.asset_media_size import AssetMediaSize

# 下载缩略图
thumbnail_data = await immich_api.view_asset(
    asset_id,
    size=AssetMediaSize.THUMBNAIL
)

# 下载预览图
preview_data = await immich_api.view_asset(
    asset_id,
    size=AssetMediaSize.PREVIEW
)

# 下载完整大小（可能经过格式转换）
fullsize_data = await immich_api.view_asset(
    asset_id,
    size=AssetMediaSize.FULLSIZE
)

# 获取缩略图并包含元信息（推荐）
response_info = await immich_api.view_asset_with_info(
    asset_id,
    size=AssetMediaSize.THUMBNAIL
)
# 返回: Dict 包含 data (bytes), content_type, headers
```

**注意**: `view_asset_with_info` 方法会返回 `Content-Type` 信息，便于正确保存文件扩展名。

#### 6. 上传资产

```python
from immich_python_sdk.models.asset_visibility import AssetVisibility

result = await immich_api.upload_asset(
    file_path="/path/to/image.jpg",
    is_favorite=False,
    visibility=AssetVisibility.TIMELINE
)
# 返回: Dict 包含 id, duplicate, status 等信息
```

### 图片格式检测

API 层提供了 `_detect_image_format()` 函数，用于检测图片格式：

```python
from core.utils.immich_api import _detect_image_format

# 通过 Content-Type 检测
extension = _detect_image_format(image_data, content_type="image/webp")
# 返回: '.webp'

# 通过文件魔数检测
extension = _detect_image_format(image_data)
# 返回: '.jpg', '.png', '.webp' 等
```

支持的格式：`.webp`, `.jpg`, `.png`, `.gif`, `.bmp`, `.tiff`

### 异步处理

API 层使用 `ThreadPoolExecutor` 将同步的 SDK 调用转换为异步操作：

```python
async def _run_sync(self, func: Callable, *args, **kwargs):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(self.executor, partial(func, *args, **kwargs))
```

---

## 业务逻辑层实现

### 初始化

```python
from core.utils.immich_api import ImmichAPI
from core.utils.immich_logic import ImmichLogic

immich_api = ImmichAPI(config)
immich_logic = ImmichLogic(immich_api)
```

### 核心方法

#### 1. 通过人物名称搜索人物 ID

```python
person_ids = await immich_logic.search_person_by_name(
    person_name="Jason",
    timeout=5.0
)
# 返回: List[str] 人物ID列表，如果未找到返回 None
```

**业务逻辑**:

- 调用 API 层的 `search_person` 获取完整人物信息
- 提取人物 ID 列表
- 提供超时保护（默认 5 秒）

#### 2. 搜索并下载缩略图

```python
from immich_python_sdk.models.asset_media_size import AssetMediaSize

result = await immich_logic.search_and_download_thumbnails(
    query="travel by bike",
    save_dir="./thumbnails",
    thumbnail_size=AssetMediaSize.THUMBNAIL,
    max_count=10,
    person_name="Jason",  # 可选：人物名称
    page=1,
    size=10,
    # ... 其他搜索参数
)
# 返回: Dict 包含:
#   - success: bool
#   - total_found: int
#   - downloaded: int
#   - failed: int
#   - saved_files: List[str]
#   - errors: List[str]
```

**业务逻辑流程**:

1. 如果提供了 `person_name`，先调用 `search_person_by_name` 获取人物 ID
2. 将人物 ID 添加到搜索参数中，调用 `search_smart`
3. 遍历搜索结果中的资产，批量下载缩略图
4. 使用 `view_asset_with_info` 获取图片数据和格式信息
5. 使用 `_detect_image_format` 检测正确的文件扩展名
6. 保存文件到指定目录

**文件命名规则**:

- 格式: `{asset_id}_{thumbnail_size}.{extension}`
- 例如: `714f6b35-9f62-44f7-bc83-b8f29baf1296_THUMBNAIL.webp`

#### 3. 批量下载缩略图

```python
asset_ids = ["asset-id-1", "asset-id-2", "asset-id-3"]
result = await immich_logic.batch_download_thumbnails(
    asset_ids=asset_ids,
    save_dir="./thumbnails",
    thumbnail_size=AssetMediaSize.THUMBNAIL
)
# 返回: Dict 包含下载统计和文件列表
```

---

## 人脸识别功能实现

### 功能需求

**输入**: 一张照片  
**输出**:

1. 照片中所有识别到的人物名称
2. 每个人物对应的 10 张相关照片

### 实现流程（4 个步骤）

#### Step 1: 上传照片

```python
result = await immich_api.upload_asset(file_path)
asset_id = result['id']
```

**API**: `POST /api/asset/upload`  
**返回**: `asset_id`

#### Step 2: 等待处理

Immich 会自动进行人脸检测和识别，需要等待处理完成。

```python
# 轮询策略
max_retries = 20
wait_seconds = 3

for i in range(max_retries):
    asset = await immich_api.get_asset(asset_id)

    # 检查是否已处理完成（有 faces 或 people 数据）
    if asset.get('faces') or asset.get('people'):
        break  # 处理完成

    await asyncio.sleep(wait_seconds)
```

**处理时间估算**:

- 小照片（< 1MB）：5-10 秒
- 中等照片（1-5MB）：10-30 秒
- 大照片（> 5MB）：30 秒 - 几分钟

#### Step 3: 获取人物信息

```python
asset = await immich_api.get_asset(asset_id)
people = asset.get('people', [])
# people 包含: [{id, name, thumbnailPath}, ...]
```

**API**: `GET /api/asset/{asset_id}`  
**返回**: `people[]` 数组，每个人物包含 `id`, `name`

#### Step 4: 获取人物照片

```python
# 对每个人物，获取其照片
for person in people:
    person_id = person['id']
    # 调用 API 获取该人物的照片（需要实现）
    # GET /api/person/{person_id}/assets?size=10
```

**API**: `GET /api/person/{id}/assets`  
**参数**: `size=10` (限制返回 10 张)  
**返回**: 该人物的照片列表

### 完整流程图

```
开始：输入照片
    ↓
Step 1: 上传照片到 Immich
    ↓
Step 2: 等待 Immich 处理照片（轮询）
    ↓
Step 3: 获取资产详情（包含人物信息）
    ↓
判断：照片中是否有人物？
    ├─ 否 → 返回空结果
    └─ 是 → 遍历每个人物
            ↓
        Step 4: 获取人物的照片
            ↓
        构建返回结果
            ↓
        返回最终结果
```

### 返回数据格式

```json
{
  "asset_id": "asset-123",
  "people": [
    {
      "person_id": "person-1",
      "person_name": "张三",
      "photos": [
        {
          "id": "asset-1",
          "originalPath": "/path/to/photo1.jpg",
          "thumbnailPath": "/path/to/thumb1.jpg"
        }
        // ... 最多 10 张
      ]
    }
  ]
}
```

### 注意事项

1. **人物可能未命名**: Immich 默认不会自动命名人物，可能显示为 "Person 1", "Person 2"，需要在 Immich 界面手动命名
2. **处理需要时间**: 需要等待 Immich 完成人脸识别
3. **识别准确性**: 取决于照片质量、光线等因素
4. **同一人物可能被识别为多个**: 需要在 Immich 中手动合并

---

## 使用示例

### 场景 1: 直接使用 API 层（简单操作）

```python
from core.utils.immich_api import ImmichAPI
from immich_python_sdk.models.asset_media_size import AssetMediaSize

# 初始化
config = load_config()
immich_api = ImmichAPI(config.get("Immich", {}))

# 获取资产信息
asset = await immich_api.get_asset("asset-id-123")

# 下载缩略图
thumbnail = await immich_api.view_asset(
    "asset-id-123",
    size=AssetMediaSize.THUMBNAIL
)
```

### 场景 2: 使用业务逻辑层（复杂业务）

```python
from core.utils.immich_api import ImmichAPI
from core.utils.immich_logic import ImmichLogic
from immich_python_sdk.models.asset_media_size import AssetMediaSize

# 初始化
config = load_config()
immich_api = ImmichAPI(config.get("Immich", {}))
immich_logic = ImmichLogic(immich_api)

# 搜索并下载缩略图
result = await immich_logic.search_and_download_thumbnails(
    query="travel by bike",
    save_dir="./thumbnails",
    thumbnail_size=AssetMediaSize.THUMBNAIL,
    max_count=10,
    person_name="Jason"
)

# result 包含:
# - success: 是否成功
# - total_found: 找到的资产总数
# - downloaded: 成功下载的数量
# - saved_files: 保存的文件路径列表
# - errors: 错误列表
```

### 场景 3: 在插件中使用（同步环境）

```python
from core.utils.immich_api import ImmichAPI
from core.utils.immich_logic import ImmichLogic
from immich_python_sdk.models.asset_media_size import AssetMediaSize
import threading
import asyncio

# 在同步函数中调用异步代码
def search_from_immich(conn, person_name=None, description=None):
    config = conn.config.get("Immich", {})
    immich_api = ImmichAPI(config)
    immich_logic = ImmichLogic(immich_api)

    # 在新线程中运行异步代码
    result_container = {}
    event = threading.Event()

    def run_in_new_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result = new_loop.run_until_complete(
                asyncio.wait_for(
                    immich_logic.search_and_download_thumbnails(
                        query=description or "",
                        save_dir="./thumbnails",
                        person_name=person_name
                    ),
                    timeout=30
                )
            )
            result_container["result"] = result
        except Exception as e:
            result_container["exception"] = e
        finally:
            new_loop.close()
            event.set()

    thread = threading.Thread(target=run_in_new_thread, daemon=True)
    thread.start()
    event.wait(timeout=40)

    if "exception" in result_container:
        raise result_container["exception"]

    return result_container.get("result")
```

---

## 测试指南

### 测试脚本

使用 `test_immich_api.py` 进行测试：

```bash
# 测试下载缩略图（默认）
python test_immich_api.py

# 测试获取资产信息
python test_immich_api.py <asset_id>

# 测试智能搜索
python test_immich_api.py search

# 测试下载原始文件
python test_immich_api.py download <asset_id>

# 测试下载缩略图
python test_immich_api.py view <asset_id>

# 测试上传资产
python test_immich_api.py upload <file_path>

# 测试业务逻辑（搜索并下载）
python test_immich_api.py logic

# 测试搜索人物
python test_immich_api.py person "Jason"

# 运行所有下载测试
python test_immich_api.py all <asset_id>
```

### 测试用例示例

#### 1. 测试获取资产信息

```python
asset_id = "c5114ccc-1166-4dfc-9b20-34068ebef508"
asset = await immich_api.get_asset(asset_id)
```

#### 2. 测试智能搜索

```python
results = await immich_api.search_smart(
    query="travel by bike",
    page=1,
    with_exif=True,
    is_visible=True,
    language="zh-CN",
    person_ids=["8e4f5acf-aaf2-408b-b0b1-16ebfcc8ce96"],
    taken_after=datetime.fromisoformat("2012-01-18T00:00:00.000Z".replace('Z', '+00:00')),
    taken_before=datetime.fromisoformat("2025-12-17T23:59:59.999Z".replace('Z', '+00:00'))
)
```

#### 3. 测试搜索人物

```python
persons = await immich_api.search_person(name="Jason")
person_ids = await immich_logic.search_person_by_name("Jason")
```

#### 4. 测试下载功能

```python
# 下载原始文件
asset_data = await immich_api.download_asset("asset-id")

# 下载缩略图（带格式检测）
response_info = await immich_api.view_asset_with_info(
    "asset-id",
    size=AssetMediaSize.THUMBNAIL
)
```

#### 5. 测试业务逻辑

```python
result = await immich_logic.search_and_download_thumbnails(
    query="travel by bike",
    save_dir="./thumbnails",
    max_count=10,
    person_name="Jason"
)
```

---

## 注意事项与最佳实践

### 1. 配置管理

配置文件位置: `main/xiaozhi-server/data/.config.yaml`

```yaml
Immich:
  api_url: "http://127.0.0.1:2283/api"
  api_key: "your-api-key"
  timeout: 30
```

### 2. 错误处理

- API 层会自动处理 `ApiException` 并记录日志
- 业务逻辑层会捕获异常并返回错误信息
- 建议在使用时检查返回值是否为 `None`

### 3. 异步处理

- API 层使用 `ThreadPoolExecutor` 处理同步 SDK 调用
- 业务逻辑层完全异步，可以并发执行多个操作
- 在同步环境中调用异步代码时，使用新线程和新事件循环

### 4. 文件格式检测

- 使用 `view_asset_with_info` 获取 `Content-Type` 信息
- 使用 `_detect_image_format` 检测正确的文件扩展名
- 不要依赖原始文件名，因为 Immich 可能返回不同格式的图片（如 WEBP）

### 5. 超时设置

- API 层默认超时：30 秒
- 人物搜索超时：5 秒（可配置）
- 业务逻辑操作超时：30 秒（可配置）

### 6. 性能优化

- **批量操作**: 使用 `batch_download_thumbnails` 批量下载
- **并发控制**: API 层使用线程池（默认 5 个工作线程）
- **缓存策略**: 可以缓存已查询的人物信息，避免重复查询

### 7. 日志记录

所有操作都会记录日志，使用 `setup_logging()` 配置日志系统：

```python
from config.logger import setup_logging
logger = setup_logging()
logger.bind(tag="immich_api").info("操作信息")
```

### 8. 人物名称到 ID 转换

- 使用 `search_person_by_name` 将人物名称转换为 ID
- 如果未找到人物 ID，会自动将人物名称添加到查询字符串中
- 建议在 Immich 界面中为人物命名，提高搜索准确性

---

## 未来扩展

### API 层可以添加的功能

1. **人物管理**

   - `get_person(person_id)` - 获取人物详情
   - `get_person_assets(person_id, size=10)` - 获取人物的照片
   - `update_person(person_id, name)` - 更新人物名称

2. **相册管理**

   - `create_album(name, description)` - 创建相册
   - `add_assets_to_album(album_id, asset_ids)` - 添加资产到相册
   - `get_album(album_id)` - 获取相册信息

3. **人脸识别**
   - `wait_for_face_recognition(asset_id, timeout=60)` - 等待人脸识别完成
   - `recognize_faces_in_photo(file_path)` - 完整的人脸识别流程

### 业务逻辑层可以添加的功能

1. **图片搜索服务**

   - `search_images_by_person(person_name)` - 根据人物搜索图片
   - `search_images_by_location(city, country)` - 根据地点搜索图片
   - `search_images_by_time_range(start_date, end_date)` - 根据时间范围搜索图片

2. **批量处理服务**

   - `batch_upload_images(file_paths)` - 批量上传图片
   - `batch_update_metadata(asset_ids, metadata)` - 批量更新元数据
   - `batch_add_to_album(asset_ids, album_id)` - 批量添加到相册

3. **缓存和优化**

   - `get_cached_thumbnail(asset_id)` - 获取缓存的缩略图
   - `prefetch_thumbnails(asset_ids)` - 预加载缩略图

4. **Web 展示服务**
   - `get_gallery_data(query, page, size)` - 获取画廊数据（用于前端展示）
   - `get_image_grid(asset_ids)` - 获取图片网格数据

### 人脸识别功能实现计划

1. ✅ 上传照片功能（已实现）
2. ⏳ 等待处理完成功能（需要实现轮询逻辑）
3. ⏳ 获取人物照片功能（需要实现 `get_person_assets` API）
4. ⏳ 完整的人脸识别流程封装（需要实现 `recognize_faces_in_photo` 方法）

---

## 参考资源

- [Immich API 文档](https://immich.app/docs/api)
- [Immich GitHub](https://github.com/immich-app/immich)
- [Immich 官方文档](https://immich.app/docs)
- [immich_python_sdk](https://github.com/immich-app/immich-python-sdk)

---

## 更新日志

### 2024-12-XX

- ✅ 实现 API 层基础功能（获取资产、搜索、下载、上传）
- ✅ 实现业务逻辑层（搜索并下载缩略图、人物搜索）
- ✅ 实现图片格式自动检测
- ✅ 实现人物名称到 ID 转换
- ✅ 添加测试脚本和测试用例
- ✅ 优化代码结构，移除重复检查逻辑

---

## 总结

本文档描述了基于 `immich_python_sdk` 的 Immich 集成实现，采用分层架构设计：

- **API 层**: 封装单个 API 调用，提供类型安全的接口
- **业务逻辑层**: 组合多个 API 调用，实现复杂业务场景
- **功能插件**: 提供自然语言搜索等高级功能

通过这种架构设计，代码结构清晰、易于维护和扩展，同时保持了良好的性能和可测试性。
