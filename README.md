# SIP Phone - Kivy Android 版本

国贸游泳馆值班呼叫系统 - Android 客户端

## 项目结构

```
sip_direct_kivy/
├── main.py              # Kivy 应用入口
├── sipphone.kv          # Kivy 界面定义
├── sip_logic.py         # SIP 协议核心逻辑
├── audio_android.py     # Android 音频处理（pyjnius）
├── g711a.py             # G.711 编解码
├── rtp.py               # RTP 会话
├── buildozer.spec       # Buildozer 打包配置
├── .github/
│   └── workflows/
│       └── build.yml    # GitHub Actions 自动构建
└── README.md
```

## 快速开始

### 方式一：GitHub Actions 自动构建（推荐）

1. **创建 GitHub 仓库**
   ```bash
   cd sip_direct_kivy
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/你的用户名/sipphone.git
   git push -u origin main
   ```

2. **配置 Android 签名密钥**（发布版本需要）
   - 在 GitHub 仓库 Settings → Secrets 添加：
     - `BUILDZOOZER_USERNAME`: Android keystore 别名
     - `BUILDZOOZER_KEY`: Base64 编码的 keystore 文件

3. **触发构建**
   - 推送代码后自动构建
   - 或手动触发：Actions → Build Android APK → Run workflow

4. **下载 APK**
   - 构建完成后在 Artifacts 中下载

### 方式二：本地构建（需要 Linux/macOS）

```bash
# 安装依赖
pip install buildozer cython pillow
sudo apt install ffmpeg libgstreamer1.0-dev gstreamer1.0-plugins-good

# 打包
buildozer android debug

# 输出: bin/sipphone-*-debug.apk
```

### 方式三：桌面测试

```bash
pip install kivy==2.1.0 pyaudio
python main.py
```

## 功能特性

| 功能 | 状态 |
|------|------|
| 发起呼叫 | ✅ |
| 接听来电 | ✅ |
| 挂断通话 | ✅ |
| 来电振铃 | ✅ |
| 双向音频 | ✅ |
| SIP 信令 | ✅ |
| RTP 传输 | ✅ |
| G.711 PCMU 编解码 | ✅ |
| Android 权限管理 | ✅ |

## Android 权限

| 权限 | 用途 |
|------|------|
| `INTERNET` | SIP 网络通信 |
| `RECORD_AUDIO` | 麦克风采集 |
| `MODIFY_AUDIO_SETTINGS` | 音频模式切换 |
| `WAKE_LOCK` | 通话保持唤醒 |
| `ACCESS_NETWORK_STATE` | 网络状态检测 |
| `ACCESS_WIFI_STATE` | Wi-Fi 状态检测 |

## 配置说明

### 目标 IP 地址

在应用中输入目标 IP 地址，默认为 `10.254.10.169`

### SIP 端口

默认为 `5060`

## 技术栈

- **UI**: Kivy 2.1.0
- **音频**: pyjnius (Android) / pyaudio (桌面)
- **打包**: Buildozer
- **SIP 协议**: RFC 3261
- **音频编码**: G.711 PCMU (RFC 4855)
- **RTP**: RFC 3550
