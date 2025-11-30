import json
import copy
from aiohttp import web
from config.logger import setup_logging
from core.utils.util import get_vision_url, is_valid_image_file
from core.utils.vllm import create_instance
from config.config_loader import get_private_config_from_api
from core.utils.auth import AuthToken
from core.utils.immich_client import ImmichClient
import base64
from typing import Tuple, Optional
from plugins_func.register import Action

TAG = __name__

# 设置最大文件大小为5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


class VisionHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        # 初始化认证工具
        self.auth = AuthToken(config["server"]["auth_key"])
        # 初始化Immich客户端
        immich_config = config.get("Immich", {})
        self.immich_client = ImmichClient(immich_config) if immich_config else None

    def _create_error_response(self, message: str) -> dict:
        """创建统一的错误响应格式"""
        return {"success": False, "message": message}

    def _verify_auth_token(self, request) -> Tuple[bool, Optional[str]]:
        """验证认证token"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False, None

        token = auth_header[7:]  # 移除"Bearer "前缀
        return self.auth.verify_token(token)

    async def handle_post(self, request):
        """处理 MCP Vision POST 请求"""
        response = None  # 初始化response变量
        try:
            # 验证token
            is_valid, token_device_id = self._verify_auth_token(request)
            if not is_valid:
                response = web.Response(
                    text=json.dumps(
                        self._create_error_response("无效的认证token或token已过期")
                    ),
                    content_type="application/json",
                    status=401,
                )
                return response

            # 获取请求头信息
            device_id = request.headers.get("Device-Id", "")
            client_id = request.headers.get("Client-Id", "")
            if device_id != token_device_id:
                raise ValueError("设备ID与token不匹配")
            # 解析multipart/form-data请求
            reader = await request.multipart()

            # 读取question字段
            question_field = await reader.next()
            if question_field is None:
                raise ValueError("缺少问题字段")
            question = await question_field.text()
            self.logger.bind(tag=TAG).info(f"Question: {question}")

            # 读取图片文件
            image_field = await reader.next()
            if image_field is None:
                raise ValueError("缺少图片文件")

            # 读取图片数据
            image_data = await image_field.read()
            if not image_data:
                raise ValueError("图片数据为空")

            # 检查文件大小
            if len(image_data) > MAX_FILE_SIZE:
                raise ValueError(
                    f"图片大小超过限制，最大允许{MAX_FILE_SIZE/1024/1024}MB"
                )

            # 检查文件格式
            if not is_valid_image_file(image_data):
                raise ValueError(
                    "不支持的文件格式，请上传有效的图片文件（支持JPEG、PNG、GIF、BMP、TIFF、WEBP格式）"
                )

            # 将图片转换为base64编码
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 调用Immich API上传图片并识别人物
            people_info = None
            if self.immich_client and self.immich_client.enabled:
                try:
                    self.logger.bind(tag=TAG).info("开始上传图片到Immich并识别人物")
                    people_info = await self.immich_client.upload_and_recognize_people(image_data)
                    if people_info.get("success"):
                        people_count = len(people_info.get("people", []))
                        self.logger.bind(tag=TAG).info(
                            f"Immich识别完成: 资产ID={people_info.get('asset_id')}, "
                            f"识别到{people_count}个人物"
                        )
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"Immich识别失败: {people_info.get('message')}"
                        )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Immich识别异常: {e}")
                    people_info = None

            # 如果识别到人物，将人物信息整合到question中，让VLLM在回答中包含人物信息
            people_names = []
            if people_info and people_info.get("success") and people_info.get("people"):
                people_list = people_info.get("people", [])
                # 只提取有效的人物名称（排除"未命名"和空值）
                people_names = [
                    p.get("person_name") 
                    for p in people_list 
                    if p.get("person_name") and p.get("person_name") != "未命名"
                ]
                if people_names:
                    # 优化question构建，更明确地要求VLLM提及人物
                    if "人物" not in question and "人" not in question:
                        # 如果原问题没有涉及人物，添加明确的人物描述要求
                        people_str = "、".join(people_names)
                        question = f"{question}\n\n注意：这张图片中识别到了以下人物：{people_str}。请在你的回答中明确提及这些人物，并结合他们来描述图片内容。"
                    else:
                        # 如果原问题已经涉及人物，添加人物列表
                        people_str = "、".join(people_names)
                        question = f"{question}\n\n[已识别的人物：{people_str}]"
                    self.logger.bind(tag=TAG).info(f"已将人物信息添加到question中: {people_names}")
                else:
                    self.logger.bind(tag=TAG).info("识别到人物但均为未命名，不添加到question中")

            # 如果开启了智控台，则从智控台获取模型配置
            current_config = copy.deepcopy(self.config)
            read_config_from_api = current_config.get("read_config_from_api", False)
            if read_config_from_api:
                current_config = get_private_config_from_api(
                    current_config,
                    device_id,
                    client_id,
                )

            select_vllm_module = current_config["selected_module"].get("VLLM")
            if not select_vllm_module:
                raise ValueError("您还未设置默认的视觉分析模块")

            vllm_type = (
                select_vllm_module
                if "type" not in current_config["VLLM"][select_vllm_module]
                else current_config["VLLM"][select_vllm_module]["type"]
            )

            if not vllm_type:
                raise ValueError(f"无法找到VLLM模块对应的供应器{vllm_type}")

            vllm = create_instance(
                vllm_type, current_config["VLLM"][select_vllm_module]
            )

            result = vllm.response(question, image_base64)
            # 打印result
            self.logger.bind(tag=TAG).info(f"VLLM识别结果: {result}")

            # 如果识别到人物但VLLM回答中没有提及，在结果中补充人物信息
            if people_names and result:
                # 检查结果中是否包含人物名称
                result_lower = result.lower()
                people_mentioned = any(name.lower() in result_lower for name in people_names)
                
                if not people_mentioned:
                    # 如果VLLM没有提及人物，在结果末尾补充
                    people_str = "、".join(people_names)
                    result = f"{result}\n\n[识别到的人物：{people_str}]"
                    self.logger.bind(tag=TAG).info(f"VLLM回答中未提及人物，已补充人物信息: {people_names}")

            # 构建返回结果，保持原有协议不变
            return_json = {
                "success": True,
                "action": Action.RESPONSE.name,
                "response": result,
            }

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except ValueError as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response(str(e))
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response("处理请求时发生错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """处理 MCP Vision GET 请求"""
        try:
            vision_explain = get_vision_url(self.config)
            if vision_explain and len(vision_explain) > 0 and "null" != vision_explain:
                message = (
                    f"MCP Vision 接口运行正常，视觉解释接口地址是：{vision_explain}"
                )
            else:
                message = "MCP Vision 接口运行不正常，请打开data目录下的.config.yaml文件，找到【server.vision_explain】，设置好地址"

            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision GET请求异常: {e}")
            return_json = self._create_error_response("服务器内部错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response

    def _add_cors_headers(self, response):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"
