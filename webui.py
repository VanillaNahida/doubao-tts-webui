import asyncio
import json
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

import gradio as gr

from doubao_tts import DoubaoTTS, TTSConfig, SPEAKERS, load_cookie_from_file, save_cookie_to_file

CONFIG_PATH = Path(__file__).parent / "config.json"


SPEAKER_CHOICES = [
    (f"{name} - {desc}", name)
    for name, (speaker_id, desc) in {
        "taozi": ("zh_female_taozi_conversation_v4_wvae_bigtts", "桃子 女声"),
        "shuangkuai": ("zh_female_shuangkuai_emo_v3_wvae_bigtts", "爽快 女声"),
        "tianmei": ("zh_female_tianmei_conversation_v4_wvae_bigtts", "甜美 女声"),
        "qingche": ("zh_female_qingche_moon_bigtts", "清澈 女声"),
        "yangguang": ("zh_male_yangguang_conversation_v4_wvae_bigtts", "阳光 男声"),
        "chenwen": ("zh_male_chenwen_moon_bigtts", "沉稳 男声"),
        "rap": ("zh_male_rap_mars_bigtts", "说唱 男声"),
        "en_female": ("en_female_sarah_conversation_bigtts", "英文 女声"),
        "en_male": ("en_male_adam_conversation_bigtts", "英文 男声"),
    }.items()
]

AUDIO_FORMATS = ["aac", "mp3"]

COOKIE_HELP = "点击下方「登录/重新登录」按钮，登录后自动获取 Cookie"

OUTPUT_DIR = Path(__file__).parent / "tts_output"

async def synthesize_audio(text, speaker, speed, pitch, fmt, cookie, auto_save, progress=gr.Progress()):
    if not text.strip():
        gr.Warning("请输入要合成的文本")
        return None, "请输入要合成的文本"

    if not cookie.strip():
        gr.Warning("请先配置 Cookie")
        return None, "请先配置 Cookie（从浏览器登录豆包后获取）"

    config = TTSConfig(format=fmt, cookie=cookie.strip())
    tts = DoubaoTTS(config)
    tts.set_speaker(speaker)
    tts.set_speed(speed)
    tts.set_pitch(pitch)

    progress(0.2, desc="正在连接服务器...")

    result = await tts.synthesize(text)

    if result.success:
        progress(0.9, desc="合成完成，准备音频...")
        suffix = f".{fmt}"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(result.audio_data)
        tmp_path = tmp.name
        tmp.close()

        if auto_save:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = OUTPUT_DIR / f"tts_{timestamp}{suffix}"
            save_path.write_bytes(result.audio_data)

        file_size = len(result.audio_data)
        sentences_count = len(result.sentences)
        status = (
            f"合成成功\n"
            f"音频大小: {file_size:,} bytes\n"
            f"句子数: {sentences_count}"
        )
        if auto_save:
            status += f"\n已保存: tts_output/tts_{timestamp}{suffix}"

        gr.Info("合成成功")
        return tmp_path, status

    gr.Error(f"合成失败: {result.error}")
    return None, f"合成失败: {result.error}"


def save_cookie(cookie):
    if not cookie.strip():
        gr.Warning("Cookie 不能为空")
        return "Cookie 不能为空"
    save_cookie_to_file(cookie.strip())
    gr.Info("Cookie 已保存")
    return "Cookie 已保存"


def load_cookie():
    cookie = load_cookie_from_file()
    if cookie:
        return cookie, "Cookie 已从文件加载"
    return "", "未找到已保存的 Cookie"


def toggle_cookie_visibility(visibility_state):
    new_state = not visibility_state
    new_type = "text" if new_state else "password"
    button_text = "隐藏 Cookie" if new_state else "显示 Cookie"
    return gr.update(type=new_type), button_text, new_state


