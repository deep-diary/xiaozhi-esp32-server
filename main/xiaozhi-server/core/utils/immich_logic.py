"""
Immich 业务逻辑层

这个模块提供基于 ImmichAPI 的业务逻辑功能，组合多个 API 调用来实现复杂的业务场景。
例如：搜索资产并下载缩略图、批量处理资产等。

架构说明：
- immich_api.py: API 层，封装单个 API 调用
- immich_logic.py: 业务逻辑层，组合多个 API 调用实现业务功能
"""

from typing import Optional, Dict, List, Union
from pathlib import Path
import asyncio
import time
from datetime import datetime

from immich_python_sdk.models.asset_media_size import AssetMediaSize
from core.utils.immich_api import ImmichAPI, _detect_image_format
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ImmichLogic:
    """
    Immich 业务逻辑处理类
    
    提供高级业务功能，组合多个 API 调用来实现复杂的业务场景。
    """
    
    def __init__(self, immich_api: ImmichAPI):
        """
        初始化业务逻辑处理器
        
        Args:
            immich_api: ImmichAPI 实例，用于调用底层 API
        """
        self.api = immich_api
        if not self.api.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，业务逻辑功能将被禁用")
    
    async def search_random_by_person(
        self,
        person_name: str,
        size: int = 10,
        **kwargs
    ) -> Optional[List[Dict]]:
        """
        根据人物姓名和数量进行随机搜索，返回资产列表
        
        业务场景：用户提供人物名称，随机获取该人物的一些照片，用于前端展示
        
        Args:
            person_name: 人物名称
            size: 返回的资产数量，默认10
            **kwargs: 其他搜索参数（传递给 search_random）
        
        Returns:
            资产列表（字典格式），如果搜索失败返回None
        """
        if not self.api.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法执行随机搜索")
            return None
        
        try:
            # 先搜索人物ID
            person_ids = await self.api.search_person(name=person_name, return_ids=True, timeout=5.0)
            
            if not person_ids:
                logger.bind(tag=TAG).warning(f"[immich_logic] 未找到名为 '{person_name}' 的人物")
                return None
            
            logger.bind(tag=TAG).info(f"[immich_logic] 找到人物ID: {person_ids}，开始随机搜索资产")
            
            # 使用人物ID进行随机搜索
            search_kwargs = {
                "person_ids": person_ids,
                "size": size,
                **kwargs
            }
            
            assets = await self.api.search_random(**search_kwargs)
            
            # 确保返回的是列表类型
            if assets is not None:
                if not isinstance(assets, list):
                    logger.bind(tag=TAG).error(f"[immich_logic] search_random 返回了非列表类型: {type(assets)}, 值: {assets}")
                    return None
                if len(assets) > 0:
                    logger.bind(tag=TAG).info(f"[immich_logic] 随机搜索完成: 找到 {len(assets)} 个资产")
                    return assets
                else:
                    logger.bind(tag=TAG).warning(f"[immich_logic] 随机搜索未找到资产")
                    return None
            else:
                logger.bind(tag=TAG).warning(f"[immich_logic] 随机搜索返回 None")
                return None
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"[immich_logic] 随机搜索异常: {e}", exc_info=True)
            return None
    
    async def search_smart_assets(
        self,
        query: str = "",
        person_name: Optional[str] = None,
        city: Optional[str] = None,
        date: Optional[tuple] = None,
        size: Optional[int] = None,
        **kwargs
    ) -> Optional[List[Dict]]:
        """
        根据时间、地点、人物、描述、数量进行智能检索，返回资产列表
        
        业务场景：根据多个条件智能搜索资产，返回资产列表供前端展示
        
        Args:
            query: 搜索查询字符串（描述）
            person_name: 人物名称（可选）
            city: 城市名称（可选）
            date: 日期范围元组 (taken_after, taken_before)，可选
            size: 每页数量，默认None（使用服务器默认值）
            **kwargs: 其他搜索参数（传递给 search_smart）
        
        Returns:
            资产列表（字典格式），如果搜索失败返回None
        """
        if not self.api.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法执行智能搜索")
            return None
        
        try:
            # 准备搜索参数
            search_kwargs = {}
            
            # 处理人物名称
            if person_name:
                person_ids = await self.api.search_person(name=person_name, return_ids=True, timeout=5.0)
                if person_ids:
                    search_kwargs["person_ids"] = person_ids
                    logger.bind(tag=TAG).info(f"[immich_logic] 使用人物ID进行搜索: {person_ids}")
                else:
                    # 如果未找到人物ID，将人物名称添加到查询字符串中
                    if query:
                        query = f"{query} {person_name}"
                    else:
                        query = person_name
            
            # 处理城市
            if city:
                search_kwargs["city"] = city
            
            # 处理日期范围
            if date:
                taken_after, taken_before = date
                if taken_after:
                    search_kwargs["taken_after"] = taken_after
                if taken_before:
                    search_kwargs["taken_before"] = taken_before
            
            # 如果没有查询字符串，使用默认值
            if not query:
                query = "photo"
            
            # 添加其他参数
            search_kwargs.update(kwargs)
            
            logger.bind(tag=TAG).info(
                f"[immich_logic] 开始智能搜索: query='{query}', "
                f"size={size}, search_kwargs={search_kwargs}"
            )
            
            # 执行智能搜索
            search_result = await self.api.search_smart(query=query, size=size, **search_kwargs)
            
            if not search_result:
                logger.bind(tag=TAG).warning("[immich_logic] 智能搜索未返回结果")
                return None
            
            # 提取资产列表
            assets_data = search_result.get('assets', {})
            assets_items = assets_data.get('items', [])
            
            # 确保返回的是列表类型
            if assets_items:
                if not isinstance(assets_items, list):
                    logger.bind(tag=TAG).error(f"[immich_logic] search_smart 返回的 items 不是列表类型: {type(assets_items)}, 值: {assets_items}")
                    return None
                logger.bind(tag=TAG).info(f"[immich_logic] 智能搜索完成: 找到 {len(assets_items)} 个资产")
                return assets_items
            else:
                logger.bind(tag=TAG).warning("[immich_logic] 智能搜索未找到资产")
                return None
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"[immich_logic] 智能搜索异常: {e}", exc_info=True)
            return None
    
    async def search_and_download_thumbnails(
        self,
        query: str,
        save_dir: Union[str, Path],
        thumbnail_size: AssetMediaSize = AssetMediaSize.THUMBNAIL,
        max_count: Optional[int] = None,
        person_name: Optional[str] = None,
        **search_kwargs
    ) -> Dict[str, any]:
        """
        搜索资产并下载缩略图到本地
        
        业务场景：根据搜索条件查找相关资产，然后将缩略图下载到本地用于web显示
        
        Args:
            query: 搜索查询字符串
            save_dir: 保存目录路径（str 或 Path）
            thumbnail_size: 缩略图尺寸，默认 THUMBNAIL
            max_count: 最大下载数量，None 表示下载所有结果
            person_name: 人物名称（可选），如果提供会先搜索人物ID，然后添加到搜索参数中
            **search_kwargs: 其他搜索参数（传递给 search_smart）
        
        Returns:
            包含以下字段的字典:
            - success: 是否成功
            - total_found: 找到的资产总数
            - downloaded: 成功下载的数量
            - failed: 下载失败的数量
            - saved_files: 保存的文件路径列表
            - errors: 错误信息列表
        """
        if not self.api.enabled:
            logger.bind(tag=TAG).warning("Immich API未启用，无法执行搜索和下载")
            return {
                "success": False,
                "total_found": 0,
                "downloaded": 0,
                "failed": 0,
                "saved_files": [],
                "errors": ["Immich API未启用"]
            }
        
        # 确保保存目录存在
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        result = {
            "success": False,
            "total_found": 0,
            "downloaded": 0,
            "failed": 0,
            "saved_files": [],
            "errors": []
        }
        
        try:
            # 步骤0: 如果提供了人物名称，先搜索人物ID
            if person_name:
                # 调用API层的方法获取人物ID
                person_ids = await self.api.search_person(name=person_name, return_ids=True, timeout=5.0)
                if person_ids:
                    # 将人物ID添加到搜索参数中
                    search_kwargs["person_ids"] = person_ids
                    logger.bind(tag=TAG).info(f"[immich_logic] 使用人物ID进行搜索: {person_ids}")
                else:
                    # 如果未找到人物ID，将人物名称添加到查询字符串中
                    logger.bind(tag=TAG).warning(f"[immich_logic] 未找到人物ID，将人物名称添加到查询字符串")
                    if query:
                        query = f"{query} {person_name}"
                    else:
                        query = person_name
            
            # 步骤1: 执行搜索
            logger.bind(tag=TAG).info(
                f"[immich_logic] 开始搜索资产: query='{query}', "
                f"max_count={max_count}, search_kwargs={search_kwargs}"
            )
            logger.bind(tag=TAG).info(f"[immich_logic] 调用 api.search_smart 开始...")
            search_start_time = time.time()
            search_result = await self.api.search_smart(query=query, **search_kwargs)
            search_duration = time.time() - search_start_time
            logger.bind(tag=TAG).info(f"[immich_logic] api.search_smart 完成，耗时: {search_duration:.2f}秒")
            
            if not search_result:
                logger.bind(tag=TAG).warning("[immich_logic] 搜索未返回结果")
                result["errors"].append("搜索未返回结果")
                return result
            
            # 提取资产列表
            assets_data = search_result.get('assets', {})
            assets_items = assets_data.get('items', [])
            total_found = assets_data.get('total', 0)
            
            result["total_found"] = total_found
            
            if not assets_items:
                logger.bind(tag=TAG).info("搜索未找到任何资产")
                result["success"] = True  # 搜索成功，只是没有结果
                return result
            
            # 限制下载数量
            if max_count:
                assets_items = assets_items[:max_count]
            
            logger.bind(tag=TAG).info(f"[immich_logic] 找到 {len(assets_items)} 个资产，准备下载缩略图...")
            
            # 步骤2: 批量下载缩略图
            download_tasks = []
            for idx, asset in enumerate(assets_items):
                asset_id = asset.get('id')
                if asset_id:
                    logger.bind(tag=TAG).debug(f"[immich_logic] 准备下载第 {idx+1}/{len(assets_items)} 个资产: {asset_id}")
                    download_tasks.append(
                        self._download_single_thumbnail(
                            asset_id=asset_id,
                            asset_info=asset,
                            save_dir=save_path,
                            thumbnail_size=thumbnail_size
                        )
                    )
            
            logger.bind(tag=TAG).info(f"[immich_logic] 开始并发下载 {len(download_tasks)} 个缩略图...")
            download_start_time = time.time()
            # 并发执行下载任务
            download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
            download_duration = time.time() - download_start_time
            logger.bind(tag=TAG).info(f"[immich_logic] 并发下载完成，耗时: {download_duration:.2f}秒")
            
            # 统计结果
            for download_result in download_results:
                if isinstance(download_result, Exception):
                    result["failed"] += 1
                    result["errors"].append(str(download_result))
                    logger.bind(tag=TAG).error(f"下载缩略图异常: {download_result}")
                elif download_result and download_result.get("success"):
                    result["downloaded"] += 1
                    result["saved_files"].append(download_result.get("file_path"))
                else:
                    result["failed"] += 1
                    if download_result:
                        result["errors"].append(download_result.get("error", "未知错误"))
            
            result["success"] = result["downloaded"] > 0
            
            logger.bind(tag=TAG).info(
                f"下载完成: 成功 {result['downloaded']} 个, "
                f"失败 {result['failed']} 个, "
                f"总计 {result['total_found']} 个"
            )
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"搜索和下载缩略图异常: {e}", exc_info=True)
            result["errors"].append(f"异常: {str(e)}")
        
        return result
    
    async def _download_single_thumbnail(
        self,
        asset_id: str,
        asset_info: Dict,
        save_dir: Path,
        thumbnail_size: AssetMediaSize
    ) -> Dict[str, any]:
        """
        下载单个资产的缩略图（内部辅助方法）
        
        Args:
            asset_id: 资产ID
            asset_info: 资产信息字典（用于获取文件名等信息）
            save_dir: 保存目录
            thumbnail_size: 缩略图尺寸
        
        Returns:
            包含 success、file_path、error 的字典
        """
        try:
            # 使用 view_asset_with_info 获取图片数据和 Content-Type
            response_info = await self.api.view_asset_with_info(
                asset_id=asset_id,
                size=thumbnail_size
            )
            
            if not response_info or not response_info.get('data'):
                return {
                    "success": False,
                    "file_path": None,
                    "error": f"下载失败: {asset_id}"
                }
            
            thumbnail_data = response_info['data']
            content_type = response_info.get('content_type', '')
            
            # 根据 Content-Type 或文件内容检测文件格式
            file_extension = _detect_image_format(thumbnail_data, content_type)
            
            # 生成保存文件名
            size_suffix = thumbnail_size.value if thumbnail_size else "default"
            save_filename = f"{asset_id}_{size_suffix}{file_extension}"
            save_path = save_dir / save_filename
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(thumbnail_data)
            
            logger.bind(tag=TAG).debug(
                f"成功下载缩略图: {asset_id} -> {save_path} (格式: {file_extension}, Content-Type: {content_type})"
            )
            
            return {
                "success": True,
                "file_path": str(save_path),
                "asset_id": asset_id,
                "file_size": len(thumbnail_data),
                "file_format": file_extension,
                "content_type": content_type
            }
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"下载缩略图失败 {asset_id}: {e}")
            return {
                "success": False,
                "file_path": None,
                "error": f"{asset_id}: {str(e)}"
            }
    
    async def batch_download_thumbnails(
        self,
        asset_ids: List[str],
        save_dir: Union[str, Path],
        thumbnail_size: AssetMediaSize = AssetMediaSize.THUMBNAIL
    ) -> Dict[str, any]:
        """
        批量下载指定资产的缩略图
        
        Args:
            asset_ids: 资产ID列表
            save_dir: 保存目录路径
            thumbnail_size: 缩略图尺寸
        
        Returns:
            包含下载结果的字典
        """
        if not self.api.enabled:
            return {
                "success": False,
                "downloaded": 0,
                "failed": 0,
                "saved_files": [],
                "errors": ["Immich API未启用"]
            }
        
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        result = {
            "success": False,
            "downloaded": 0,
            "failed": 0,
            "saved_files": [],
            "errors": []
        }
        
        # 获取资产信息并下载
        download_tasks = []
        for asset_id in asset_ids:
            # 先获取资产信息
            asset_info_task = self.api.get_asset(asset_id)
            download_tasks.append(
                self._download_with_info(
                    asset_id=asset_id,
                    asset_info_task=asset_info_task,
                    save_dir=save_path,
                    thumbnail_size=thumbnail_size
                )
            )
        
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        for download_result in download_results:
            if isinstance(download_result, Exception):
                result["failed"] += 1
                result["errors"].append(str(download_result))
            elif download_result and download_result.get("success"):
                result["downloaded"] += 1
                result["saved_files"].append(download_result.get("file_path"))
            else:
                result["failed"] += 1
                if download_result:
                    result["errors"].append(download_result.get("error", "未知错误"))
        
        result["success"] = result["downloaded"] > 0
        return result
    
    async def _download_with_info(
        self,
        asset_id: str,
        asset_info_task,
        save_dir: Path,
        thumbnail_size: AssetMediaSize
    ) -> Dict[str, any]:
        """下载缩略图（等待资产信息获取完成）"""
        try:
            asset_info = await asset_info_task
            if not asset_info:
                return {
                    "success": False,
                    "file_path": None,
                    "error": f"无法获取资产信息: {asset_id}"
                }
            
            return await self._download_single_thumbnail(
                asset_id=asset_id,
                asset_info=asset_info,
                save_dir=save_dir,
                thumbnail_size=thumbnail_size
            )
        except Exception as e:
            return {
                "success": False,
                "file_path": None,
                "error": f"{asset_id}: {str(e)}"
            }

