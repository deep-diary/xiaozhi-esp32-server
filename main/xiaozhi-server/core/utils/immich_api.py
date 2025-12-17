"""
基于 immich_python_sdk 的 Immich API 客户端

这个模块提供了基于官方 Python SDK 的 Immich API 客户端实现。
相比原生请求实现，这个实现更加规范和类型安全。
"""

from typing import Optional, Dict, Callable, Union, List
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from datetime import datetime
import hashlib
import uuid
import re

from immich_python_sdk import Configuration, ApiClient
from immich_python_sdk.exceptions import ApiException
from immich_python_sdk.models.asset_response_dto import AssetResponseDto
from immich_python_sdk.models.smart_search_dto import SmartSearchDto
from immich_python_sdk.models.random_search_dto import RandomSearchDto
from immich_python_sdk.models.asset_media_size import AssetMediaSize
from immich_python_sdk.models.asset_media_response_dto import AssetMediaResponseDto
from immich_python_sdk.models.asset_visibility import AssetVisibility
from immich_python_sdk.api.assets_api import AssetsApi
from immich_python_sdk.api.search_api import SearchApi
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def _detect_image_format(data: bytes, content_type: Optional[str] = None) -> str:
    """
    检测图片格式
    
    Args:
        data: 图片二进制数据
        content_type: HTTP Content-Type 头（可选）
    
    Returns:
        文件扩展名（包含点号），例如: '.jpg', '.webp', '.png'
    """
    # 优先使用 Content-Type
    if content_type:
        # 解析 Content-Type，例如: "image/webp", "image/jpeg"
        content_type_lower = content_type.lower()
        if 'webp' in content_type_lower:
            return '.webp'
        elif 'jpeg' in content_type_lower or 'jpg' in content_type_lower:
            return '.jpg'
        elif 'png' in content_type_lower:
            return '.png'
        elif 'gif' in content_type_lower:
            return '.gif'
        elif 'bmp' in content_type_lower:
            return '.bmp'
        elif 'tiff' in content_type_lower:
            return '.tiff'
    
    # 如果没有 Content-Type，通过文件魔数检测
    if len(data) < 12:
        return '.jpg'  # 默认返回 jpg
    
    # WEBP: RIFF....WEBP
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    # JPEG: FF D8 FF
    elif data[:3] == b'\xff\xd8\xff':
        return '.jpg'
    # PNG: 89 50 4E 47
    elif data[:4] == b'\x89PNG':
        return '.png'
    # GIF: GIF87a 或 GIF89a
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return '.gif'
    # BMP: BM
    elif data[:2] == b'BM':
        return '.bmp'
    # TIFF: II* 或 MM*
    elif data[:4] in (b'II*\x00', b'MM\x00*'):
        return '.tiff'
    
    # 默认返回 jpg
    return '.jpg'