def relogin(process, orig_mtime, countdown):
    login_script = Path(__file__).parent / "login.py"
    if not login_script.exists():
        gr.Error("未找到 login.py")
        return "未找到 login.py，请确认文件存在", process, orig_mtime, 0
    if process is not None and process.poll() is None:
        gr.Warning("登录浏览器已打开，请勿重复点击")
        return "登录浏览器已打开，请勿重复点击", process, orig_mtime, 0

    cookie_file = Path(__file__).parent / ".cookie"
    try:
        orig_mtime = cookie_file.stat().st_mtime
    except (FileNotFoundError, OSError):
        orig_mtime = 0.0

    python = sys.executable
    process = subprocess.Popen([python, str(login_script)], shell=True)
    gr.Info("已打开登录浏览器，请在浏览器窗口中完成登录")
    return "已打开登录浏览器，请在浏览器窗口中完成登录", process, orig_mtime, 0


def check_login_status(process, orig_mtime, countdown):
    if process is None:
        if countdown > 0:
            countdown -= 1
            if countdown == 0:
                return "使用当前 Cookie", None, 0.0, 0
            return f"登录失败，请稍后再试（{countdown}s）", None, 0.0, countdown
        return gr.skip()

    retcode = process.poll()
    if retcode is None:
        return "已打开登录浏览器，请在浏览器窗口中完成登录", process, orig_mtime, 0

    cookie_file = Path(__file__).parent / ".cookie"
    try:
        mtime = cookie_file.stat().st_mtime
        if mtime > orig_mtime and cookie_file.stat().st_size > 0:
            gr.Info("登录成功")
            return "登录成功", None, 0.0, 0
    except (FileNotFoundError, OSError):
        pass

    gr.Error("登录失败，请稍后再试")
    return "登录失败，请稍后再试（3s）", None, 0.0, 3


FONT_CSS = (
    '<link rel="stylesheet" href="//cdn.jsdelivr.net/gh/VanillaNahida/BA-Spark-Cursor/fonts/Blueaka/Blueaka.css">\n'
    '<link rel="stylesheet" href="//cdn.jsdelivr.net/gh/VanillaNahida/BA-Spark-Cursor/fonts/Blueaka_Bold/Blueaka_Bold.css">\n'
    "<style>"
    "* { font-family: 'Blueaka', 'Blueaka_Bold', sans-serif !important; }"
    ".text-input-area textarea { overflow-y: auto !important; resize: vertical !important; }"
    "</style>"
)

DEFAULT_CONFIG = {
    "speaker": "taozi",
    "fmt": "aac",
    "speed": 0.0,
    "pitch": 0.0,
    "auto_save": False,
}


def save_config(speaker, fmt, speed, pitch, auto_save):
    data = {
        "speaker": speaker,
        "fmt": fmt,
        "speed": speed,
        "pitch": pitch,
        "auto_save": auto_save,
    }
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return


def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = DEFAULT_CONFIG
    for key in DEFAULT_CONFIG:
        if key not in data:
            data[key] = DEFAULT_CONFIG[key]
    return (
        gr.update(value=data["speaker"]),
        gr.update(value=data["fmt"]),
        gr.update(value=data["speed"]),
        gr.update(value=data["pitch"]),
        gr.update(value=data["auto_save"]),
    )


def welcome_toast():
    gr.Info(
        "欢迎使用豆包 TTS WebUI！如果该项目对你有帮助，可以点个star支持一下！感谢你的支持！"
    )


