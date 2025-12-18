"""
WebSocket消息验证器
验证消息格式的正确性，确保消息符合协议规范
"""
from typing import Dict, Any, Optional, Tuple
from core.protocol.message_types import WebMessageType


class WebMessageValidator:
    """WebSocket消息验证器 - 验证消息格式"""
    
    @staticmethod
    def validate(message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证消息格式
        
        Args:
            message: 要验证的消息字典
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
                - is_valid: 消息是否有效
                - error_message: 错误信息（如果无效）
        """
        if not isinstance(message, dict):
            return False, "消息必须是字典类型"
        
        msg_type = message.get("type")
        if not msg_type:
            return False, "消息缺少type字段"
        
        if not WebMessageType.is_valid(msg_type):
            return False, f"无效的消息类型: {msg_type}"
        
        # 根据消息类型验证必需字段
        if msg_type == WebMessageType.STT.value:
            required = ["text", "session_id"]
            if not all(field in message for field in required):
                return False, f"STT消息缺少必需字段: {', '.join(required)}"
        
        elif msg_type == WebMessageType.LLM.value:
            required = ["text", "session_id", "device_id"]
            if not all(field in message for field in required):
                return False, f"LLM消息缺少必需字段: {', '.join(required)}"
        
        elif msg_type == WebMessageType.LLM_SENTENCE.value:
            required = ["text", "session_id", "device_id"]
            if not all(field in message for field in required):
                return False, f"LLM_SENTENCE消息缺少必需字段: {', '.join(required)}"
        
        elif msg_type == WebMessageType.TTS.value:
            required = ["state", "session_id"]
            if not all(field in message for field in required):
                return False, f"TTS消息缺少必需字段: {', '.join(required)}"
            # 验证state值
            valid_states = ["start", "sentence_start", "stop"]
            if message.get("state") not in valid_states:
                return False, f"TTS消息的state字段无效，必须是: {', '.join(valid_states)}"
        
        elif msg_type == WebMessageType.VOICEPRINT_IDENTIFIED.value:
            required = ["data"]
            if not all(field in message for field in required):
                return False, f"VOICEPRINT_IDENTIFIED消息缺少必需字段: {', '.join(required)}"
            # 验证data字段结构
            data = message.get("data")
            if not isinstance(data, dict):
                return False, "VOICEPRINT_IDENTIFIED消息的data字段必须是字典类型"
            data_required = ["speaker_name", "session_id", "device_id", "timestamp"]
            if not all(field in data for field in data_required):
                return False, f"VOICEPRINT_IDENTIFIED消息的data字段缺少必需字段: {', '.join(data_required)}"
        
        elif msg_type == WebMessageType.VISION.value:
            required = ["result", "people", "people_ids", "session_id", "device_id"]
            if not all(field in message for field in required):
                return False, f"VISION消息缺少必需字段: {', '.join(required)}"
            # 验证people和people_ids是列表
            if not isinstance(message.get("people"), list):
                return False, "VISION消息的people字段必须是列表类型"
            if not isinstance(message.get("people_ids"), list):
                return False, "VISION消息的people_ids字段必须是列表类型"
        
        elif msg_type == WebMessageType.IMMICH_SEARCH_RESULT.value:
            required = ["data", "device_id"]
            if not all(field in message for field in required):
                return False, f"IMMICH_SEARCH_RESULT消息缺少必需字段: {', '.join(required)}"
            # 验证data字段结构
            data = message.get("data")
            if not isinstance(data, dict):
                return False, "IMMICH_SEARCH_RESULT消息的data字段必须是字典类型"
            if "assets" not in data:
                return False, "IMMICH_SEARCH_RESULT消息的data字段缺少assets字段"
        
        elif msg_type == WebMessageType.HELLO.value:
            if "content" not in message:
                return False, "HELLO消息缺少必需字段: content"
        
        elif msg_type == WebMessageType.MEMORY_MARKDOWN.value:
            required = ["content", "session_id"]
            if not all(field in message for field in required):
                return False, f"MEMORY_MARKDOWN消息缺少必需字段: {', '.join(required)}"
        
        elif msg_type == WebMessageType.MEMORY_IMAGES.value:
            required = ["images", "session_id"]
            if not all(field in message for field in required):
                return False, f"MEMORY_IMAGES消息缺少必需字段: {', '.join(required)}"
            if not isinstance(message.get("images"), list):
                return False, "MEMORY_IMAGES消息的images字段必须是列表类型"
        
        elif msg_type == WebMessageType.RESOURCE_MATCH.value:
            required = ["matches", "session_id"]
            if not all(field in message for field in required):
                return False, f"RESOURCE_MATCH消息缺少必需字段: {', '.join(required)}"
        
        return True, None
    
    @staticmethod
    def validate_required_fields(message: Dict[str, Any], required_fields: list[str]) -> Tuple[bool, Optional[str]]:
        """验证消息是否包含所有必需字段
        
        Args:
            message: 要验证的消息字典
            required_fields: 必需字段列表
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        missing_fields = [field for field in required_fields if field not in message]
        if missing_fields:
            return False, f"消息缺少必需字段: {', '.join(missing_fields)}"
        return True, None

