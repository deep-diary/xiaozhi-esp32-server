import os
import io
import wave
import uuid
import json
import time
import queue
import asyncio
import traceback
import threading
import opuslib_next
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List, Dict, Any
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import handleAudioMessage

TAG = __name__
logger = setup_logging()


async def search_and_send_person_photos(conn, speaker_name: str):
    """异步搜索人物照片并发送到前端
    
    Args:
        conn: 连接对象
        speaker_name: 说话人名称
    """
    try:
        # 使用连接对象的懒加载方法获取 ImmichLogic 实例
        immich_logic = conn.get_immich_logic()
        if not immich_logic:
            logger.bind(tag=TAG).debug("ImmichLogic 不可用，跳过照片搜索")
            return
        
        from core.protocol.message_builder import WebMessageBuilder
        
        # 获取 Immich 配置（用于读取 voiceprint_photo_count）
        immich_config = conn.config.get("Immich", {})
        
        # 搜索人物照片（随机返回10张）
        # 使用默认的 size=4，但可以通过配置调整
        photo_count = immich_config.get("voiceprint_photo_count", 10)
        assets = await immich_logic.search_random_by_person(
            person_name=speaker_name,
            size=photo_count
        )
        
        if assets and len(assets) > 0:
            # 格式化资产数据，只包含必要字段（不包含URL，因为Immich URL不是公开的）
            formatted_assets = []
            for asset in assets:
                # 提取资产基本信息
                asset_dict = {
                    "id": asset.get("id"),  # asset_id，前端可以通过此ID访问照片
                    "type": asset.get("type"),  # IMAGE 或 VIDEO
                    "createdAt": asset.get("createdAt"),  # 创建时间
                    "localDateTime": asset.get("localDateTime"),  # 本地时间
                    "originalFileName": asset.get("originalFileName"),  # 原始文件名
                }
                
                # 添加 EXIF 信息（如果有）
                if asset.get("exifInfo"):
                    asset_dict["exifInfo"] = asset.get("exifInfo")
                
                # 添加其他有用信息
                if asset.get("isFavorite") is not None:
                    asset_dict["isFavorite"] = asset.get("isFavorite")
                
                formatted_assets.append(asset_dict)
            
            # 发送搜索结果到前端
            message = WebMessageBuilder.build_immich_search_result_message(
                assets=formatted_assets,
                query="voiceprint_triggered",  # 标识这是声纹触发的搜索
                device_id=conn.device_id,
                person_name=speaker_name
            )
            
            await conn.server.forward_to_web_by_device_id(conn.device_id, message)
            logger.bind(tag=TAG).info(
                f"已发送 {len(formatted_assets)} 张照片到web端（声纹识别触发）: {speaker_name}"
            )
        else:
            logger.bind(tag=TAG).debug(f"未找到 {speaker_name} 的照片")
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"搜索并发送人物照片失败: {e}", exc_info=True)


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # 打开音频通道
    async def open_audio_channels(self, conn):
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # 有序处理ASR音频
    def asr_text_priority_thread(self, conn):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理ASR文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    # 接收音频
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "manual":
            # 手动模式：缓存音频用于ASR识别
            conn.asr_audio.append(audio)
        else:
            # 自动/实时模式：使用VAD检测
            have_voice = audio_have_voice

            conn.asr_audio.append(audio)
            if not have_voice and not conn.client_have_voice:
                conn.asr_audio = conn.asr_audio[-10:]
                return

            # 自动模式下通过VAD检测到语音停止时触发识别
            if conn.client_voice_stop:
                asr_audio_task = conn.asr_audio.copy()
                conn.asr_audio.clear()
                conn.reset_vad_states()

                if len(asr_audio_task) > 15:
                    await self.handle_voice_stop(conn, asr_audio_task)

    # 处理语音停止
    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """并行处理ASR和声纹识别"""
        try:
            total_start_time = time.monotonic()

            # 准备音频数据
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)

            combined_pcm_data = b"".join(pcm_data)

            # 预先准备WAV数据
            wav_data = None
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)

            # 定义ASR任务
            asr_task = self.speech_to_text(asr_audio_task, conn.session_id, conn.audio_format)

            if conn.voiceprint_provider and wav_data:
                voiceprint_task = conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                # 并发等待两个结果
                asr_result, voiceprint_result = await asyncio.gather(
                    asr_task, voiceprint_task, return_exceptions=True
                )
            else:
                asr_result = await asr_task
                voiceprint_result = None

            # 记录识别结果 - 检查是否为异常
            if isinstance(asr_result, Exception):
                logger.bind(tag=TAG).error(f"ASR识别失败: {asr_result}")
                raw_text = ""
            else:
                raw_text, _ = asr_result

            if isinstance(voiceprint_result, Exception):
                logger.bind(tag=TAG).error(f"声纹识别失败: {voiceprint_result}")
                speaker_name = ""
            else:
                speaker_name = voiceprint_result

            if raw_text:
                logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
            if speaker_name:
                logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")
                
                # 识别到有效声纹后，异步从Immich搜索该人物的照片并发送给前端
                if speaker_name and speaker_name != "未知说话人":
                    # 异步搜索并发送照片（不阻塞主流程）
                    if hasattr(conn, 'server') and conn.server and hasattr(conn.server, 'forward_to_web_by_device_id'):
                        # 使用 create_task 异步执行，不阻塞当前流程
                        asyncio.create_task(
                            search_and_send_person_photos(conn, speaker_name)
                        )
                    else:
                        logger.bind(tag=TAG).warning("无法搜索人物照片: server或forward_to_web_by_device_id方法不存在")

            # 性能监控
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).debug(f"总处理耗时: {total_time:.3f}s")

            # 检查文本长度
            text_len, _ = remove_punctuation_and_length(raw_text)
            self.stop_ws_connection()

            if text_len > 0:
                # 构建包含说话人信息的JSON字符串
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)

                # 使用自定义模块进行上报
                await startToChat(conn, enhanced_text)
                enqueue_asr_report(conn, enhanced_text, asr_audio_task)
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理语音停止失败: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"异常详情: {traceback.format_exc()}")

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """构建包含说话人信息的文本"""
        if speaker_name and speaker_name.strip():
            return json.dumps({
                "speaker": speaker_name,
                "content": text
            }, ensure_ascii=False)
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """将PCM数据转换为WAV格式"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM数据为空，无法转换WAV")
            return b""
        
        # 确保数据长度是偶数（16位音频）
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        
        # 创建WAV文件头
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)      # 单声道
                wav_file.setsampwidth(2)      # 16位
                wav_file.setframerate(16000)  # 16kHz采样率
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV转换失败: {e}")
            return b""

    def stop_ws_connection(self):
        pass

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """将Opus音频数据解码为PCM数据"""
        decoder = None
        try:
            decoder = opuslib_next.Decoder(16000, 1)
            pcm_data = []
            buffer_size = 960  # 每次处理960个采样点 (60ms at 16kHz)
            
            for i, opus_packet in enumerate(opus_data):
                try:
                    if not opus_packet or len(opus_packet) == 0:
                        continue
                    
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame and len(pcm_frame) > 0:
                        pcm_data.append(pcm_frame)
                        
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus解码错误，跳过数据包 {i}: {e}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"音频处理错误，数据包 {i}: {e}")
            
            return pcm_data
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频解码过程发生错误: {e}")
            return []
        finally:
            if decoder is not None:
                try:
                    del decoder
                except Exception as e:
                    logger.bind(tag=TAG).debug(f"释放decoder资源时出错: {e}")
