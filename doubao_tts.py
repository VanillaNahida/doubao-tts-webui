#!/usr/bin/env python3
"""
豆包 TTS (Text-to-Speech) 逆向工程客户端
Doubao TTS Reverse Engineering Client

用法:
    python doubao_tts.py "你好，世界" -o output.aac
    python doubao_tts.py "Hello World" --speaker zh_male_rap_mars_bigtts -o rap.aac
"""

import asyncio
import json
import argparse
import uuid
import random
import time
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field

try:
    import websockets
except ImportError:
    print("请安装 websockets: pip install websockets")
    exit(1)


@dataclass
class TTSConfig:
    """TTS 配置"""
    # 语音角色 ID
    speaker: str = "zh_female_taozi_conversation_v4_wvae_bigtts"
    # 音频格式: aac, mp3, wav
    format: str = "aac"
    # 语速: -1.0 ~ 1.0, 0 为正常
    speech_rate: float = 0
    # 音调: -1.0 ~ 1.0, 0 为正常
    pitch: float = 0
    # 语言
    language: str = "zh"
    # 应用 ID
    aid: int = 497858
    # 版本号
    version_code: int = 20800
    pc_version: str = "2.46.3"
    # Cookie (从浏览器获取)
    cookie: str = ""


@dataclass
class TTSResult:
    """TTS 结果"""
    audio_data: bytes = field(default_factory=bytes)
    sentences: list = field(default_factory=list)
    success: bool = False
    error: str = ""


# 常用语音角色
SPEAKERS = {
    # 女声
    "taozi": "zh_female_taozi_conversation_v4_wvae_bigtts",  # 桃子 - 对话
    "shuangkuai": "zh_female_shuangkuai_emo_v3_wvae_bigtts",  # 爽快
    "tianmei": "zh_female_tianmei_conversation_v4_wvae_bigtts",  # 甜美
    "qingche": "zh_female_qingche_moon_bigtts",  # 清澈
    
    # 男声
    "yangguang": "zh_male_yangguang_conversation_v4_wvae_bigtts",  # 阳光
    "chenwen": "zh_male_chenwen_moon_bigtts",  # 沉稳
    "rap": "zh_male_rap_mars_bigtts",  # 说唱
    
    # 多语言
    "en_female": "en_female_sarah_conversation_bigtts",
    "en_male": "en_male_adam_conversation_bigtts",
}


class DoubaoTTS:
    """豆包 TTS 客户端"""
    
    WS_URL = "wss://ws-samantha.doubao.com/samantha/audio/tts"
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._device_id = self._generate_device_id()
        self._web_id = self._generate_web_id()
    
    def _generate_device_id(self) -> str:
        """生成设备 ID"""
        return str(random.randint(7400000000000000000, 7499999999999999999))
    
    def _generate_web_id(self) -> str:
        """生成 Web ID"""
        return str(random.randint(7400000000000000000, 7499999999999999999))
    
    def _build_ws_url(self) -> str:
        """构建 WebSocket URL"""
        params = {
            "speaker": self.config.speaker,
            "format": self.config.format,
            "speech_rate": int(self.config.speech_rate * 100) if self.config.speech_rate != 0 else 0,
            "pitch": int(self.config.pitch * 100) if self.config.pitch != 0 else 0,
            "version_code": self.config.version_code,
            "language": self.config.language,
            "device_platform": "web",
            "aid": self.config.aid,
            "real_aid": self.config.aid,
            "pkg_type": "release_version",
            "device_id": self._device_id,
            "pc_version": self.config.pc_version,
            "web_id": self._web_id,
            "tea_uuid": self._web_id,
            "region": "",
            "sys_region": "",
            "samantha_web": 1,
            "use-olympus-account": 1,
            "web_tab_id": str(uuid.uuid4()),
        }
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.WS_URL}?{query}"
    
    async def synthesize(
        self, 
        text: str,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
        on_sentence_start: Optional[Callable[[str], None]] = None,
        on_sentence_end: Optional[Callable[[], None]] = None,
    ) -> TTSResult:
        """
        合成语音
        
        Args:
            text: 要转换的文本
            on_audio_chunk: 音频块回调 (用于流式播放)
            on_sentence_start: 句子开始回调
            on_sentence_end: 句子结束回调
            
        Returns:
            TTSResult: 合成结果
        """
        result = TTSResult()
        audio_chunks = []
        
        ws_url = self._build_ws_url()
        
        headers = {
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Origin": "https://www.doubao.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # 如果有 cookie，添加到 headers
        if self.config.cookie:
            headers["Cookie"] = self.config.cookie
        
        try:
            async with websockets.connect(
                ws_url,
                additional_headers=headers,
            ) as ws:
                # 发送文本
                await ws.send(json.dumps({
                    "event": "text",
                    "text": text
                }))
                
                # 发送结束信号
                await ws.send(json.dumps({
                    "event": "finish"
                }))
                
                # 接收响应
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=30)
                        
                        if isinstance(message, bytes):
                            # 音频数据
                            audio_chunks.append(message)
                            if on_audio_chunk:
                                on_audio_chunk(message)
                        else:
                            # JSON 消息
                            data = json.loads(message)
                            event = data.get("event", "")
                            
                            if event == "open_success":
                                print(f"[INFO] 连接成功")
                                
                            elif event == "sentence_start":
                                readable_text = data.get("sentence_start_result", {}).get("readable_text", "")
                                result.sentences.append(readable_text)
                                if on_sentence_start:
                                    on_sentence_start(readable_text)
                                print(f"[句子] {readable_text[:50]}...")
                                
                            elif event == "sentence_end":
                                if on_sentence_end:
                                    on_sentence_end()
                                    
                            elif event == "error":
                                result.error = data.get("message", "Unknown error")
                                print(f"[ERROR] {result.error}")
                                break
                                
                            elif data.get("code", 0) != 0:
                                result.error = data.get("message", "Unknown error")
                                print(f"[ERROR] Code: {data.get('code')}, {result.error}")
                                break
                                
                    except asyncio.TimeoutError:
                        print("[INFO] 接收超时，合成完成")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        print("[INFO] 连接关闭，合成完成")
                        break
                        
        except Exception as e:
            result.error = str(e)
            print(f"[ERROR] 连接失败: {e}")
            return result
        
        # 合并音频数据
        result.audio_data = b"".join(audio_chunks)
        result.success = len(result.audio_data) > 0
        
        print(f"[INFO] 合成完成, 音频大小: {len(result.audio_data)} bytes")
        return result
    
    def synthesize_sync(self, text: str, **kwargs) -> TTSResult:
        """同步版本的合成方法"""
        return asyncio.run(self.synthesize(text, **kwargs))
    
    def set_speaker(self, speaker: str):
        """设置语音角色"""
        # 如果是简称，转换为完整 ID
        self.config.speaker = SPEAKERS.get(speaker, speaker)
        return self
    
    def set_speed(self, speed: float):
        """设置语速 (-1.0 ~ 1.0)"""
        self.config.speech_rate = max(-1.0, min(1.0, speed))
        return self
    
    def set_pitch(self, pitch: float):
        """设置音调 (-1.0 ~ 1.0)"""
        self.config.pitch = max(-1.0, min(1.0, pitch))
        return self


