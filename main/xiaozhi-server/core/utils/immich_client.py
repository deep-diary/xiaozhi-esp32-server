import asyncio
import aiohttp
from io import BytesIO
from typing import Optional, Dict, List
from datetime import datetime
import uuid
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ImmichClient:
    """Immich API客户端，用于上传图片并识别人物"""
    
    def __init__(self, config: dict):
        """
        初始化Immich客户端
        
        Args:
            config: Immich配置字典，包含:
                - api_url: Immich API地址 (例如: http://127.0.0.1:2283/api)
                - api_key: API密钥
                - email: 登录邮箱（可选，用于获取Bearer token）
                - password: 登录密码（可选，用于获取Bearer token）
                - max_retries: 最大重试次数，默认20
                - wait_seconds: 轮询等待时间（秒），默认3
                - timeout: 请求超时时间（秒），默认30
        """
        self.api_url = config.get("api_url", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.email = config.get("email", "")
        self.password = config.get("password", "")
        self.max_retries = int(config.get("max_retries", 20))
        self.wait_seconds = int(config.get("wait_seconds", 3))
        self.timeout = aiohttp.ClientTimeout(total=int(config.get("timeout", 30)))
        self.access_token = None
        
        # 检查配置
        if not self.api_url:
            self.enabled = False
            logger.bind(tag=TAG).warning("Immich API URL未配置，人脸识别功能将被禁用")
        elif not self.api_key and (not self.email or not self.password):
            self.enabled = False
            logger.bind(tag=TAG).warning("Immich认证信息不完整（需要api_key或email+password），人脸识别功能将被禁用")
        else:
            self.enabled = True
            logger.bind(tag=TAG).info(f"Immich客户端已初始化: API={self.api_url}")
    
    async def _get_headers(self) -> dict:
        """获取API请求头，优先使用Bearer token"""
        # 如果有access_token，优先使用Bearer token
        if self.access_token:
            return {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
        # 否则使用x-api-key
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
    
    async def _ensure_authenticated(self):
        """确保已认证，如果需要则登录获取token"""
        if self.access_token:
            return
        
        # 如果有email和password，尝试登录获取token
        if self.email and self.password:
            try:
                login_url = f"{self.api_url}/auth/login"
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        login_url,
                        json={"email": self.email, "password": self.password},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200 or response.status == 201:
                            result = await response.json()
                            self.access_token = result.get("accessToken")
                            if self.access_token:
                                logger.bind(tag=TAG).info("已通过登录获取Bearer token")
            except Exception as e:
                logger.bind(tag=TAG).warning(f"登录获取token失败，将使用api_key: {e}")
    
    async def upload_asset(self, image_data: bytes) -> Optional[str]:
        """
        上传图片到Immich
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            资产ID，如果上传失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich未启用，跳过上传")
            return None
        
        try:
            # 确保已认证
            await self._ensure_authenticated()
            
            # 根据官方文档，正确的端点是 /api/assets
            url = f"{self.api_url}/assets"
            headers = await self._get_headers()
            
            # 生成必需的参数
            device_asset_id = str(uuid.uuid4())
            device_id = "xiaozhi-esp32-server"
            now = datetime.utcnow()
            # 格式化为ISO 8601格式，带Z后缀
            file_created_at = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            file_modified_at = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # 准备multipart/form-data数据
            data = aiohttp.FormData()
            data.add_field(
                'assetData',
                BytesIO(image_data),
                filename='image.jpg',
                content_type='image/jpeg'
            )
            # 添加必需参数（根据官方API文档）
            data.add_field('deviceAssetId', device_asset_id)
            data.add_field('deviceId', device_id)
            data.add_field('fileCreatedAt', file_created_at)
            data.add_field('fileModifiedAt', file_modified_at)
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        asset_id = result.get("id")
                        status = result.get("status", "unknown")
                        if asset_id:
                            logger.bind(tag=TAG).info(
                                f"图片上传成功，资产ID: {asset_id}, 状态: {status}"
                            )
                            return asset_id
                        else:
                            logger.bind(tag=TAG).error(f"上传响应中未找到资产ID: {result}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.bind(tag=TAG).error(
                            f"图片上传失败: HTTP {response.status}, {error_text}"
                        )
                        return None
                        
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error("图片上传超时")
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"图片上传异常: {e}")
            return None
    
    async def get_asset(self, asset_id: str) -> Optional[Dict]:
        """
        获取资产详情
        
        Args:
            asset_id: 资产ID
            
        Returns:
            资产详情字典，如果获取失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            await self._ensure_authenticated()
            # 根据官方文档，正确的端点是 /api/assets/{id}
            url = f"{self.api_url}/assets/{asset_id}"
            headers = await self._get_headers()
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.bind(tag=TAG).warning(
                            f"获取资产详情失败: HTTP {response.status}, {error_text}"
                        )
                        return None
                        
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取资产详情异常: {e}")
            return None
    
    async def wait_for_processing(
        self, 
        asset_id: str, 
        max_retries: Optional[int] = None,
        wait_seconds: Optional[int] = None
    ) -> bool:
        """
        等待资产处理完成（人脸检测和识别）
        
        Args:
            asset_id: 资产ID
            max_retries: 最大重试次数，默认使用初始化时的值
            wait_seconds: 轮询等待时间（秒），默认使用初始化时的值
            
        Returns:
            是否处理完成
        """
        if not self.enabled:
            return False
        
        max_retries = max_retries or self.max_retries
        wait_seconds = wait_seconds or self.wait_seconds
        
        for i in range(max_retries):
            asset = await self.get_asset(asset_id)
            if not asset:
                await asyncio.sleep(wait_seconds)
                continue
            
            # 检查是否已处理完成（有faces或people数据）
            faces = asset.get("faces", [])
            people = asset.get("people", [])
            
            if faces or people:
                logger.bind(tag=TAG).info(
                    f"资产处理完成 (第{i+1}次检查): faces={len(faces)}, people={len(people)}"
                )
                return True
            
            if i < max_retries - 1:  # 最后一次不需要等待
                await asyncio.sleep(wait_seconds)
        
        logger.bind(tag=TAG).warning(
            f"资产处理超时，已重试{max_retries}次: {asset_id}"
        )
        return False
    
    async def get_person_photos(
        self, 
        person_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        获取人物的相关照片
        
        Args:
            person_id: 人物ID
            limit: 返回照片数量限制，默认10
            
        Returns:
            照片列表
        """
        if not self.enabled:
            return []
        
        try:
            await self._ensure_authenticated()
            # 根据官方文档，正确的端点是 /api/people/{id}/assets
            url = f"{self.api_url}/people/{person_id}/assets"
            headers = await self._get_headers()
            params = {"size": limit}
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        # 返回items数组，如果没有items字段则返回空数组
                        return result.get("items", [])
                    else:
                        error_text = await response.text()
                        logger.bind(tag=TAG).warning(
                            f"获取人物照片失败: HTTP {response.status}, {error_text}"
                        )
                        return []
                        
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取人物照片异常: {e}")
            return []
    
    async def upload_and_recognize_people(
        self, 
        image_data: bytes
    ) -> Dict:
        """
        完整流程：上传图片并识别人物
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            包含以下字段的字典:
            {
                "success": bool,  # 是否成功
                "asset_id": str,   # 资产ID
                "people": [        # 人物列表
                    {
                        "person_id": str,      # 人物ID
                        "person_name": str,    # 人物名称
                        "photos": [            # 相关照片列表
                            {
                                "id": str,
                                "originalPath": str,
                                "thumbnailPath": str,
                                ...
                            }
                        ]
                    }
                ],
                "message": str     # 消息（成功或错误信息）
            }
        """
        if not self.enabled:
            return {
                "success": False,
                "asset_id": None,
                "people": [],
                "message": "Immich未启用"
            }
        
        # 1. 上传图片
        asset_id = await self.upload_asset(image_data)
        if not asset_id:
            return {
                "success": False,
                "asset_id": None,
                "people": [],
                "message": "图片上传失败"
            }
        
        # 2. 等待处理完成
        processing_complete = await self.wait_for_processing(asset_id)
        if not processing_complete:
            logger.bind(tag=TAG).warning(
                f"资产处理超时，但继续尝试获取人物信息: {asset_id}"
            )
        
        # 3. 获取资产详情
        asset = await self.get_asset(asset_id)
        if not asset:
            return {
                "success": False,
                "asset_id": asset_id,
                "people": [],
                "message": "无法获取资产详情"
            }
        
        # 4. 提取人物信息
        people_list = asset.get("people", [])
        
        if not people_list:
            return {
                "success": True,
                "asset_id": asset_id,
                "people": [],
                "message": "未检测到人物"
            }
        
        # 5. 获取每个人物的相关照片（如果API可用）
        result_people = []
        for person in people_list:
            person_id = person.get("id")
            person_name = person.get("name", "未命名")
            
            if not person_id:
                continue
            
            # 尝试获取该人物的其他照片（如果API不可用，不影响主要功能）
            photos = []
            try:
                photos = await self.get_person_photos(person_id, limit=10)
            except Exception as e:
                logger.bind(tag=TAG).debug(f"获取人物照片失败（不影响主要功能）: {e}")
            
            result_people.append({
                "person_id": person_id,
                "person_name": person_name,
                "photos": photos
            })
        
        logger.bind(tag=TAG).info(
            f"识别完成: 资产ID={asset_id}, 人物数量={len(result_people)}"
        )
        
        return {
            "success": True,
            "asset_id": asset_id,
            "people": result_people,
            "message": f"成功识别{len(result_people)}个人物"
        }

