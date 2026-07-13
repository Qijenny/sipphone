"""
SIP Phone - Kivy 主程序
国贸游泳馆值班呼叫系统
可在 Android 上运行（使用 Buildozer 打包）
"""
import os
import sys
import threading
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform

# 加载 .kv 文件
Builder.load_file(os.path.join(os.path.dirname(__file__), 'sipphone.kv'))

# 导入 SIP 逻辑
from sip_logic import (
    DirectSIPPhone, IDLE, CALLING, RINGING, ANSWERED, HUNGUP,
    STATE_NAMES, get_local_ip, log
)

# Android 权限申请
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.INTERNET,
            Permission.RECORD_AUDIO,
            Permission.MODIFY_AUDIO_SETTINGS,
            Permission.WAKE_LOCK,
            Permission.ACCESS_NETWORK_STATE,
        ])
    except ImportError:
        pass


class RootWidget(BoxLayout):
    """根容器"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phone = None
        self.log_lines = []
        self._max_log_lines = 200
    
    def on_call(self):
        """呼叫按钮回调"""
        ip = self.ids.input_ip.text.strip()
        port_text = self.ids.input_port.text.strip()
        try:
            port = int(port_text) if port_text else 5060
        except:
            port = 5060
        
        if not ip:
            self._append_log("❌ 请输入目标 IP")
            return
        
        if self.phone:
            self.phone.call(ip, port)
    
    def on_answer(self):
        """接听按钮回调"""
        if self.phone:
            self.phone.answer_incoming()
    
    def on_hangup(self):
        """挂断按钮回调"""
        if self.phone:
            self.phone.hangup()
    
    def init_phone(self, local_ip):
        """初始化电话"""
        self.phone = DirectSIPPhone(local_ip)
        
        # 设置回调
        self.phone.on_state_change = self._on_state_change
        self.phone.on_incoming = self._on_incoming
        self.phone.on_log = self._on_log
        
        # 启动
        self.phone.start()
        
        # 更新 IP 显示
        self.ids.lbl_ip.text = f"本机 IP: {local_ip}  |  SIP: {self.phone.sip_port}"
    
    def _on_state_change(self, state, reason):
        """状态变化回调（需要在线程安全的方式调用）"""
        Clock.schedule_once(lambda dt: self._update_state_ui(state, reason), 0)
    
    def _on_incoming(self, msg, addr):
        """来电回调"""
        Clock.schedule_once(lambda dt: self._update_state_ui(RINGING, "有来电呼入"), 0)
    
    def _on_log(self, msg):
        """日志回调"""
        Clock.schedule_once(lambda dt: self._append_log(msg), 0)
    
    def _update_state_ui(self, state, reason=""):
        """更新 UI 状态"""
        name = STATE_NAMES.get(state, state)
        text = f"状态: {name}"
        if reason:
            text += f" - {reason}"
        
        self.ids.lbl_status.text = text
        
        # 按钮状态
        if state == IDLE:
            self.ids.btn_call.disabled = False
            self.ids.btn_answer.disabled = True
            self.ids.btn_hangup.disabled = True
        elif state == CALLING:
            self.ids.btn_call.disabled = True
            self.ids.btn_answer.disabled = True
            self.ids.btn_hangup.disabled = False
        elif state == RINGING:
            self.ids.btn_call.disabled = True
            self.ids.btn_answer.disabled = False
            self.ids.btn_hangup.disabled = True
        elif state == ANSWERED:
            self.ids.btn_call.disabled = True
            self.ids.btn_answer.disabled = True
            self.ids.btn_hangup.disabled = False
        elif state == HUNGUP:
            self.ids.btn_call.disabled = False
            self.ids.btn_answer.disabled = True
            self.ids.btn_hangup.disabled = True
        
        self._append_log(text)
    
    def _append_log(self, msg):
        """添加日志"""
        ts = time.strftime('%H:%M:%S')
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        if len(self.log_lines) > self._max_log_lines:
            self.log_lines = self.log_lines[-self._max_log_lines:]
        
        self.ids.lbl_log.text = '\n'.join(self.log_lines)
        # 滚动到底部
        if hasattr(self.ids, 'log_scroll'):
            self.ids.log_scroll.scroll_y = 0


class SIPPhoneApp(App):
    """主应用"""
    
    def build(self):
        self.title = "国贸游泳馆值班呼叫系统"
        
        # 创建根窗口
        root = RootWidget()
        
        # 异步获取 IP 并初始化
        def _async_init():
            time.sleep(0.5)  # 等 UI 完全加载
            local_ip = get_local_ip()
            Clock.schedule_once(lambda dt: root.init_phone(local_ip), 0)
        
        threading.Thread(target=_async_init, daemon=True).start()
        
        return root
    
    def on_pause(self):
        """Android 后台时"""
        return True
    
    def on_resume(self):
        """Android 恢复时"""
        pass


if __name__ == '__main__':
    SIPPhoneApp().run()