def create_ui():
    with gr.Blocks(title="豆包 TTS WebUI", head=FONT_CSS) as ui:
        gr.Markdown(
            """
            # 豆包 TTS WebUI
            作者：callmerio & VanillaNahida   
            基于豆包 WebSocket 接口的文本转语音工具   
            原作者：https://github.com/callmerio/doubao-tts   
            开源地址：https://github.com/VanillaNahida/doubao-tts-webui  
            B站主页：https://space.bilibili.com/1347891621
            """
        )
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 配置")
                cookie_visibility = gr.State(False)
                cookie_input = gr.Textbox(
                    label="Cookie",
                    placeholder="sessionid=xxx; sid_guard=xxx; uid_tt=xxx",
                    info=COOKIE_HELP,
                    type="password",
                )
                with gr.Row():
                    load_cookie_btn = gr.Button("加载 Cookie", size="sm")
                    save_cookie_btn = gr.Button("保存 Cookie", size="sm", variant="secondary")
                    toggle_visibility_btn = gr.Button("显示 Cookie", size="sm", variant="secondary")
                with gr.Row():
                    relogin_btn = gr.Button("登录/重新登录", size="sm", variant="primary")
                cookie_status = gr.Textbox(label="Cookie 状态", interactive=False)
                login_process = gr.State(None)
                login_cookie_mtime = gr.State(0.0)
                login_fail_countdown = gr.State(0)

                speaker_input = gr.Dropdown(
                    choices=SPEAKER_CHOICES,
                    value="taozi",
                    label="语音角色",
                    info="选择不同的语音风格",
                )

                fmt_input = gr.Radio(
                    choices=AUDIO_FORMATS,
                    value="aac",
                    label="音频格式",
                )

                speed_input = gr.Slider(
                    minimum=-1.0,
                    maximum=1.0,
                    value=0,
                    step=0.1,
                    label="语速",
                    info="-1.0 ~ 1.0，0 为正常语速",
                )

                pitch_input = gr.Slider(
                    minimum=-1.0,
                    maximum=1.0,
                    value=0,
                    step=0.1,
                    label="音调",
                    info="-1.0 ~ 1.0，0 为正常音调",
                )

                auto_save = gr.Checkbox(
                    label="自动保存音频",
                    value=False,
                    info="勾选后每次合成自动保存音频文件到 tts_output 目录",
                )

            with gr.Column(scale=2):
                gr.Markdown("### 文本输入")
                text_input = gr.Textbox(
                    label="文本输入",
                    placeholder="请输入要转换为语音的文本...",
                    lines=8,
                    elem_classes="text-input-area",
                )

                synthesize_btn = gr.Button("合成语音", size="lg", variant="primary")

                status_output = gr.Textbox(label="执行状态", value="已准备就绪。", interactive=False)

                audio_output = gr.Audio(
                    label="合成结果",
                    type="filepath",
                    interactive=False,
                )

        gr.Markdown(
            """
            ---
            ### 使用说明
            1. 点击"登录/重新登录"按钮，程序会自动打开浏览器
            2. 在浏览器中登录豆包账号，登录成功后自动保存 Cookie 并关闭
            3. 回到本页面点击"加载 Cookie"按钮加载已保存的 Cookie
            4. 选择语音角色，调整语速和音调
            5. 输入文本，点击"合成语音"即可生成音频
            6. 生成的音频可直接播放或下载
            """
        )

        load_cookie_btn.click(
            fn=load_cookie,
            outputs=[cookie_input, cookie_status],
        )

        save_cookie_btn.click(
            fn=save_cookie,
            inputs=[cookie_input],
            outputs=[cookie_status],
        )

        toggle_visibility_btn.click(
            fn=toggle_cookie_visibility,
            inputs=[cookie_visibility],
            outputs=[cookie_input, toggle_visibility_btn, cookie_visibility],
        )

        relogin_btn.click(
            fn=relogin,
            inputs=[login_process, login_cookie_mtime, login_fail_countdown],
            outputs=[cookie_status, login_process, login_cookie_mtime, login_fail_countdown],
        )

        login_timer = gr.Timer(value=1)
        login_timer.tick(
            fn=check_login_status,
            inputs=[login_process, login_cookie_mtime, login_fail_countdown],
            outputs=[cookie_status, login_process, login_cookie_mtime, login_fail_countdown],
        )

        speaker_input.change(
            fn=save_config,
            inputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        )
        fmt_input.change(
            fn=save_config,
            inputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        )
        speed_input.change(
            fn=save_config,
            inputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        )
        pitch_input.change(
            fn=save_config,
            inputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        )
        auto_save.change(
            fn=save_config,
            inputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        )

        synthesize_event = synthesize_btn.click(
            fn=synthesize_audio,
            inputs=[
                text_input,
                speaker_input,
                speed_input,
                pitch_input,
                fmt_input,
                cookie_input,
                auto_save,
            ],
            outputs=[audio_output, status_output],
        )

        ui.load(
            fn=load_config,
            outputs=[speaker_input, fmt_input, speed_input, pitch_input, auto_save],
        ).then(
            fn=load_cookie,
            outputs=[cookie_input, cookie_status],
        ).then(
            fn=welcome_toast,
        )

    return ui


def open_browser_delay(url, delay=2):
    def open_browser():
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()


if __name__ == "__main__":
    ui = create_ui()
    open_browser_delay("http://127.0.0.1:7860", delay=2)
    ui.launch(server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft())
