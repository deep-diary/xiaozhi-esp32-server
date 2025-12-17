"""
Immich 图片搜索功能插件

从 Immich 相册中搜索图片并下载缩略图到本地，用于web显示。
支持根据人名、城市、日期、文字描述等条件进行搜索。
"""

import asyncio
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.immich_api import ImmichAPI
from core.utils.immich_logic import ImmichLogic
from immich_python_sdk.models.asset_media_size import AssetMediaSize
from immich_python_sdk.models.asset_visibility import AssetVisibility

TAG = __name__
logger = setup_logging()

# 定义函数描述模板
SEARCH_FROM_IMMICH_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_immich",
        "description": (
            "从 Immich 相册中搜索图片并下载缩略图。"
            "可以根据人名、城市、日期、文字描述等条件搜索照片。"
            "搜索完成后会将缩略图下载到本地，用于web显示。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": (
                        "要搜索的人物名称（人名），例如：Json、张三、John、Mary等。"
                        "当用户提到人名时，必须提取并传入此参数。可选参数，如果不提供则不传"
                    ),
                },
                "city": {
                    "type": "string",
                    "description": "要搜索的城市名称（英文），例如：Beijing、Shanghai、New York等。可选参数，如果不提供则不传",
                },
                "date": {
                    "type": "string",
                    "description": "要搜索的日期，格式：YYYY-MM-DD 或 YYYY-MM-DD 到 YYYY-MM-DD（日期范围）。可选参数，如果不提供则不传",
                },
                "description": {
                    "type": "string",
                    "description": (
                        "英文文字描述，用于智能搜索照片。"
                        "必须将用户的中文描述翻译成英文后传入，例如：'骑自行车'翻译为'travel by bike'，'在海边'翻译为'beach'，'生日聚会'翻译为'birthday party'等。"
                        "可选参数，如果不提供则不传"
                    ),
                },
                "max_count": {
                    "type": "integer",
                    "description": "最大返回数量，默认5。可选参数",
                },
            },
            "required": [],
        },
    },
}


