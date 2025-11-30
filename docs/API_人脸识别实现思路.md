# Immich API 人脸识别实现思路

## 📋 功能需求

**输入**：一张照片  
**输出**：
1. 照片中识别到的人物名称列表
2. 每个人物对应的 10 张相关照片

## 🔄 实现流程

### 阶段一：照片上传与人脸检测

```
用户上传照片
    ↓
调用 Immich API 上传照片
    ↓
Immich 自动进行人脸检测和识别
    ↓
等待处理完成（可能需要几秒到几分钟）
```

### 阶段二：获取照片中的人物信息

```
查询上传照片的详细信息
    ↓
提取照片中识别到的人物 ID 列表
    ↓
根据人物 ID 获取人物名称
```

### 阶段三：获取人物的其他照片

```
遍历每个人物 ID
    ↓
查询该人物的所有照片
    ↓
返回前 10 张照片
```

## 🔌 Immich API 端点梳理

### 1. 上传照片

**端点**: `POST /api/asset/upload`

**请求方式**: `multipart/form-data`

**参数**:
- `assetData`: 照片文件（二进制）
- `deviceAssetId`: 设备资产 ID（可选，用于去重）
- `deviceId`: 设备 ID（可选）
- `fileCreatedAt`: 文件创建时间（可选）
- `fileModifiedAt`: 文件修改时间（可选）

**响应示例**:
```json
{
  "id": "asset-id-123",
  "duplicate": false,
  "status": "SUCCESS"
}
```

**注意事项**:
- 上传后需要等待 Immich 处理（人脸检测、特征提取）
- 可以通过轮询资产状态来确认处理完成

---

### 2. 获取资产详情（包含人物信息）

**端点**: `GET /api/asset/{id}`

**响应示例**:
```json
{
  "id": "asset-id-123",
  "type": "IMAGE",
  "originalPath": "/path/to/image.jpg",
  "resizedPath": "/path/to/resized.jpg",
  "people": [
    {
      "id": "person-id-1",
      "name": "张三",
      "thumbnailPath": "/path/to/thumbnail.jpg"
    },
    {
      "id": "person-id-2",
      "name": "李四",
      "thumbnailPath": "/path/to/thumbnail2.jpg"
    }
  ],
  "faces": [
    {
      "id": "face-id-1",
      "personId": "person-id-1",
      "imageHeight": 2000,
      "imageWidth": 3000,
      "boundingBoxX1": 100,
      "boundingBoxY1": 200,
      "boundingBoxX2": 500,
      "boundingBoxY2": 600
    }
  ]
}
```

**关键字段**:
- `people`: 照片中识别到的人物列表
- `faces`: 检测到的人脸信息（包含位置和关联的人物）

---

### 3. 获取人物列表

**端点**: `GET /api/person`

**查询参数**:
- `withHidden`: 是否包含隐藏的人物（默认 false）

**响应示例**:
```json
{
  "people": [
    {
      "id": "person-id-1",
      "name": "张三",
      "thumbnailPath": "/path/to/thumbnail.jpg",
      "faceCount": 15,
      "isHidden": false
    },
    {
      "id": "person-id-2",
      "name": "李四",
      "thumbnailPath": "/path/to/thumbnail2.jpg",
      "faceCount": 8,
      "isHidden": false
    }
  ],
  "total": 2
}
```

---

### 4. 获取特定人物信息

**端点**: `GET /api/person/{id}`

**响应示例**:
```json
{
  "id": "person-id-1",
  "name": "张三",
  "thumbnailPath": "/path/to/thumbnail.jpg",
  "faceCount": 15,
  "isHidden": false,
  "birthDate": "1990-01-01"
}
```

---

### 5. 获取人物的所有照片

**端点**: `GET /api/person/{id}/assets`

**查询参数**:
- `page`: 页码（默认 1）
- `size`: 每页数量（默认 10）

**响应示例**:
```json
{
  "items": [
    {
      "id": "asset-id-1",
      "type": "IMAGE",
      "originalPath": "/path/to/image1.jpg",
      "thumbnailPath": "/path/to/thumb1.jpg",
      "createdAt": "2024-01-01T00:00:00Z"
    },
    {
      "id": "asset-id-2",
      "type": "IMAGE",
      "originalPath": "/path/to/image2.jpg",
      "thumbnailPath": "/path/to/thumb2.jpg",
      "createdAt": "2024-01-02T00:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "size": 10
}
```

---

### 6. 等待资产处理完成

**端点**: `GET /api/asset/{id}`

**轮询策略**:
1. 上传后立即查询资产状态
2. 检查 `faces` 字段是否已生成
3. 如果未完成，等待 2-5 秒后重试
4. 最多重试 10-20 次（根据照片大小调整）

**判断处理完成的标志**:
- `faces` 字段存在且不为空
- 或者 `people` 字段已填充

---

## 🛠️ 实现伪代码

