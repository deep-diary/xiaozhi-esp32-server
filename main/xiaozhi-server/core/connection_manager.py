"""
连接管理器 - 统一管理所有WebSocket连接（设备端和Web端）
提供统一的消息转发接口
"""
import json
import asyncio
from typing import Dict, Set, Optional
from config.logger import setup_logging

TAG = __name__


class ConnectionManager:
    """连接管理器 - 统一管理所有连接"""
    
    def __init__(self):
        """初始化连接管理器"""
        self.logger = setup_logging()
        
        # 设备连接: {device_id: ConnectionHandler}
        self.device_connections: Dict[str, any] = {}
        
        # Web连接: {device_id: set(WebConnectionHandler)} - 一个device_id可能对应多个web客户端
        self.web_connections: Dict[str, Set[any]] = {}
    
    def register_device(self, device_id: str, connection_handler):
        """注册设备连接
        
        Args:
            device_id: 设备ID
            connection_handler: ConnectionHandler实例
        """
        self.device_connections[device_id] = connection_handler
        self.logger.bind(tag=TAG).info(
            f"注册设备连接: device_id={device_id}, 当前设备连接数={len(self.device_connections)}"
        )
    
    def unregister_device(self, device_id: str):
        """注销设备连接
        
        Args:
            device_id: 设备ID
        """
        if device_id in self.device_connections:
            del self.device_connections[device_id]
            self.logger.bind(tag=TAG).info(
                f"注销设备连接: device_id={device_id}, 当前设备连接数={len(self.device_connections)}"
            )
    
    def register_web(self, device_id: str, web_handler):
        """注册Web客户端连接
        
        Args:
            device_id: 设备ID（用于匹配对应的设备连接）
            web_handler: WebConnectionHandler实例
        """
        if device_id not in self.web_connections:
            self.web_connections[device_id] = set()
        self.web_connections[device_id].add(web_handler)
        
        self.logger.bind(tag=TAG).info(
            f"注册Web客户端: device_id={device_id}, "
            f"该设备Web客户端数={len(self.web_connections[device_id])}, "
            f"总Web客户端数={self.get_total_web_count()}"
        )
    
    def unregister_web(self, device_id: str, web_handler):
        """注销Web客户端连接
        
        Args:
            device_id: 设备ID
            web_handler: WebConnectionHandler实例
        """
        if device_id in self.web_connections:
            self.web_connections[device_id].discard(web_handler)
            if not self.web_connections[device_id]:
                del self.web_connections[device_id]
        
        self.logger.bind(tag=TAG).info(
            f"注销Web客户端: device_id={device_id}, "
            f"总Web客户端数={self.get_total_web_count()}"
        )
    
    def get_device_connection(self, device_id: str):
        """根据device_id获取设备连接
        
        Args:
            device_id: 设备ID
            
        Returns:
            ConnectionHandler实例，如果不存在则返回None
        """
        return self.device_connections.get(device_id)
    
    def get_total_web_count(self) -> int:
        """获取所有Web客户端的总数"""
        return sum(len(handlers) for handlers in self.web_connections.values())
    
    async def broadcast_to_all_web(self, message: dict):
        """广播消息到所有Web客户端
        
        Args:
            message: 要发送的消息字典
        """
        if not self.web_connections:
            return
        
        disconnected_handlers = []
        total_sent = 0
        
        for device_id, handlers in self.web_connections.items():
            for handler in handlers.copy():
                try:
                    if not handler.is_closed():
                        await handler.send_message(message)
                        total_sent += 1
                    else:
                        disconnected_handlers.append((device_id, handler))
                except Exception as e:
                    self.logger.bind(tag=TAG).error(
                        f"向Web客户端广播消息失败: device_id={device_id}, error={e}"
                    )
                    disconnected_handlers.append((device_id, handler))
        
        # 清理断开的客户端
        for device_id, handler in disconnected_handlers:
            self.unregister_web(device_id, handler)
        
        self.logger.bind(tag=TAG).debug(
            f"广播消息到所有Web客户端完成: 成功={total_sent}, 断开={len(disconnected_handlers)}"
        )
    
    async def broadcast_to_all_devices(self, message: dict):
        """广播消息到所有设备连接
        
        Args:
            message: 要发送的消息字典
        """
        if not self.device_connections:
            return
        
        disconnected_devices = []
        total_sent = 0
        
        for device_id, handler in self.device_connections.items():
            try:
                if handler.websocket and not handler.websocket.closed:
                    await handler.websocket.send(json.dumps(message))
                    total_sent += 1
                else:
                    disconnected_devices.append(device_id)
            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"向设备连接广播消息失败: device_id={device_id}, error={e}"
                )
                disconnected_devices.append(device_id)
        
        # 清理断开的设备连接
        for device_id in disconnected_devices:
            self.unregister_device(device_id)
        
        self.logger.bind(tag=TAG).debug(
            f"广播消息到所有设备连接完成: 成功={total_sent}, 断开={len(disconnected_devices)}"
        )
    
    async def forward_to_web_by_device_id(self, device_id: str, message: dict):
        """根据device_id转发消息到匹配的Web客户端
        
        Args:
            device_id: 设备ID
            message: 要发送的消息字典
        """
        if device_id not in self.web_connections:
            return
        
        disconnected_handlers = []
        total_sent = 0
        
        for handler in self.web_connections[device_id].copy():
            try:
                if not handler.is_closed():
                    await handler.send_message(message)
                    total_sent += 1
                else:
                    disconnected_handlers.append(handler)
            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"向Web客户端转发消息失败: device_id={device_id}, error={e}"
                )
                disconnected_handlers.append(handler)
        
        # 清理断开的客户端
        for handler in disconnected_handlers:
            self.unregister_web(device_id, handler)
        
        self.logger.bind(tag=TAG).debug(
            f"转发消息到Web客户端完成: device_id={device_id}, 成功={total_sent}, 断开={len(disconnected_handlers)}"
        )
    
    async def forward_to_device_by_device_id(self, device_id: str, message: dict):
        """根据device_id转发消息到匹配的设备连接
        
        Args:
            device_id: 设备ID
            message: 要发送的消息字典
        """
        handler = self.device_connections.get(device_id)
        if not handler:
            self.logger.bind(tag=TAG).debug(
                f"未找到设备连接: device_id={device_id}"
            )
            return
        
        try:
            if handler.websocket and not handler.websocket.closed:
                await handler.websocket.send(json.dumps(message))
                self.logger.bind(tag=TAG).debug(
                    f"转发消息到设备连接成功: device_id={device_id}"
                )
            else:
                self.logger.bind(tag=TAG).warning(
                    f"设备连接已关闭: device_id={device_id}"
                )
                self.unregister_device(device_id)
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"向设备连接转发消息失败: device_id={device_id}, error={e}"
            )
            self.unregister_device(device_id)
    
    def get_connection_stats(self) -> dict:
        """获取连接统计信息
        
        Returns:
            包含连接统计信息的字典
        """
        return {
            "device_count": len(self.device_connections),
            "web_count": self.get_total_web_count(),
            "web_by_device": {
                device_id: len(handlers) 
                for device_id, handlers in self.web_connections.items()
            },
            "device_ids": list(self.device_connections.keys())
        }

