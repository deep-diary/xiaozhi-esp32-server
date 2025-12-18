"""
Web连接处理器 - 专门处理 Gradio/Web 客户端连接
与 ConnectionHandler 分离，独立管理 Web 客户端的连接和消息转发
"""
import json
import asyncio
import logging
import websockets
from typing import Optional, Dict, Any
from config.logger import setup_logging
from core.protocol.message_builder import WebMessageBuilder
from core.protocol.message_types import WebMessageType

TAG = __name__


class WebConnectionHandler:
    """Web客户端连接处理器"""
    
    def __init__(self, websocket, device_id: str, server=None):
        """
        初始化Web连接处理器
        
        Args:
            websocket: WebSocket连接对象
            device_id: 设备ID，用于匹配对应的设备连接
            server: WebSocketServer实例引用
        """
        self.websocket = websocket
        self.device_id = device_id
        self.server = server
        self.logger = setup_logging()
        self.client_ip = None
        self._closed = False
        
    async def handle_connection(self):
        """处理Web客户端连接"""
        try:
            # 获取客户端IP
            headers = dict(self.websocket.request.headers)
            real_ip = headers.get("x-real-ip") or headers.get("x-forwarded-for")
            if real_ip:
                self.client_ip = real_ip.split(",")[0].strip()
            else:
                self.client_ip = self.websocket.remote_address[0] if hasattr(self.websocket, 'remote_address') else "unknown"
            
            self.logger.bind(tag=TAG).info(
                f"Web客户端连接: device_id={self.device_id}, ip={self.client_ip}"
            )
            
            # 保持连接活跃，监听消息和断开
            try:
                async for message in self.websocket:
                    await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info(f"Web客户端断开连接: device_id={self.device_id}")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Web客户端连接异常: {e}")
        finally:
            self._closed = True
            await self.cleanup()
    
    async def _handle_message(self, message):
        """处理来自Web客户端的消息"""
        try:
            if isinstance(message, str):
                # 处理文本消息
                try:
                    data = json.loads(message)
                    await self._process_web_message(data)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).warning(f"收到非JSON格式的Web消息: {message}")
            elif isinstance(message, bytes):
                # 处理二进制消息（如果需要）
                self.logger.bind(tag=TAG).debug(f"收到Web客户端二进制消息，长度: {len(message)}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理Web客户端消息失败: {e}")
    
    async def _process_web_message(self, data: Dict[str, Any]):
        """处理Web客户端的JSON消息"""
        msg_type = data.get("type", "")
        
        if msg_type == WebMessageType.HELLO.value:
            # 处理来自Web的聊天消息，转发到对应的设备连接
            content = data.get("content", "")
            if content and self.server:
                await self._forward_to_device(content)
        elif msg_type == WebMessageType.PING.value:
            # 心跳消息
            pong_message = WebMessageBuilder.build_pong_message()
            await self.send_message(pong_message)
        else:
            self.logger.bind(tag=TAG).debug(f"收到Web客户端消息: {msg_type}")
    
    async def _forward_to_device(self, content: str):
        """将Web客户端的消息转发到对应的设备连接"""
        if not self.server:
            return
        
        # 通过server的connection_manager找到对应的设备连接
        device_conn = self.server.connection_manager.get_device_connection(self.device_id)
        if device_conn:
            # 转发消息到设备连接（通过文本消息处理）
            from core.handle.textHandle import handleTextMessage
            hello_message = WebMessageBuilder.build_hello_message(content=content)
            await handleTextMessage(device_conn, json.dumps(hello_message))
        else:
            self.logger.bind(tag=TAG).warning(
                f"未找到对应的设备连接: device_id={self.device_id}"
            )
    
    async def send_message(self, message: Dict[str, Any]):
        """向Web客户端发送消息"""
        if self._closed or not self.websocket:
            return
        
        # 验证消息格式（可选，用于调试）
        try:
            from core.protocol.message_validator import WebMessageValidator
            is_valid, error = WebMessageValidator.validate(message)
            if not is_valid:
                self.logger.bind(tag=TAG).warning(f"消息格式验证失败: {error}, message={message}")
        except Exception:
            # 验证失败不影响消息发送
            pass
        
        try:
            await self.websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            self._closed = True
            self.logger.bind(tag=TAG).debug(f"Web客户端连接已关闭，无法发送消息")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"向Web客户端发送消息失败: {e}")
            self._closed = True
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.websocket and not self._closed:
                try:
                    await self.websocket.close()
                except Exception:
                    pass
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"清理Web连接资源失败: {e}")
    
    def is_closed(self) -> bool:
        """检查连接是否已关闭"""
        return self._closed

