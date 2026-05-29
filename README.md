# 豆包 TTS 逆向工程客户端

![doubao-tts-webui-webui](https://socialify.git.ci/VanillaNahida/doubao-tts-webui/image?description=1&font=Raleway&forks=1&issues=1&language=1&name=1&owner=1&pattern=Circuit+Board&pulls=1&stargazers=1&theme=Auto)

![:name](https://count.getloli.com/@doubao-tts-webui?name=doubao-tts-webui&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

基于 WebSocket 协议逆向的豆包文本转语音 Python 客户端，支持多种语音角色、语速和音调调节，提供命令行、Python API 和 WebUI 三种使用方式。   

修改自  [callmerio/doubao-tts](https://github.com/callmerio/doubao-tts)

<div align="center">

  [![GitHub license](https://img.shields.io/github/license/VanillaNahida/doubao-tts-webui?style=flat-square)](https://github.com/VanillaNahida/doubao-tts-webui/blob/main/LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/VanillaNahida/doubao-tts-webui?style=flat-square)](https://github.com/VanillaNahida/doubao-tts-webui/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/VanillaNahida/doubao-tts-webui?style=flat-square)](https://github.com/VanillaNahida/doubao-tts-webui/network)
  [![GitHub issues](https://img.shields.io/github/issues/VanillaNahida/doubao-tts-webui?style=flat-square)](https://github.com/VanillaNahida/doubao-tts-webui/issues)
  [![python3](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square)](https://www.python.org/)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-brightgreen.svg?style=flat-square)]()
  [![Author](https://img.shields.io/badge/%E4%BD%9C%E8%80%85-VanillaNahida-green)](https://github.com/VanillaNahida)

</div>

# 功能特性

- **多种语音角色**：内置 9 种语音角色，涵盖中文女声/男声、英文女声/男声，包括桃子、阳光、沉稳、说唱等风格。
- **灵活的语速音调**：支持语速和音调独立调节（-1.0 ~ 1.0），满足不同场景需求。
- **多种使用方式**：提供命令行快速合成、Python API 集成、WebUI 可视化界面三种使用方式。
- **自动登录获取 Cookie**：内置 Playwright 自动化脚本，一键登录自动保存 Cookie，无需手动复制。
- **配置持久化**：WebUI 中的语音角色、格式、语速等设置自动保存，下次启动自动恢复。

# 安装

## 环境依赖

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1    # Windows
source venv/bin/activate       # Linux
pip install -r requirements.txt
```

WebUI 和登录脚本额外依赖：

```bash
pip install playwright
python -m playwright install chromium
```

## 配置 Cookie（必须）

本工具需要豆包登录态 Cookie 才能使用。推荐使用自动化登录脚本：

```bash
python login.py
```

脚本会自动打开浏览器访问豆包登录页，检测到以下三个必需 Cookie 后自动保存：

| Cookie 名称 | 说明 |
|-------------|------|
| `sessionid` | 登录会话 ID |
| `sid_guard` | 会话守护令牌 |
| `uid_tt` | 用户唯一标识 |

如需手动配置，创建 `.cookie` 文件并写入：

```
sessionid=你的sessionid; sid_guard=你的sid_guard; uid_tt=你的uid_tt
```

> Cookie 有效期约 30 天，过期后需重新登录获取。

# 使用方法

## WebUI（推荐）

```bash
python webui.py
```

运行后会自动打开浏览器访问 `http://127.0.0.1:7860`，点击「登录/重新登录」按钮自动获取 Cookie，选择语音角色和参数，输入文本即可合成语音。

## 命令行

```
| 命令 | 说明 |
|------|------|
| `python doubao_tts.py "你好世界" -o hello.aac` | 基础用法，输出音频文件 |
| `python doubao_tts.py "欢迎" -s yangguang -o welcome.aac` | 指定阳光男声 |
| `python doubao_tts.py "测试" --speed 0.5 --pitch 0.2 -o fast.aac` | 调整语速和音调 |
| `python doubao_tts.py --list-speakers ""` | 查看所有可用语音 |
```

## Python API

```
| 方法 | 说明 |
|------|------|
| `DoubaoTTS().synthesize_sync(text)` | 同步合成 |
| `await DoubaoTTS().synthesize(text)` | 异步合成 |
| `tts.set_speaker(name)` | 设置语音角色 |
| `tts.set_speed(value)` | 设置语速 |
| `tts.set_pitch(value)` | 设置音调 |
```

```python
from doubao_tts import DoubaoTTS

tts = DoubaoTTS()
result = tts.synthesize_sync("你好，世界")
if result.success:
    with open("output.aac", "wb") as f:
        f.write(result.audio_data)
```

# 可用语音角色

| 简称 | ID | 描述 |
|------|---------|------|
| taozi | zh_female_taozi_conversation_v4_wvae_bigtts | 桃子 - 女声对话 |
| shuangkuai | zh_female_shuangkuai_emo_v3_wvae_bigtts | 爽快 - 女声 |
| tianmei | zh_female_tianmei_conversation_v4_wvae_bigtts | 甜美 - 女声 |
| qingche | zh_female_qingche_moon_bigtts | 清澈 - 女声 |
| yangguang | zh_male_yangguang_conversation_v4_wvae_bigtts | 阳光 - 男声 |
| chenwen | zh_male_chenwen_moon_bigtts | 沉稳 - 男声 |
| rap | zh_male_rap_mars_bigtts | 说唱 - 男声 |
| en_female | en_female_sarah_conversation_bigtts | 英文女声 |
| en_male | en_male_adam_conversation_bigtts | 英文男声 |

# Bug 反馈

如果在使用过程中遇到任何问题，请通过以下方式反馈：

 - [GitHub Issues](https://github.com/VanillaNahida/doubao-tts-webui/issues)
 - QQ群：
   - [195260107](https://qm.qq.com/q/sUmbgXcUTY) （推荐）
   - [1074471035](https://qm.qq.com/q/eGYIxyLRtu) （闲聊群）

# 致谢

 - 参考了 [callmerio/doubao-tts](https://github.com/callmerio/doubao-tts)  的豆包 WebSocket 接口的逆向分析思路。

# Star History

[![Star History Chart](https://api.star-history.com/svg?repos=VanillaNahida/doubao-tts-webui&type=Date)](https://star-history.com/#VanillaNahida/doubao-tts-webui&Date)
