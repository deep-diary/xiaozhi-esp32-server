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
    
    async def search_person_by_name(
        self,
        person_name: str,
        timeout: float = 5.0
    ) -> Optional[List[str]]:
        """
        通过人物名称搜索人物ID列表
        
        业务场景：用户提供人物名称，需要先搜索获取人物ID，然后用于资产搜索
        
        Args:
            person_name: 人物名称
            timeout: 搜索超时时间（秒），默认5秒
        
        Returns:
            人物ID列表，如果搜索失败或未找到返回None
        """
        try:
            logger.bind(tag=TAG).info(f"[immich_logic] 通过人物名称搜索人物ID: person_name='{person_name}'")
            # 直接调用API层，API层已经做了enabled和name的检查
            # 添加超时保护
            persons = await asyncio.wait_for(
                self.api.search_person(name=person_name),
                timeout=timeout
            )
            
            if persons and len(persons) > 0:
                # 提取人物ID列表（业务逻辑：从完整人物信息中提取ID）
                person_ids = [person.get('id') for person in persons if person.get('id')]
                if person_ids:
                    person_names = [p.get('name', 'N/A') for p in persons]
                    logger.bind(tag=TAG).info(
                        f"[immich_logic] 找到人物ID: {person_ids}, 人物名称: {person_names}"
                    )
                    return person_ids
                else:
                    logger.bind(tag=TAG).warning(f"[immich_logic] 未找到有效的人物ID")
                    return None
            else:
                logger.bind(tag=TAG).warning(f"[immich_logic] 未找到名为 '{person_name}' 的人物")
                return None
                
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).warning(f"[immich_logic] 搜索人物ID超时（{timeout}秒）")
            return None
        except Exception as e:
            # API层的异常会被传播到这里，这里只处理超时异常
            logger.bind(tag=TAG).error(f"[immich_logic] 搜索人物ID异常: {e}", exc_info=True)
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
                person_ids = await self.search_person_by_name(person_name)
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