def _parse_date_range(date_str: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    解析日期字符串，支持单个日期或日期范围
    
    Args:
        date_str: 日期字符串，格式：YYYY-MM-DD 或 YYYY-MM-DD 到 YYYY-MM-DD
    
    Returns:
        (开始日期, 结束日期) 元组，如果是单个日期则结束日期为同一天
    """
    if not date_str:
        return None, None
    
    try:
        # 检查是否是日期范围
        if "到" in date_str or "-" in date_str and len(date_str.split()) > 1:
            # 处理日期范围，例如："2024-01-01 到 2024-12-31"
            parts = date_str.replace("到", "-").split("-")
            if len(parts) >= 2:
                start_str = parts[0].strip()
                end_str = parts[-1].strip()
                
                # 尝试解析日期
                try:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                    # 结束日期设置为当天的23:59:59
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    return start_date, end_date
                except ValueError:
                    pass
        
        # 单个日期
        date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        end_date = date.replace(hour=23, minute=59, second=59)
        return date, end_date
    
    except ValueError:
        logger.bind(tag=TAG).warning(f"日期格式解析失败: {date_str}")
        return None, None


@register_function(
    "search_from_immich", SEARCH_FROM_IMMICH_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def search_from_immich(
    conn,
    person_name: Optional[str] = None,
    city: Optional[str] = None,
    date: Optional[str] = None,
    description: Optional[str] = None,
    max_count: Optional[int] = None,
):
    """
    从 Immich 相册中搜索图片并下载缩略图
    
    Args:
        conn: 连接对象，包含配置信息
        person_name: 人物名称（可选）
        city: 城市名称（可选）
        date: 日期或日期范围，格式：YYYY-MM-DD 或 YYYY-MM-DD 到 YYYY-MM-DD（可选）
        description: 文字描述（可选）
        max_count: 最大返回数量，默认5（可选）
    
    Returns:
        ActionResponse: 包含搜索结果或错误信息
    """
    try:
        # 获取 Immich 配置
        immich_config = conn.config.get("Immich", {})
        if not immich_config:
            logger.bind(tag=TAG).error("Immich 配置未找到")
            return ActionResponse(
                Action.RESPONSE, None, "Immich 相册服务未配置，无法搜索图片"
            )
        
        # 检查配置是否启用
        api_url = immich_config.get("api_url", "")
        api_key = immich_config.get("api_key", "")
        
        if not api_url or not api_key:
            logger.bind(tag=TAG).error("Immich API 配置不完整")
            return ActionResponse(
                Action.RESPONSE, None, "Immich 相册服务配置不完整，无法搜索图片"
            )
        
        # 获取保存目录配置
        save_dir_config = conn.config.get("plugins", {}).get("search_from_immich", {}).get(
            "save_dir", "tmp/immich_thumbnails"
        )
        save_dir = Path(save_dir_config)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Immich API 和业务逻辑层
        immich_api = ImmichAPI(immich_config)
        if not immich_api.enabled:
            return ActionResponse(
                Action.RESPONSE, None, "Immich 相册服务未启用，无法搜索图片"
            )
        
        immich_logic = ImmichLogic(immich_api)
        
        # 构建搜索查询字符串
        query_parts = []
        
        # 处理文字描述：LLM应该已经返回英文，直接使用
        if description:
            # 检查是否还有中文，如果有则记录警告（LLM应该已经翻译了）
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', description))
            if has_chinese:
                logger.bind(tag=TAG).warning(
                    f"描述参数包含中文，LLM应该已经翻译成英文: '{description}'"
                )
            query_parts.append(description)
        
        # 如果没有提供任何搜索条件，返回提示
        if not query_parts and not person_name and not city and not date:
            return ActionResponse(
                Action.RESPONSE,
                None,
                "请提供至少一个搜索条件（人物名称、城市、日期或文字描述）",
            )
        
        # 组合查询字符串
        query = " ".join(query_parts) if query_parts else ""
        
        # 准备搜索参数
        search_kwargs = {}
        
        # 处理城市
        if city:
            search_kwargs["city"] = city
        
        # 处理日期范围
        if date:
            taken_after, taken_before = _parse_date_range(date)
            if taken_after:
                search_kwargs["taken_after"] = taken_after
            if taken_before:
                search_kwargs["taken_before"] = taken_before
        
        # 注意：人物名称的处理已经移到 immich_logic.search_and_download_thumbnails 中
        # 这里只需要传递 person_name 参数即可
        
        # 设置可见性为可见的资产
        search_kwargs["visibility"] = AssetVisibility.TIMELINE
        
        # 设置最大数量
        max_download_count = max_count or 5
        
        # 如果没有查询字符串，使用默认值
        if not query:
            query = "photo"
        
        logger.bind(tag=TAG).info(
            f"准备搜索 Immich 图片: query='{query}', "
            f"person_name={person_name}, city={city}, date={date}, max_count={max_download_count}, "
            f"search_kwargs={search_kwargs}"
        )
        
        # 在新线程中运行事件循环，避免与当前线程的事件循环冲突
        # 直接调用 immich_logic.search_and_download_thumbnails，不需要额外的包装函数
        try:
            timeout_seconds = 10  # 10秒超时
            
            # 用于存储结果的变量
            result_container = {"result": None, "exception": None}
            event = threading.Event()
            
            def run_in_new_thread():
                """在新线程中运行事件循环并执行异步搜索"""
                try:
                    logger.bind(tag=TAG).info("在新线程中创建事件循环并执行搜索")
                    # 在新线程中创建新的事件循环
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    try:
                        # 直接调用异步函数，带超时保护
                        # person_name 参数会由 immich_logic 内部处理（搜索人物ID）
                        result = new_loop.run_until_complete(
                            asyncio.wait_for(
                                immich_logic.search_and_download_thumbnails(
                                    query=query,
                                    save_dir=save_dir,
                                    thumbnail_size=AssetMediaSize.THUMBNAIL,
                                    max_count=max_download_count,
                                    person_name=person_name,  # 传递人物名称，由业务逻辑层处理
                                    **search_kwargs
                                ),
                                timeout=timeout_seconds
                            )
                        )
                        result_container["result"] = result
                        logger.bind(tag=TAG).info(f"搜索完成，获得结果: success={result.get('success') if result else None}")
                    except asyncio.TimeoutError:
                        logger.bind(tag=TAG).error(f"搜索超时（{timeout_seconds}秒）")
                        result_container["exception"] = TimeoutError(f"搜索超时（{timeout_seconds}秒）")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"搜索异常: {e}", exc_info=True)
                        result_container["exception"] = e
                    finally:
                        # 关闭新的事件循环
                        new_loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"线程执行异常: {e}", exc_info=True)
                    result_container["exception"] = e
                finally:
                    # 通知主线程任务完成
                    event.set()
            
            # 启动新线程
            thread = threading.Thread(target=run_in_new_thread, daemon=True)
            thread.start()
            logger.bind(tag=TAG).info("等待搜索任务完成...")
            
            # 等待任务完成（带超时保护，避免无限等待）
            if event.wait(timeout=timeout_seconds + 10):  # 多等待10秒作为缓冲
                # 检查是否有异常
                if result_container["exception"]:
                    if isinstance(result_container["exception"], TimeoutError):
                        return ActionResponse(
                            Action.RESPONSE,
                            None,
                            str(result_container["exception"])
                        )
                    else:
                        raise result_container["exception"]
                
                result = result_container["result"]
                logger.bind(tag=TAG).info(f"搜索任务完成: success={result.get('success') if result else None}")
            else:
                logger.bind(tag=TAG).error(f"等待搜索任务超时（{timeout_seconds + 10}秒）")
                return ActionResponse(
                    Action.RESPONSE,
                    None,
                    f"搜索超时（{timeout_seconds}秒），请检查网络连接或稍后重试"
                )
        except Exception as e:
            logger.bind(tag=TAG).error(f"执行搜索时发生错误: {e}", exc_info=True)
            # 检查是否是超时相关的错误
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                return ActionResponse(
                    Action.RESPONSE, 
                    None, 
                    "搜索超时，图片搜索可能需要较长时间，请稍后重试或减少搜索条件"
                )
            raise
        
        # 处理结果
        if result.get("success"):
            total_found = result.get("total_found", 0)
            downloaded = result.get("downloaded", 0)
            failed = result.get("failed", 0)
            saved_files = result.get("saved_files", [])
            
            # 构建回复消息
            response_message = f"搜索完成！\n"
            response_message += f"找到 {total_found} 张相关照片\n"
            response_message += f"成功下载 {downloaded} 张缩略图\n"
            
            if failed > 0:
                response_message += f"下载失败 {failed} 张\n"
            
            if saved_files:
                response_message += f"\n缩略图已保存到: {save_dir}\n"
                response_message += f"共 {len(saved_files)} 个文件"
            
            logger.bind(tag=TAG).info(
                f"Immich 搜索完成: 找到 {total_found} 张, 下载 {downloaded} 张"
            )
            
            return ActionResponse(Action.REQLLM, response_message, None)
        else:
            errors = result.get("errors", [])
            error_msg = "搜索失败"
            if errors:
                error_msg += f": {errors[0]}"
            
            logger.bind(tag=TAG).error(f"Immich 搜索失败: {errors}")
            return ActionResponse(Action.RESPONSE, None, error_msg)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"搜索 Immich 图片异常: {e}", exc_info=True)
        return ActionResponse(Action.RESPONSE, None, f"搜索图片时发生错误: {str(e)}")

