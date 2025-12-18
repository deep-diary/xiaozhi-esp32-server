"""
WebSocket消息类型枚举
用于Gradio Web客户端与xiaozhi-server之间的通讯协议
"""
from enum import Enum


class WebMessageType(str, Enum):
    """WebSocket消息类型枚举 - 用于Gradio Web客户端通讯"""
    
    # ========== Web客户端 → 服务器 ==========
    HELLO = "hello"  # 聊天消息
    PING = "ping"    # 心跳消息
    
    # ========== 服务器 → Web客户端 ==========
    # 语音和文本处理
    STT = "stt"                    # 语音识别结果
    LLM = "llm"                    # LLM完整回复
    LLM_SENTENCE = "llm_sentence"  # LLM句子片段（流式输出）
    TTS = "tts"                    # TTS状态
    VOICEPRINT_IDENTIFIED = "voiceprint_identified"  # 声纹识别结果
    
    # 视觉和记忆
    VISION = "vision"                      # 视觉识别结果
    IMMICH_SEARCH_RESULT = "immich_search_result"  # Immich搜索结果
    MEMORY_MARKDOWN = "memory_markdown"    # 记忆Markdown内容
    MEMORY_IMAGES = "memory_images"        # 记忆图片列表
    
    # 资源追溯
    RESOURCE_MATCH = "resource_match"  # 资源匹配结果
    
    # 系统消息
    PONG = "pong"  # 心跳响应
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """检查消息类型是否有效
        
        Args:
            value: 消息类型字符串
            
        Returns:
            bool: 是否为有效的消息类型
        """
        return value in [item.value for item in cls]
    
    @classmethod
    def get_all_types(cls) -> list[str]:
        """获取所有消息类型列表
        
        Returns:
            list[str]: 所有消息类型的值列表
        """
        return [item.value for item in cls]
    
    @classmethod
    def get_client_to_server_types(cls) -> list[str]:
        """获取客户端到服务器的消息类型列表
        
        Returns:
            list[str]: 客户端到服务器的消息类型列表
        """
        return [cls.HELLO.value, cls.PING.value]
    
    @classmethod
    def get_server_to_client_types(cls) -> list[str]:
        """获取服务器到客户端的消息类型列表
        
        Returns:
            list[str]: 服务器到客户端的消息类型列表
        """
        return [
            cls.STT.value,
            cls.LLM.value,
            cls.LLM_SENTENCE.value,
            cls.TTS.value,
            cls.VOICEPRINT_IDENTIFIED.value,
            cls.VISION.value,
            cls.IMMICH_SEARCH_RESULT.value,
            cls.MEMORY_MARKDOWN.value,
            cls.MEMORY_IMAGES.value,
            cls.RESOURCE_MATCH.value,
            cls.PONG.value,
        ]