```python
class ImmichFaceRecognition:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def upload_photo(self, photo_path):
        """上传照片到 Immich"""
        url = f"{self.api_url}/api/asset/upload"
        
        with open(photo_path, 'rb') as f:
            files = {'assetData': f}
            headers = {"x-api-key": self.api_key}
            response = requests.post(url, files=files, headers=headers)
        
        return response.json()['id']
    
    def wait_for_processing(self, asset_id, max_retries=20, wait_seconds=3):
        """等待资产处理完成"""
        for i in range(max_retries):
            asset = self.get_asset(asset_id)
            
            # 检查是否已处理完成（有 faces 或 people 数据）
            if asset.get('faces') or asset.get('people'):
                return True
            
            time.sleep(wait_seconds)
        
        return False
    
    def get_asset(self, asset_id):
        """获取资产详情"""
        url = f"{self.api_url}/api/asset/{asset_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_person_photos(self, person_id, limit=10):
        """获取人物的照片（限制数量）"""
        url = f"{self.api_url}/api/person/{person_id}/assets"
        params = {"size": limit}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()['items']
    
    def recognize_faces_in_photo(self, photo_path):
        """主函数：识别照片中的人物并返回相关信息"""
        # 1. 上传照片
        asset_id = self.upload_photo(photo_path)
        print(f"照片已上传，资产 ID: {asset_id}")
        
        # 2. 等待处理完成
        if not self.wait_for_processing(asset_id):
            raise Exception("照片处理超时")
        
        # 3. 获取资产详情
        asset = self.get_asset(asset_id)
        
        # 4. 提取人物信息
        people = asset.get('people', [])
        
        if not people:
            return {
                "message": "未检测到人物",
                "people": []
            }
        
        # 5. 获取每个人物的照片
        result = []
        for person in people:
            person_id = person['id']
            person_name = person.get('name', '未命名')
            
            # 获取该人物的其他照片
            photos = self.get_person_photos(person_id, limit=10)
            
            result.append({
                "person_id": person_id,
                "person_name": person_name,
                "photos": photos
            })
        
        return {
            "asset_id": asset_id,
            "people": result
        }
```

---

## 📝 完整实现步骤

### Step 1: 环境准备

1. **获取 Immich API Key**
   - 登录 Immich Web 界面
   - 进入设置 → API Keys
   - 创建新的 API Key

2. **确定 Immich 服务地址**
   - 本地部署：`http://localhost:2283`
   - 远程部署：`https://your-immich-domain.com`

### Step 2: 安装依赖

```bash
pip install requests
```

### Step 3: 实现核心功能

按照上面的伪代码实现各个函数。

### Step 4: 测试流程

1. 准备一张包含人物的测试照片
2. 调用 `recognize_faces_in_photo()` 函数
3. 验证返回结果

---

## ⚠️ 注意事项

### 1. 处理时间

- **小照片**（< 1MB）：通常 5-10 秒
- **中等照片**（1-5MB）：通常 10-30 秒
- **大照片**（> 5MB）：可能需要 30 秒到几分钟

### 2. 人物命名

- Immich 默认不会自动给人物命名
- 人物可能显示为 "Person 1", "Person 2" 等
- 需要用户手动在 Immich 界面中为人物命名
- 或者通过 API 更新人物名称：`PUT /api/person/{id}`

### 3. 人脸识别准确性

- 取决于照片质量、光线、角度等因素
- 同一人物在不同照片中可能被识别为不同人物（需要手动合并）
- 建议在 Immich 界面中定期检查和合并人物

### 4. API 认证

- 所有 API 请求都需要在 Header 中包含 `x-api-key`
- 确保 API Key 有足够的权限

### 5. 错误处理

- 网络错误：实现重试机制
- 处理超时：增加重试次数或调整等待时间
- 未识别到人物：返回友好的提示信息

---

## 🔍 扩展功能

### 1. 批量处理

可以扩展为批量上传多张照片，识别所有照片中的人物。

### 2. 人物合并

如果发现同一人物被识别为多个，可以调用合并 API：
- `PUT /api/person/{id}` - 更新人物信息
- 可能需要手动在 Immich 界面中合并

### 3. 缓存机制

- 缓存已识别的人物信息
- 避免重复查询相同的人物

### 4. 异步处理

- 对于大量照片，使用异步队列处理
- 提供回调接口通知处理完成

---

## 📚 参考资源

- [Immich API 文档](https://immich.app/docs/api)
- [Immich GitHub](https://github.com/immich-app/immich)
- [Immich 官方文档](https://immich.app/docs)

---

## 🎯 下一步实现

1. ✅ 创建 API 客户端类
2. ✅ 实现照片上传功能
3. ✅ 实现等待处理完成的功能
4. ✅ 实现获取人物信息的功能
5. ✅ 实现获取人物照片的功能
6. ✅ 整合所有功能到主函数
7. ✅ 添加错误处理和日志记录
8. ✅ 编写测试用例

