import asyncio
import json

import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api_async
from core.auth import AuthManager, AuthenticationError
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        auth_config = self.config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # 设备白名单
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        secret_key = self.config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds", None)
        self.auth = AuthManager(secret_key=secret_key, expire_seconds=expire_seconds)

        # Gradio 客户端连接集合
        self.gradio_clients = set()

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection, host, port, process_request=self._http_response
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        headers = dict(websocket.request.headers)
        if headers.get("device-id", None) is None:
            # 尝试从 URL 的查询参数中获取 device-id
            from urllib.parse import parse_qs, urlparse

            # 从 WebSocket 请求中获取路径
            request_path = websocket.request.path
            if not request_path:
                self.logger.bind(tag=TAG).error("无法获取请求路径")
                await websocket.close()
                return
            parsed_url = urlparse(request_path)
            query_params = parse_qs(parsed_url.query)
            if "device-id" not in query_params:
                await websocket.send("端口正常，如需测试连接，请使用test_page.html")
                await websocket.close()
                return
            else:
                websocket.request.headers["device-id"] = query_params["device-id"][0]
            if "client-id" in query_params:
                websocket.request.headers["client-id"] = query_params["client-id"][0]
            if "authorization" in query_params:
                websocket.request.headers["authorization"] = query_params[
                    "authorization"
                ][0]

        """处理新连接，每次创建独立的ConnectionHandler"""
        # 获取客户端类型
        headers = dict(websocket.request.headers)
        client_id = headers.get("client-id", "")
        device_id = headers.get("device-id", "")

        # 判断是否为 Gradio 客户端
        is_gradio_client = client_id == "gradio-client" or device_id.startswith("web_")

        if is_gradio_client:
            # 处理 Gradio 客户端连接
            try:
                await self._handle_auth(websocket)
                await self.register_gradio_client(websocket)

                # 保持连接活跃，监听断开
                try:
                    await websocket.wait_closed()
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Gradio 客户端连接异常: {e}")
                finally:
                    await self.unregister_gradio_client(websocket)

            except AuthenticationError:
                await websocket.send("认证失败")
                await websocket.close()
                return
        else:
            # 处理设备客户端连接
            try:
                await self._handle_auth(websocket)
            except AuthenticationError:
                await websocket.send("认证失败")
                await websocket.close()
                return

            # 创建ConnectionHandler时传入当前server实例
            handler = ConnectionHandler(
                self.config,
                self._vad,
                self._asr,
                self._llm,
                self._memory,
                self._intent,
                self,  # 传入server实例
            )
            try:
                await handler.handle_connection(websocket)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"处理设备连接时出错: {e}")
            finally:
                # 强制关闭连接（如果还没有关闭的话）
                try:
                    # 安全地检查WebSocket状态并关闭
                    if hasattr(websocket, "closed") and not websocket.closed:
                        await websocket.close()
                    elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                        await websocket.close()
                    else:
                        # 如果没有closed属性，直接尝试关闭
                        await websocket.close()
                except Exception as close_error:
                    self.logger.bind(tag=TAG).error(
                        f"服务器端强制关闭连接时出错: {close_error}"
                    )

    async def _http_response(self, websocket, request_headers):
        # 检查是否为 WebSocket 升级请求
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # 如果是 WebSocket 请求，返回 None 允许握手继续
            return None
        else:
            # 如果是普通 HTTP 请求，返回 "server is running"
            return websocket.respond(200, "Server is running\n")

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置（使用异步版本）
                new_config = await get_config_from_api_async(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    async def register_gradio_client(self, websocket):
        """注册 Gradio 客户端"""
        self.gradio_clients.add(websocket)
        self.logger.bind(tag=TAG).info(f"注册新的 Gradio 客户端，当前客户端数量: {len(self.gradio_clients)}")

    async def unregister_gradio_client(self, websocket):
        """注销 Gradio 客户端"""
        self.gradio_clients.discard(websocket)
        self.logger.bind(tag=TAG).info(f"注销 Gradio 客户端，当前客户端数量: {len(self.gradio_clients)}")

    async def broadcast_to_gradio(self, message):
        """向所有 Gradio 客户端广播消息"""
        if not self.gradio_clients:
            return

        disconnected_clients = set()
        for client in self.gradio_clients.copy():
            try:
                await client.send(json.dumps(message))
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"向 Gradio 客户端广播消息失败: {e}")
                disconnected_clients.add(client)

        # 清理断开的客户端
        for client in disconnected_clients:
            self.gradio_clients.discard(client)

    async def _handle_auth(self, websocket):
        # 先认证，后建立连接
        if self.auth_enable:
            headers = dict(websocket.request.headers)
            device_id = headers.get("device-id", None)
            client_id = headers.get("client-id", None)
            if self.allowed_devices and device_id in self.allowed_devices:
                # 如果属于白名单内的设备，不校验token，直接放行
                return
            else:
                # 否则校验token
                token = headers.get("authorization", "")
                if token.startswith("Bearer "):
                    token = token[7:]  # 移除'Bearer '前缀
                else:
                    raise AuthenticationError("Missing or invalid Authorization header")
                # 进行认证
                auth_success = self.auth.verify_token(
                    token, client_id=client_id, username=device_id
                )
                if not auth_success:
                    raise AuthenticationError("Invalid token")
