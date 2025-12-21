"""
WebSocket消息构建器
统一构建和格式化WebSocket消息，确保消息格式的一致性
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.protocol.message_types import WebMessageType


class WebMessageBuilder:
    """WebSocket消息构建器 - 统一构建WebSocket消息"""
    
    @staticmethod
    def _serialize_datetime(obj: Any) -> Any:
        """递归地将字典中的 datetime 对象转换为 ISO 格式字符串
        
        Args:
            obj: 要处理的对象（可能是字典、列表、datetime 或其他类型）
            
        Returns:
            处理后的对象，datetime 对象已转换为字符串
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: WebMessageBuilder._serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [WebMessageBuilder._serialize_datetime(item) for item in obj]
        else:
            return obj
    
    @staticmethod
    def build_hello_message(content: str) -> Dict[str, Any]:
        """构建hello消息（Web客户端 → 服务器）
        
        Args:
            content: 用户输入的文本消息
            
        Returns:
            Dict: hello消息字典
        """
        return {
            "type": WebMessageType.HELLO.value,
            "content": content
        }
    
    @staticmethod
    def build_ping_message() -> Dict[str, Any]:
        """构建ping消息（Web客户端 → 服务器）
        
        Returns:
            Dict: ping消息字典
        """
        return {
            "type": WebMessageType.PING.value
        }
    
    @staticmethod
    def build_stt_message(
        text: str,
        session_id: str,
        speaker: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建STT消息（服务器 → Web客户端）
        
        Args:
            text: 识别到的用户说话内容
            session_id: 会话ID
            speaker: 说话人名称（可选）
            
        Returns:
            Dict: STT消息字典
        """
        message = {
            "type": WebMessageType.STT.value,
            "text": text,
            "session_id": session_id
        }
        if speaker:
            message["speaker"] = speaker
        return message
    
    @staticmethod
    def build_llm_message(
        text: str,
        session_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """构建LLM消息（服务器 → Web客户端）
        
        Args:
            text: AI的完整回复内容
            session_id: 会话ID
            device_id: 设备ID
            
        Returns:
            Dict: LLM消息字典
        """
        return {
            "type": WebMessageType.LLM.value,
            "text": text,
            "session_id": session_id,
            "device_id": device_id
        }
    
    @staticmethod
    def build_llm_sentence_message(
        text: str,
        session_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """构建LLM句子片段消息（服务器 → Web客户端）
        
        Args:
            text: 句子片段内容
            session_id: 会话ID
            device_id: 设备ID
            
        Returns:
            Dict: LLM句子片段消息字典
        """
        return {
            "type": WebMessageType.LLM_SENTENCE.value,
            "text": text,
            "session_id": session_id,
            "device_id": device_id
        }
    
    @staticmethod
    def build_tts_message(
        state: str,
        session_id: str,
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建TTS消息（服务器 → Web客户端）
        
        Args:
            state: TTS状态（start/sentence_start/stop）
            session_id: 会话ID
            text: 句子文本（仅在sentence_start状态时使用）
            
        Returns:
            Dict: TTS消息字典
        """
        message = {
            "type": WebMessageType.TTS.value,
            "state": state,
            "session_id": session_id
        }
        if text is not None:
            message["text"] = text
        return message
    
    @staticmethod
    def build_voiceprint_identified_message(
        speaker_name: str,
        session_id: str,
        device_id: str,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """构建声纹识别消息（服务器 → Web客户端）
        
        Args:
            speaker_name: 识别到的说话人名称
            session_id: 会话ID
            device_id: 设备ID
            timestamp: 时间戳（可选，默认使用当前时间）
            
        Returns:
            Dict: 声纹识别消息字典
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        
        return {
            "type": WebMessageType.VOICEPRINT_IDENTIFIED.value,
            "data": {
                "speaker_name": speaker_name,
                "session_id": session_id,
                "device_id": device_id,
                "timestamp": timestamp
            }
        }
    
    @staticmethod
    def build_vision_message(
        result: str,
        people: List[str],
        people_ids: List[str],
        session_id: str,
        device_id: str,
        asset_id: Optional[str] = None,
        image_url: Optional[str] = None,
        image: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建视觉识别消息（服务器 → Web客户端）
        
        Args:
            result: VLLM识别的图片内容描述
            people: 识别到的人物名称列表
            people_ids: 识别到的人物ID列表
            session_id: 会话ID
            device_id: 设备ID
            asset_id: Immich资产ID（可选）
            image_url: Immich图片URL（可选，优先使用）
            image: base64编码的图片数据（可选，降级方案）
            
        Returns:
            Dict: 视觉识别消息字典
        """
        message = {
            "type": WebMessageType.VISION.value,
            "result": result,
            "people": people,
            "people_ids": people_ids,
            "session_id": session_id,
            "device_id": device_id
        }
        if asset_id:
            message["asset_id"] = asset_id
        if image_url:
            message["image_url"] = image_url
        elif image:
            message["image"] = image
        return message
    
    @staticmethod
    def build_immich_search_result_message(
        assets: List[Dict[str, Any]],
        query: str,
        device_id: str,
        person_name: Optional[str] = None,
        city: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建Immich搜索结果消息（服务器 → Web客户端）
        
        Args:
            assets: 资产列表（可能包含 datetime 对象）
            query: 查询关键词
            device_id: 设备ID
            person_name: 查询的人物名称（可选）
            city: 查询的城市（可选）
            date: 查询的日期（可选）
            
        Returns:
            Dict: Immich搜索结果消息字典（所有 datetime 对象已转换为字符串）
        """
        # 序列化资产数据中的 datetime 对象
        serialized_assets = WebMessageBuilder._serialize_datetime(assets)
        
        return {
            "type": WebMessageType.IMMICH_SEARCH_RESULT.value,
            "data": {
                "assets": serialized_assets,
                "count": len(assets),
                "query": query,
                "person_name": person_name,
                "city": city,
                "date": date,
                "device_id": device_id
            },
            "device_id": device_id
        }
    
    @staticmethod
    def build_pong_message() -> Dict[str, Any]:
        """构建pong消息（服务器 → Web客户端）
        
        Returns:
            Dict: pong消息字典
        """
        return {
            "type": WebMessageType.PONG.value
        }
    
    @staticmethod
    def build_memory_markdown_message(
        content: str,
        session_id: str
    ) -> Dict[str, Any]:
        """构建记忆Markdown消息（服务器 → Web客户端）
        
        Args:
            content: Markdown格式的记忆内容
            session_id: 会话ID
            
        Returns:
            Dict: 记忆Markdown消息字典
        """
        return {
            "type": WebMessageType.MEMORY_MARKDOWN.value,
            "content": content,
            "session_id": session_id
        }
    
    @staticmethod
    def build_memory_images_message(
        images: List[str],
        session_id: str
    ) -> Dict[str, Any]:
        """构建记忆图片列表消息（服务器 → Web客户端）
        
        Args:
            images: 图片URL列表
            session_id: 会话ID
            
        Returns:
            Dict: 记忆图片列表消息字典
        """
        return {
            "type": WebMessageType.MEMORY_IMAGES.value,
            "images": images,
            "session_id": session_id
        }
    
    @staticmethod
    def build_resource_match_message(
        matches: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """构建资源匹配结果消息（服务器 → Web客户端）
        
        Args:
            matches: 匹配结果数据
            session_id: 会话ID
            
        Returns:
            Dict: 资源匹配结果消息字典
        """
        return {
            "type": WebMessageType.RESOURCE_MATCH.value,
            "matches": matches,
            "session_id": session_id
        }
    
    @staticmethod
    def build_immich_kiosk_url_message(
        kiosk_url: str,
        device_id: str,
        person_name: Optional[str] = None,
        person_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建 Immich Kiosk URL 消息（服务器 → Web客户端）
        
        Args:
            kiosk_url: Immich Kiosk 完整 URL（包含参数）
            device_id: 设备ID
            person_name: 人物名称（可选）
            person_id: 人物 ID（可选）
            
        Returns:
            Dict: Immich Kiosk URL 消息字典
        """
        message = {
            "type": WebMessageType.IMMICH_KIOSK_URL.value,
            "data": {
                "kiosk_url": kiosk_url,
                "device_id": device_id
            },
            "device_id": device_id
        }
        if person_name:
            message["data"]["person_name"] = person_name
        if person_id:
            message["data"]["person_id"] = person_id
        return message

