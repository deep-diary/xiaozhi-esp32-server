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
            "从 Immich 相册中搜索图片。"
            "根据用户的需求，提取搜索条件（人物、地点、日期、内容描述）来搜索照片。"
            "重要：只有当用户明确提到某个条件时，才填写对应的参数；如果用户没有提到，则不要填写该参数。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": (
                        "要搜索的人物名称（人名）。"
                        "重要：只有当用户明确提到人名时才填写此参数，例如用户说'Jason的照片'、'找Alex的照片'等。"
                        "如果用户没有提到人名，则不要填写此参数（不传或传空）。"
                        "示例：'Jason'、'Alex'、'张三'、'Mary'等。"
                    ),
                },
                "city": {
                    "type": "string",
                    "description": (
                        "要搜索的城市名称（英文）。"
                        "重要：只有当用户明确提到城市名称时才填写此参数，例如用户说'在北京拍的照片'、'上海的照片'等。"
                        "如果用户没有提到城市，则不要填写此参数（不传或传空）。"
                        "示例：'Beijing'、'Shanghai'、'New York'、'Tokyo'等。"
                    ),
                },
                "date": {
                    "type": "string",
                    "description": (
                        "要搜索的日期。"
                        "重要：只有当用户明确提到日期时才填写此参数，例如用户说'2024年的照片'、'去年拍的照片'、'1月1日的照片'等。"
                        "如果用户没有提到日期，则不要填写此参数（不传或传空）。"
                        "格式：YYYY-MM-DD 或 YYYY-MM-DD 到 YYYY-MM-DD（日期范围）。"
                        "示例：'2024-01-01'、'2024-01-01 到 2024-12-31'等。"
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "照片内容的英文文字描述，用于智能搜索。"
                        "重要：必须将用户的中文描述准确翻译成英文关键词。"
                        "如果用户说'我想看雪山的照片'，应该翻译为'snow mountain'或'snowy mountain'；"
                        "如果用户说'骑自行车的照片'，应该翻译为'bicycle'或'cycling'或'bike'；"
                        "如果用户说'海边的照片'，应该翻译为'beach'或'seaside'；"
                        "如果用户说'生日聚会的照片'，应该翻译为'birthday party'；"
                        "如果用户说'宠物的照片'，应该翻译为'pet'或'dog'或'cat'等。"
                        "如果用户没有提到具体的内容描述，则不要填写此参数（不传或传空）。"
                    ),
                },
                "max_count": {
                    "type": "integer",
                    "description": (
                        "最大返回数量，默认5。"
                        "如果用户明确提到数量（如'给我看10张照片'），则填写对应数字；否则使用默认值5。"
                    ),
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
        date_str = date_str.strip()
        
        # 检查是否是日期范围（包含"到"关键字）
        if "到" in date_str:
            # 处理日期范围，例如："2024-01-01 到 2024-12-31"
            parts = date_str.split("到", 1)  # 只分割一次，避免日期中的"-"干扰
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                
                # 尝试解析日期
                try:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                    # 结束日期设置为当天的23:59:59
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    logger.bind(tag=TAG).info(f"成功解析日期范围: {start_date} 到 {end_date}")
                    return start_date, end_date
                except ValueError as e:
                    logger.bind(tag=TAG).warning(f"日期范围解析失败: {date_str}, 错误: {e}")
                    return None, None
        
        # 单个日期
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = date.replace(hour=23, minute=59, second=59)
            logger.bind(tag=TAG).info(f"成功解析单个日期: {date} 到 {end_date}")
            return date, end_date
        except ValueError as e:
            logger.bind(tag=TAG).warning(f"日期格式解析失败: {date_str}, 错误: {e}")
            return None, None
    
    except Exception as e:
        logger.bind(tag=TAG).warning(f"日期解析异常: {date_str}, 错误: {e}")
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
        
        # 组合查询字符串
        query = " ".join(query_parts) if query_parts else ""
        
        # 处理日期范围
        date_range = None
        if date:
            taken_after, taken_before = _parse_date_range(date)
            if taken_after or taken_before:
                date_range = (taken_after, taken_before)
                logger.bind(tag=TAG).info(f"日期范围解析成功: {taken_after} 到 {taken_before}")
            else:
                logger.bind(tag=TAG).warning(f"日期范围解析失败，将不使用日期过滤: {date}")
        
        # 设置最大数量
        max_count_value = max_count or 5
        
        logger.bind(tag=TAG).info(
            f"准备搜索 Immich 图片: query='{query}', "
            f"person_name={person_name}, city={city}, date={date}, max_count={max_count_value}"
        )
        
        # 在新线程中运行事件循环，避免与当前线程的事件循环冲突
        try:
            timeout_seconds = 30  # 30秒超时
            
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
                        # 根据是否有query参数决定调用智能搜索还是随机搜索
                        if query:
                            # 有query参数，调用智能搜索
                            logger.bind(tag=TAG).info("使用智能搜索")
                            assets = new_loop.run_until_complete(
                                asyncio.wait_for(
                                    immich_logic.search_smart_assets(
                                        query=query,
                                        person_name=person_name,
                                        city=city,
                                        date=date_range,
                                        size=max_count_value,
                                        visibility=AssetVisibility.TIMELINE
                                    ),
                                    timeout=timeout_seconds
                                )
                            )
                        elif person_name:
                            # query为空但人物信息不为空，调用随机检索
                            logger.bind(tag=TAG).info(f"使用随机搜索，人物: {person_name}")
                            assets = new_loop.run_until_complete(
                                asyncio.wait_for(
                                    immich_logic.search_random_by_person(
                                        person_name=person_name,
                                        size=max_count_value,
                                        city=city,
                                        date=date_range,
                                        visibility=AssetVisibility.TIMELINE
                                    ),
                                    timeout=timeout_seconds
                                )
                            )
                        else:
                            # 既没有query也没有person_name，返回错误
                            result_container["exception"] = ValueError("请提供至少一个搜索条件（人物名称或文字描述）")
                            return
                        
                        # 确保 assets 是列表类型
                        if assets is not None and not isinstance(assets, list):
                            logger.bind(tag=TAG).error(f"搜索返回了非列表类型: {type(assets)}, 值: {assets}")
                            result_container["exception"] = TypeError(f"搜索返回了非列表类型: {type(assets)}")
                            return
                        
                        result_container["result"] = assets
                        logger.bind(tag=TAG).info(f"搜索完成，找到 {len(assets) if assets else 0} 个资产")
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
                
                assets = result_container["result"]
                
                # 确保 assets 是列表类型
                if assets is not None and not isinstance(assets, list):
                    logger.bind(tag=TAG).error(f"搜索结果不是列表类型: {type(assets)}, 值: {assets}")
                    return ActionResponse(
                        Action.RESPONSE,
                        None,
                        f"搜索返回了错误的数据类型: {type(assets).__name__}"
                    )
                
                # 统计实际找到的资产数量（这是真实的搜索结果，不是请求数量）
                actual_count = len(assets) if assets else 0
                logger.bind(tag=TAG).info(
                    f"搜索任务完成: 实际找到 {actual_count} 个资产 "
                    f"(请求数量: {max_count_value}, 这是真实的搜索结果)"
                )
                
                if not assets:
                    return ActionResponse(
                        Action.RESPONSE,
                        None,
                        "未找到相关照片，请尝试其他搜索条件"
                    )
                
                # 通过socket接口发送资产列表给web端
                if hasattr(conn, 'server') and conn.server and hasattr(conn.server, 'forward_to_web_by_device_id'):
                    try:
                        import json
                        message = {
                            "type": "immich_search_result",
                            "data": {
                                "assets": assets,
                                "count": len(assets),
                                "query": query,
                                "person_name": person_name,
                                "city": city,
                                "date": date,
                                "device_id": conn.device_id
                            },
                            "device_id": conn.device_id
                        }
                        # 在新线程的事件循环中发送消息
                        def send_message():
                            send_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(send_loop)
                            try:
                                send_loop.run_until_complete(conn.server.forward_to_web_by_device_id(conn.device_id, message))
                                logger.bind(tag=TAG).info(f"已通过socket发送 {len(assets)} 个资产到web端")
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"发送资产列表到web端失败: {e}", exc_info=True)
                            finally:
                                send_loop.close()
                        
                        send_thread = threading.Thread(target=send_message, daemon=True)
                        send_thread.start()
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"创建发送线程失败: {e}", exc_info=True)
                else:
                    logger.bind(tag=TAG).warning("无法发送资产列表到web端: server或forward_to_web_by_device_id方法不存在")
                
                # 构建简洁的回复消息，只包含查询结果汇总信息，供LLM生成语音回复
                search_conditions = []
                if person_name:
                    search_conditions.append(f"人物：{person_name}")
                if city:
                    search_conditions.append(f"城市：{city}")
                if date:
                    search_conditions.append(f"日期：{date}")
                if query and query != "photo":
                    search_conditions.append(f"描述：{query}")
                
                conditions_text = "、".join(search_conditions) if search_conditions else "所有照片"
                
                # 统计实际找到的照片数量（这是真实的搜索结果，不是请求数量）
                actual_count = len(assets) if assets else 0
                
                # 构建简洁的回复消息（只包含汇总信息，不列出每张照片的详细信息）
                if actual_count > 0:
                    response_message = f"搜索完成！根据条件（{conditions_text}）找到了 {actual_count} 张相关照片。所有照片已发送到前端展示，您可以在界面上查看。"
                else:
                    response_message = f"搜索完成！根据条件（{conditions_text}）未找到相关照片，请尝试其他搜索条件。"
                
                logger.bind(tag=TAG).info(f"构建回复消息: {response_message[:100]}...")
                
                return ActionResponse(Action.REQLLM, response_message, None)
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
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"搜索 Immich 图片异常: {e}", exc_info=True)
        return ActionResponse(Action.RESPONSE, None, f"搜索图片时发生错误: {str(e)}")