def load_cookie_from_file() -> str:
    """从配置文件加载 cookie"""
    cookie_file = Path(__file__).parent / ".cookie"
    if cookie_file.exists():
        return cookie_file.read_text().strip()
    return ""


def save_cookie_to_file(cookie: str):
    """保存 cookie 到配置文件"""
    cookie_file = Path(__file__).parent / ".cookie"
    cookie_file.write_text(cookie)
    print(f"✅ Cookie 已保存到: {cookie_file}")


async def main():
    parser = argparse.ArgumentParser(description="豆包 TTS 文本转语音工具")
    parser.add_argument("text", nargs="?", default="", help="要转换的文本")
    parser.add_argument("-o", "--output", default="output.aac", help="输出文件路径")
    parser.add_argument("-s", "--speaker", default="taozi", help=f"语音角色: {', '.join(SPEAKERS.keys())}")
    parser.add_argument("--speed", type=float, default=0, help="语速 (-1.0 ~ 1.0)")
    parser.add_argument("--pitch", type=float, default=0, help="音调 (-1.0 ~ 1.0)")
    parser.add_argument("--format", default="aac", choices=["aac", "mp3"], help="音频格式")
    parser.add_argument("--list-speakers", action="store_true", help="列出可用语音")
    parser.add_argument("--cookie", help="豆包网站 Cookie (首次使用需要)")
    parser.add_argument("--save-cookie", action="store_true", help="保存 Cookie 到配置文件")
    
    args = parser.parse_args()
    
    if args.list_speakers:
        print("\n可用语音角色:")
        print("-" * 60)
        for name, speaker_id in SPEAKERS.items():
            print(f"  {name:15} → {speaker_id}")
        print("-" * 60)
        return
    
    # 处理 cookie
    cookie = args.cookie or load_cookie_from_file()
    
    if args.save_cookie and args.cookie:
        save_cookie_to_file(args.cookie)
    
    if not cookie:
        print("⚠️  需要提供 Cookie 才能使用豆包 TTS")
        print("\n获取方法:")
        print("  1. 打开浏览器访问 https://www.doubao.com 并登录")
        print("  2. 按 F12 打开开发者工具")
        print("  3. 切换到 Network 标签页")
        print("  4. 刷新页面，点击任意请求")
        print("  5. 在 Headers 中找到 Cookie 并复制")
        print("\n使用方法:")
        print('  python doubao_tts.py "文本" --cookie "你的cookie" --save-cookie')
        return
    
    if not args.text:
        parser.print_help()
        return
    
    # 创建客户端
    config = TTSConfig(format=args.format, cookie=cookie)
    tts = DoubaoTTS(config)
    tts.set_speaker(args.speaker)
    tts.set_speed(args.speed)
    tts.set_pitch(args.pitch)
    
    print(f"\n🎤 豆包 TTS")
    print(f"   文本: {args.text[:50]}{'...' if len(args.text) > 50 else ''}")
    print(f"   语音: {args.speaker}")
    print(f"   输出: {args.output}\n")
    
    # 合成语音
    result = await tts.synthesize(args.text)
    
    if result.success:
        # 保存文件
        output_path = Path(args.output)
        output_path.write_bytes(result.audio_data)
        print(f"\n✅ 已保存到: {output_path.absolute()}")
        print(f"   文件大小: {len(result.audio_data):,} bytes")
    else:
        print(f"\n❌ 合成失败: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