class ImmichAPI:
    """基于 immich_python_sdk 的 Immich API 客户端"""
    
    def __init__(self, config: dict):
        """
        初始化 Immich API 客户端
        
        Args:
            config: Immich配置字典，包含:
                - api_url: Immich API地址 (例如: http://127.0.0.1:2283/api)
                - api_key: API密钥
                - timeout: 请求超时时间（秒），默认30
        """
        self.api_url = config.get("api_url", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.timeout = int(config.get("timeout", 30))
        
        # 检查配置
        if not self.api_url:
            self.enabled = False
            logger.bind(tag=TAG).warning("Immich API URL未配置，Immich API功能将被禁用")
        elif not self.api_key:
            self.enabled = False
            logger.bind(tag=TAG).warning("Immich API密钥未配置，Immich API功能将被禁用")
        else:
            self.enabled = True
            # 初始化 SDK 配置
            self._init_sdk()
            logger.bind(tag=TAG).info(f"Immich API客户端已初始化: API={self.api_url}")
    
    def _init_sdk(self):
        """初始化 SDK 配置和客户端"""
        # 创建配置对象
        self.configuration = Configuration(
            host=self.api_url,
            api_key={"api_key": self.api_key}
        )
        
        # 创建 API 客户端
        self.api_client = ApiClient(self.configuration)
        
        # 初始化各个 API 实例
        self.assets_api = AssetsApi(self.api_client)
        self.search_api = SearchApi(self.api_client)
        
        # 创建线程池用于执行同步 SDK 调用
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def _run_sync(self, func: Callable, *args, **kwargs):
        """
        在事件循环中运行同步函数
        
        Args:
            func: 要执行的同步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        loop = asyncio.get_event_loop()
        # 使用 functools.partial 包装函数调用，确保关键字参数正确传递
        wrapped_func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(self.executor, wrapped_func)
    
    async def get_asset(self, asset_id: str) -> Optional[Dict]:
        """
        获取资产详情
        
        Args:
            asset_id: 资产ID
            
        Returns:
            资产详情字典，如果获取失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法获取资产信息")
            return None
        
        if not asset_id:
            logger.bind(tag=TAG).warning("资产ID为空，无法获取资产信息")
            return None
        
        try:
            # 使用 SDK 的 get_asset_info 方法
            asset_dto = await self._run_sync(
                self.assets_api.get_asset_info,
                id=asset_id
            )
            
            # AssetResponseDto 对象有 to_dict 方法，直接转换为字典
            if asset_dto:
                result = asset_dto.to_dict()
                logger.bind(tag=TAG).debug(f"成功获取资产详情: {asset_id}")
                return result
            
            logger.bind(tag=TAG).warning(f"获取资产详情返回空结果: {asset_id}")
            return None
            
        except ApiException as e:
            if e.status == 404:
                logger.bind(tag=TAG).warning(f"资产不存在: {asset_id}")
            else:
                logger.bind(tag=TAG).error(
                    f"获取资产详情失败 (API异常): HTTP {e.status}, {e.reason}"
                )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取资产详情异常: {e}", exc_info=True)
            return None
    
    async def search_person(
        self,
        name: str,
        with_hidden: Optional[bool] = None,
        return_ids: bool = True,
        timeout: Optional[float] = None
    ) -> Union[Optional[List[Dict]], Optional[List[str]]]:
        """
        通过人物名称搜索人物
        
        Args:
            name: 人物名称
            with_hidden: 是否包含隐藏的人物，默认None
            return_ids: 是否只返回人物ID列表，默认False（返回完整人物信息）
            timeout: 搜索超时时间（秒），默认None（无超时）。当return_ids=True时建议设置超时
            
        Returns:
            如果 return_ids=False: 人物列表（字典格式），每个字典包含 id, name 等信息
            如果 return_ids=True: 人物ID列表（字符串列表）
            如果搜索失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法搜索人物")
            return None
        
        if not name:
            logger.bind(tag=TAG).warning("人物名称为空，无法搜索人物")
            return None
        
        try:
            # 使用 SDK 的 search_person 方法
            search_func = self._run_sync(
                self.search_api.search_person,
                name=name,
                with_hidden=with_hidden
            )
            
            # 如果设置了超时，添加超时保护
            if timeout is not None:
                search_func = asyncio.wait_for(search_func, timeout=timeout)
            
            persons = await search_func
            
            if persons:
                # 将 PersonResponseDto 对象列表转换为字典列表
                result = [person.to_dict() for person in persons]
                
                if return_ids:
                    # 提取人物ID列表
                    person_ids = [person.get('id') for person in result if person.get('id')]
                    if person_ids:
                        person_names = [p.get('name', 'N/A') for p in result]
                        logger.bind(tag=TAG).info(
                            f"成功搜索人物ID: name='{name}', 找到 {len(person_ids)} 个人物ID: {person_ids}, 人物名称: {person_names}"
                        )
                        return person_ids
                    else:
                        logger.bind(tag=TAG).warning(f"未找到有效的人物ID: name='{name}'")
                        return None
                else:
                    logger.bind(tag=TAG).info(f"成功搜索人物: name='{name}', 找到 {len(result)} 个人物")
                    return result
            
            logger.bind(tag=TAG).warning(f"搜索人物返回空结果: name='{name}'")
            return None
            
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).warning(f"搜索人物超时（{timeout}秒）: name='{name}'")
            return None
        except ApiException as e:
            logger.bind(tag=TAG).error(
                f"搜索人物失败 (API异常): HTTP {e.status}, {e.reason}, name='{name}'"
            )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"搜索人物异常: {e}, name='{name}'", exc_info=True)
            return None
    
    async def search_smart(
        self,
        query: str,
        page: Optional[int] = None,
        size: Optional[int] = None,
        **kwargs
    ) -> Optional[Dict]:
        """
        智能搜索资产
        
        Args:
            query: 搜索查询字符串（必需）
            page: 页码，从1开始，默认None
            size: 每页数量，1-1000，默认None
            **kwargs: 其他可选搜索参数:
                - city: 城市名称
                - country: 国家名称
                - state: 州/省名称
                - person_ids: 人物ID列表
                - tag_ids: 标签ID列表
                - is_favorite: 是否收藏
                - is_archived: 是否归档
                - is_offline: 是否离线
                - type: 资产类型 (IMAGE/VIDEO)
                - make: 相机品牌
                - model: 相机型号
                - lens_model: 镜头型号
                - library_id: 库ID
                - device_id: 设备ID
                - is_encoded: 是否已编码
                - is_motion: 是否动态照片
                - is_not_in_album: 是否不在相册中
                - language: 语言
                - rating: 评分 (-1到5)
                - visibility: 可见性
                - with_deleted: 是否包含已删除
                - with_exif: 是否包含EXIF信息
                - created_after: 创建时间之后 (datetime)
                - created_before: 创建时间之前 (datetime)
                - taken_after: 拍摄时间之后 (datetime)
                - taken_before: 拍摄时间之前 (datetime)
                - updated_after: 更新时间之后 (datetime)
                - updated_before: 更新时间之前 (datetime)
                - trashed_after: 删除时间之后 (datetime)
                - trashed_before: 删除时间之前 (datetime)
        
        Returns:
            搜索结果字典，包含 assets 和 albums，如果搜索失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法执行搜索")
            return None
        
        if not query:
            logger.bind(tag=TAG).warning("搜索查询字符串为空，无法执行搜索")
            return None
        
        try:
            logger.bind(tag=TAG).info(
                f"[immich_api] 构建搜索参数: query='{query}', page={page}, size={size}, "
                f"kwargs={kwargs}"
            )
            # 构建 SmartSearchDto 对象
            search_dto = SmartSearchDto(
                query=query,
                page=page,
                size=size,
                **kwargs
            )
            
            logger.bind(tag=TAG).info(f"[immich_api] 调用 SDK search_api.search_smart 开始...")
            api_start_time = time.time()
            # 使用 SDK 的 search_smart 方法
            search_result = await self._run_sync(
                self.search_api.search_smart,
                smart_search_dto=search_dto
            )
            api_duration = time.time() - api_start_time
            logger.bind(tag=TAG).info(f"[immich_api] SDK search_api.search_smart 完成，耗时: {api_duration:.2f}秒")
            
            # SearchResponseDto 对象有 to_dict 方法，直接转换为字典
            if search_result:
                result = search_result.to_dict()
                assets_count = len(result.get('assets', {}).get('items', [])) if result.get('assets') else 0
                albums_count = len(result.get('albums', {}).get('items', [])) if result.get('albums') else 0
                logger.bind(tag=TAG).info(
                    f"智能搜索完成: query='{query}', 找到 {assets_count} 个资产, {albums_count} 个相册"
                )
                return result
            
            logger.bind(tag=TAG).warning(f"智能搜索返回空结果: query='{query}'")
            return None
            
        except ApiException as e:
            logger.bind(tag=TAG).error(
                f"智能搜索失败 (API异常): HTTP {e.status}, {e.reason}"
            )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"智能搜索异常: {e}", exc_info=True)
            return None
    
    async def search_random(
        self,
        size: Optional[int] = None,
        **kwargs
    ) -> Optional[List[Dict]]:
        """
        随机搜索资产
        
        根据指定的筛选条件随机返回资产列表。与 search_smart 的区别：
        - search_smart: 基于文本查询的智能搜索，返回分页结果
        - search_random: 随机搜索，不基于文本查询，返回资产列表
        
        Args:
            size: 返回的资产数量，1-1000，默认None（使用服务器默认值）
            **kwargs: 可选搜索参数:
                - city: 城市名称
                - country: 国家名称
                - state: 州/省名称
                - person_ids: 人物ID列表
                - tag_ids: 标签ID列表
                - is_favorite: 是否收藏
                - is_archived: 是否归档（注意：RandomSearchDto 中没有此字段，使用 is_offline 等）
                - is_offline: 是否离线
                - type: 资产类型 (IMAGE/VIDEO)
                - make: 相机品牌
                - model: 相机型号
                - lens_model: 镜头型号
                - library_id: 库ID
                - device_id: 设备ID
                - is_encoded: 是否已编码
                - is_motion: 是否动态照片
                - is_not_in_album: 是否不在相册中
                - rating: 评分 (-1到5)
                - visibility: 可见性
                - with_deleted: 是否包含已删除
                - with_exif: 是否包含EXIF信息
                - with_people: 是否包含人物
                - with_stacked: 是否包含堆叠资产
                - created_after: 创建时间之后 (datetime)
                - created_before: 创建时间之前 (datetime)
                - taken_after: 拍摄时间之后 (datetime)
                - taken_before: 拍摄时间之前 (datetime)
                - updated_after: 更新时间之后 (datetime)
                - updated_before: 更新时间之前 (datetime)
                - trashed_after: 删除时间之后 (datetime)
                - trashed_before: 删除时间之前 (datetime)
        
        Returns:
            资产列表（字典格式），如果搜索失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法执行随机搜索")
            return None
        
        try:
            logger.bind(tag=TAG).info(
                f"[immich_api] 构建随机搜索参数: size={size}, kwargs={kwargs}"
            )
            # 构建 RandomSearchDto 对象
            random_search_dto = RandomSearchDto(
                size=size,
                **kwargs
            )
            
            logger.bind(tag=TAG).info(f"[immich_api] 调用 SDK search_api.search_random 开始...")
            api_start_time = time.time()
            # 使用 SDK 的 search_random 方法
            search_result = await self._run_sync(
                self.search_api.search_random,
                random_search_dto=random_search_dto
            )
            api_duration = time.time() - api_start_time
            logger.bind(tag=TAG).info(f"[immich_api] SDK search_api.search_random 完成，耗时: {api_duration:.2f}秒")
            
            # search_random 返回 List[AssetResponseDto]，转换为字典列表
            if search_result:
                # 确保返回的是列表类型
                if not isinstance(search_result, list):
                    logger.bind(tag=TAG).error(
                        f"search_random SDK 返回了非列表类型: {type(search_result)}, 值: {search_result}"
                    )
                    return None
                
                result = [asset.to_dict() for asset in search_result]
                logger.bind(tag=TAG).info(
                    f"随机搜索完成: 找到 {len(result)} 个资产"
                )
                return result
            
            logger.bind(tag=TAG).warning("随机搜索返回空结果")
            return None
            
        except ApiException as e:
            logger.bind(tag=TAG).error(
                f"随机搜索失败 (API异常): HTTP {e.status}, {e.reason}"
            )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"随机搜索异常: {e}", exc_info=True)
            return None
    
    async def download_asset(
        self,
        asset_id: str,
        key: Optional[str] = None
    ) -> Optional[bytes]:
        """
        下载资产的原始文件（未经处理的原始文件）
        
        注意：此方法返回的是服务器上存储的完全原始文件，与用户上传时完全一致。
        与 view_asset(size=FULLSIZE) 的区别：
        - download_asset: 返回原始文件，格式、大小、元数据完全不变
        - view_asset(size=FULLSIZE): 返回完整大小的图片，但可能经过格式转换（如统一转换为JPEG）或优化处理
        
        Args:
            asset_id: 资产ID
            key: 可选的共享密钥（用于访问共享资产）
            
        Returns:
            资产的二进制数据（bytes），如果下载失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法下载资产")
            return None
        
        if not asset_id:
            logger.bind(tag=TAG).warning("资产ID为空，无法下载资产")
            return None
        
        try:
            # 使用 SDK 的 download_asset 方法下载原始文件
            asset_data = await self._run_sync(
                self.assets_api.download_asset,
                id=asset_id,
                key=key
            )
            
            if asset_data:
                logger.bind(tag=TAG).info(f"成功下载资产原始文件: {asset_id}, 大小: {len(asset_data)} 字节")
                return bytes(asset_data)
            
            logger.bind(tag=TAG).warning(f"下载资产返回空数据: {asset_id}")
            return None
            
        except ApiException as e:
            if e.status == 404:
                logger.bind(tag=TAG).warning(f"资产不存在: {asset_id}")
            else:
                logger.bind(tag=TAG).error(
                    f"下载资产失败 (API异常): HTTP {e.status}, {e.reason}"
                )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"下载资产异常: {e}", exc_info=True)
            return None
    
    async def view_asset(
        self,
        asset_id: str,
        size: Optional[AssetMediaSize] = None,
        key: Optional[str] = None
    ) -> Optional[bytes]:
        """
        下载资产的缩略图或预览图（经过处理的图片）
        
        注意：此方法返回的图片可能经过格式转换或优化处理。
        与 download_asset 的区别：
        - download_asset: 返回原始文件，格式、大小、元数据完全不变
        - view_asset(size=FULLSIZE): 返回完整大小的图片，但可能经过格式转换（如统一转换为JPEG）或优化处理
        
        Args:
            asset_id: 资产ID
            size: 图片尺寸，可选值:
                - AssetMediaSize.THUMBNAIL: 缩略图（最小）
                - AssetMediaSize.PREVIEW: 预览图（中等）
                - AssetMediaSize.FULLSIZE: 完整大小（最大，但可能经过格式转换）
                如果为None，则返回默认缩略图
            key: 可选的共享密钥（用于访问共享资产）
            
        Returns:
            图片的二进制数据（bytes），如果下载失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法查看资产")
            return None
        
        if not asset_id:
            logger.bind(tag=TAG).warning("资产ID为空，无法查看资产")
            return None
        
        try:
            # 使用 SDK 的 view_asset 方法下载缩略图
            image_data = await self._run_sync(
                self.assets_api.view_asset,
                id=asset_id,
                size=size,
                key=key
            )
            
            if image_data:
                size_str = size.value if size else "默认"
                logger.bind(tag=TAG).info(
                    f"成功下载资产缩略图: {asset_id}, 尺寸: {size_str}, 大小: {len(image_data)} 字节"
                )
                return bytes(image_data)
            
            logger.bind(tag=TAG).warning(f"下载资产缩略图返回空数据: {asset_id}")
            return None
            
        except ApiException as e:
            if e.status == 404:
                logger.bind(tag=TAG).warning(f"资产不存在: {asset_id}")
            else:
                logger.bind(tag=TAG).error(
                    f"下载资产缩略图失败 (API异常): HTTP {e.status}, {e.reason}"
                )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"下载资产缩略图异常: {e}", exc_info=True)
            return None
    
    async def view_asset_with_info(
        self,
        asset_id: str,
        size: Optional[AssetMediaSize] = None,
        key: Optional[str] = None
    ) -> Optional[Dict]:
        """
        下载资产的缩略图或预览图，并返回响应信息（包括Content-Type）
        
        这个方法返回字典，包含图片数据和响应头信息，用于确定实际的文件格式。
        
        Args:
            asset_id: 资产ID
            size: 图片尺寸，可选值:
                - AssetMediaSize.THUMBNAIL: 缩略图（最小）
                - AssetMediaSize.PREVIEW: 预览图（中等）
                - AssetMediaSize.FULLSIZE: 完整大小（最大）
                如果为None，则返回默认缩略图
            key: 可选的共享密钥（用于访问共享资产）
            
        Returns:
            包含以下字段的字典:
            - data: 图片的二进制数据（bytes）
            - content_type: Content-Type 响应头
            - headers: 所有响应头
            如果下载失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法查看资产")
            return None
        
        if not asset_id:
            logger.bind(tag=TAG).warning("资产ID为空，无法查看资产")
            return None
        
        try:
            # 使用 SDK 的 view_asset_with_http_info 方法获取响应信息
            from immich_python_sdk.api_response import ApiResponse
            
            api_response: ApiResponse[bytearray] = await self._run_sync(
                self.assets_api.view_asset_with_http_info,
                id=asset_id,
                size=size,
                key=key
            )
            
            if api_response and api_response.data:
                image_data = bytes(api_response.data)
                headers = api_response.headers or {}
                content_type = headers.get('content-type', '')
                
                size_str = size.value if size else "默认"
                logger.bind(tag=TAG).info(
                    f"成功下载资产缩略图: {asset_id}, 尺寸: {size_str}, "
                    f"大小: {len(image_data)} 字节, Content-Type: {content_type}"
                )
                
                return {
                    "data": image_data,
                    "content_type": content_type,
                    "headers": headers
                }
            
            logger.bind(tag=TAG).warning(f"下载资产缩略图返回空数据: {asset_id}")
            return None
            
        except ApiException as e:
            if e.status == 404:
                logger.bind(tag=TAG).warning(f"资产不存在: {asset_id}")
            else:
                logger.bind(tag=TAG).error(
                    f"下载资产缩略图失败 (API异常): HTTP {e.status}, {e.reason}"
                )
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"下载资产缩略图异常: {e}", exc_info=True)
            return None
    
    async def upload_asset(
        self,
        file_path: Union[str, bytes],
        device_id: Optional[str] = None,
        device_asset_id: Optional[str] = None,
        file_created_at: Optional[datetime] = None,
        file_modified_at: Optional[datetime] = None,
        is_favorite: Optional[bool] = None,
        visibility: Optional[AssetVisibility] = None,
        x_immich_checksum: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict]:
        """
        上传资产（图片或视频）到 Immich 服务器
        
        Args:
            file_path: 文件路径（str）或文件数据（bytes）
            device_id: 设备ID，如果为None则自动生成UUID
            device_asset_id: 设备资产ID，如果为None则使用文件名或自动生成
            file_created_at: 文件创建时间，如果为None则使用当前时间
            file_modified_at: 文件修改时间，如果为None则使用当前时间
            is_favorite: 是否收藏
            visibility: 资产可见性（AssetVisibility枚举）
            x_immich_checksum: SHA1校验和（用于重复检测），如果为None则自动计算
            **kwargs: 其他可选参数:
                - key: 共享密钥
                - duration: 持续时间（视频）
                - live_photo_video_id: Live Photo视频ID
                - sidecar_data: 侧车数据
        
        Returns:
            上传结果字典（包含资产ID等信息），如果上传失败返回None
        """
        if not self.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法上传资产")
            return None
        
        try:
            # 读取文件数据
            if isinstance(file_path, str):
                with open(file_path, 'rb') as f:
                    asset_data = f.read()
                # 从文件路径获取文件名作为device_asset_id（如果未提供）
                if device_asset_id is None:
                    import os
                    device_asset_id = os.path.basename(file_path)
            elif isinstance(file_path, bytes):
                asset_data = file_path
                if device_asset_id is None:
                    device_asset_id = f"upload_{uuid.uuid4().hex[:8]}"
            else:
                logger.bind(tag=TAG).error("file_path必须是文件路径（str）或文件数据（bytes）")
                return None
            
            if not asset_data:
                logger.bind(tag=TAG).error("文件数据为空，无法上传")
                return None
            
            # 生成设备ID（如果未提供）
            if device_id is None:
                device_id = str(uuid.uuid4())
            
            # 设置文件时间（如果未提供）
            now = datetime.now()
            if file_created_at is None:
                file_created_at = now
            if file_modified_at is None:
                file_modified_at = now
            
            # 计算SHA1校验和（如果未提供）
            if x_immich_checksum is None:
                x_immich_checksum = hashlib.sha1(asset_data).hexdigest()
            
            # 准备上传参数
            upload_params = {
                'asset_data': asset_data,
                'device_asset_id': device_asset_id,
                'device_id': device_id,
                'file_created_at': file_created_at,
                'file_modified_at': file_modified_at,
            }
            
            # 添加可选参数
            if is_favorite is not None:
                upload_params['is_favorite'] = is_favorite
            if visibility is not None:
                upload_params['visibility'] = visibility
            if x_immich_checksum:
                upload_params['x_immich_checksum'] = x_immich_checksum
            
            # 添加其他kwargs参数
            upload_params.update(kwargs)
            
            # 使用 SDK 的 upload_asset 方法上传文件
            upload_result = await self._run_sync(
                self.assets_api.upload_asset,
                **upload_params
            )
            
            if upload_result:
                result = upload_result.to_dict()
                asset_id = result.get('id', 'N/A')
                file_size = len(asset_data)
                logger.bind(tag=TAG).info(
                    f"成功上传资产: ID={asset_id}, 大小={file_size:,} 字节 ({file_size / 1024 / 1024:.2f} MB)"
                )
                return result
            
            logger.bind(tag=TAG).warning("上传资产返回空结果")
            return None
            
        except ApiException as e:
            logger.bind(tag=TAG).error(
                f"上传资产失败 (API异常): HTTP {e.status}, {e.reason}"
            )
            if e.status == 409:
                logger.bind(tag=TAG).warning("资产已存在（可能是重复上传）")
            return None
        except FileNotFoundError as e:
            logger.bind(tag=TAG).error(f"文件不存在: {e}")
            return None
        except Exception as e:
            logger.bind(tag=TAG).error(f"上传资产异常: {e}", exc_info=True)
            return None
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

