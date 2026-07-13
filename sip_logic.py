"""
SIP 协议核心逻辑（重用原项目代码，适配 Kivy）
"""
import socket
import hashlib
import re
import json
import time
import threading
import struct
import os
import sys
import random
import queue

# 状态常量
IDLE = "idle"
CALLING = "calling"
RINGING = "ringing"
ANSWERED = "answered"
HUNGUP = "hungup"

# 状态名称
STATE_NAMES = {
    IDLE: "空闲",
    CALLING: "呼叫中",
    RINGING: "振铃",
    ANSWERED: "通话中",
    HUNGUP: "已挂断",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "sip_direct.log")

# 默认配置
LOCAL_SIP_PORT = 5060
LOCAL_IP = "0.0.0.0"
SIP_BUFFER = 8192


def log(msg):
    """日志函数"""
    ts = time.strftime('%H:%M:%S')
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{ts} {msg}\n")
    except:
        pass


def get_local_ip():
    """获取本机 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.254.10.1", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


def generate_branch():
    """生成 SIP branch 参数"""
    return f"z9hG4bK{random.randint(100000, 999999)}"


def generate_tag():
    """生成 SIP tag 参数"""
    return f"{random.randint(10000000, 99999999)}"


def generate_call_id():
    """生成 Call-ID"""
    return f"{random.randint(100000, 999999)}@sipphone"


def md5(s):
    """MD5 哈希"""
    return hashlib.md5(s.encode()).hexdigest()


def parse_sdp(body):
    """解析 SDP 提取音频信息"""
    if not body:
        return None, None
    
    m = re.search(r'm=audio (\d+)', body)
    port = int(m.group(1)) if m else None
    
    a = re.search(r'a=rtpmap:(\d+)', body)
    pt = int(a.group(1)) if a else 0
    
    return port, pt


class DirectSIPPhone:
    """P2P SIP 电话核心类（Kivy 适配版）"""
    
    def __init__(self, local_ip):
        self.local_ip = local_ip
        self.sip_port = LOCAL_SIP_PORT
        self.sock = None
        self.running = False
        self.state = IDLE
        self._state_lock = threading.Lock()
        
        # 回调
        self.on_state_change = None  # (state, reason)
        self.on_incoming = None      # (msg, addr)
        self.on_log = None           # (msg)
        
        # SIP 状态
        self.call_id = None
        self.from_tag = None
        self.to_tag = None
        self.cseq = 0
        self.invite_cseq = 0
        self.peer_ip = None
        self.peer_port = None
        self.peer_contact = None
        self.peer_uri = None
        self._is_incoming_call = False
        
        # RTP
        self.rtp = None
        
        # 音频
        self.audio = None
        
        # 来电/挂断时间戳
        self.ringing_start_time = None
    
    def _update_state(self, new_state, reason=""):
        """更新状态"""
        with self._state_lock:
            if self.state == new_state:
                return
            self.state = new_state
        log(f"【状态】{STATE_NAMES.get(new_state, new_state)} - {reason}")
        if self.on_state_change:
            try:
                self.on_state_change(new_state, reason)
            except:
                pass
        if self.on_log:
            try:
                self.on_log(f"[状态] {STATE_NAMES.get(new_state, new_state)} - {reason}")
            except:
                pass
    
    def _emit_log(self, msg):
        """发送日志"""
        log(msg)
        if self.on_log:
            try:
                self.on_log(msg)
            except:
                pass
    
    def start(self):
        """启动 SIP 监听"""
        if self.running:
            return
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', self.sip_port))
            self.sock.settimeout(0.5)
            self.running = True
            
            self._emit_log(f"【启动】监听端口 {self.sip_port}")
            threading.Thread(target=self._recv_loop, daemon=True).start()
        except Exception as e:
            self._emit_log(f"【启动失败】{e}")
            if self.on_state_change:
                self.on_state_change(IDLE, f"启动失败: {e}")
    
    def stop(self):
        """停止 SIP 监听"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self._cleanup_call()
    
    def _recv_loop(self):
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(SIP_BUFFER)
                if data:
                    msg = data.decode('utf-8', errors='ignore')
                    threading.Thread(target=self._handle_message, args=(msg, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self._emit_log(f"【接收异常】{e}")
                break
    
    def _handle_message(self, msg, addr):
        """处理接收到的消息"""
        first_line = msg.split('\r\n')[0]
        self._emit_log(f"【收到】{first_line} <- {addr[0]}:{addr[1]}")
        
        if msg.startswith('INVITE'):
            self._handle_invite(msg, addr)
        elif msg.startswith('BYE'):
            self._handle_bye(msg, addr)
        elif msg.startswith('CANCEL'):
            self._handle_cancel(msg, addr)
        elif msg.startswith('ACK'):
            self._handle_ack(msg, addr)
        elif msg.startswith('SIP/2.0'):
            self._handle_response(msg, addr)
    
    def _handle_response(self, msg, addr):
        """处理 SIP 响应"""
        lines = msg.split('\r\n')
        status_line = lines[0]
        m = re.match(r'SIP/2.0 (\d+)', status_line)
        if not m:
            return
        code = int(m.group(1))
        
        # 提取 Call-ID
        call_id = self._get_header(msg, 'Call-ID') or self._get_header(msg, 'i')
        
        if code == 200:
            if self.state == CALLING and call_id == self.call_id:
                self._handle_200_ok_invite(msg, addr)
        elif code == 180 or code == 183:
            if self.state == CALLING and call_id == self.call_id:
                self._handle_180_ringing(msg, addr)
        elif code == 487:
            if call_id == self.call_id:
                self._handle_487(msg, addr)
        elif code == 481:
            self._emit_log(f"【481】会话不存在")
            self._update_state(IDLE, "对方已挂断")
        elif code == 407:
            self._emit_log(f"【407】需要认证")
    
    def _handle_200_ok_invite(self, msg, addr):
        """处理 INVITE 200 OK"""
        self._emit_log("【200 OK】对方已接听")
        
        # 提取对方 Contact
        contact = self._get_header(msg, 'Contact') or self._get_header(msg, 'm')
        if contact:
            self.peer_contact = self._extract_uri(contact)
        
        # 发送 ACK
        self._send_ack(addr)
        
        # 解析 SDP
        sdp_start = msg.find('\r\n\r\n') + 4
        sdp_body = msg[sdp_start:] if sdp_start > 4 else ''
        rtp_port, pt = parse_sdp(sdp_body)
        
        if rtp_port:
            # 启动 RTP
            from rtp import RTPSession
            self.rtp = RTPSession(self.local_ip)
            self.rtp.set_remote(addr[0], rtp_port, pt)
            self.rtp.start()
            
            # 启动音频
            self._start_audio()
        
        self._update_state(ANSWERED, "通话中")
    
    def _handle_180_ringing(self, msg, addr):
        """处理 180 Ringing"""
        self._emit_log("【180 Ringing】对方振铃中")
    
    def _handle_487(self, msg, addr):
        """处理 487 响应"""
        self._emit_log("【487】对方取消/拒绝")
        self._update_state(HUNGUP, "对方拒绝/不可用")
    
    def _handle_invite(self, msg, addr):
        """处理 INVITE 请求（来电）"""
        if self.state != IDLE:
            self._emit_log(f"【拒绝 INVITE】当前状态: {self.state}")
            try:
                self.sock.sendto(self._build_response(msg, addr, 486, 'Busy Here').encode(), addr)
            except:
                pass
            return
        
        self._emit_log(f"【INVITE】来电 from {addr[0]}:{addr[1]}")
        
        # 提取 Call-ID
        call_id = self._get_header(msg, 'Call-ID') or self._get_header(msg, 'i')
        if not call_id:
            return
        call_id = call_id.strip()
        
        # 检查重传
        if self.call_id == call_id and self.state in (RINGING, ANSWERED):
            if self.state == ANSWERED:
                # 重传 200 OK
                self._emit_log("【INVITE 重传】重发 200 OK")
                try:
                    self.sock.sendto(self._build_response(msg, addr, 200, 'OK', extra_body=self._last_sdp).encode(), addr)
                except:
                    pass
            return
        
        # 提取 From/To tags
        from_header = self._get_header(msg, 'From') or self._get_header(msg, 'f')
        to_header = self._get_header(msg, 'To') or self._get_header(msg, 't')
        
        if not from_header or not to_header:
            return
        
        from_tag = self._extract_tag(from_header)
        to_tag = generate_tag()
        
        # 解析 SDP
        sdp_start = msg.find('\r\n\r\n') + 4
        sdp_body = msg[sdp_start:] if sdp_start > 4 else ''
        rtp_port, pt = parse_sdp(sdp_body)
        
        # 保存状态
        self.call_id = call_id
        self.from_tag = from_tag
        self.to_tag = to_tag
        self.peer_ip = addr[0]
        self.peer_port = addr[1]
        self.cseq = 1
        self.invite_cseq = 1
        self._is_incoming_call = True
        self._invite_msg = msg  # 保存原始 INVITE 消息
        
        # 提取对方 Contact
        contact = self._get_header(msg, 'Contact') or self._get_header(msg, 'm')
        if contact:
            self.peer_contact = self._extract_uri(contact)
        
        # 发送 180 Ringing
        self._emit_log("【发送 180 Ringing】")
        try:
            self.sock.sendto(self._build_response(msg, addr, 180, 'Ringing').encode(), addr)
        except:
            pass
        
        self._update_state(RINGING, "有来电呼入")
        
        if self.on_incoming:
            try:
                self.on_incoming(msg, addr)
            except:
                pass
    
    def answer_incoming(self):
        """接听来电"""
        if self.state != RINGING:
            return
        
        self._emit_log("【接听】建立通话")
        self._is_incoming_call = True
        
        # 使用保存的原始 INVITE 消息构造 200 OK
        if not hasattr(self, '_invite_msg') or not self._invite_msg:
            self._emit_log("【错误】缺少 INVITE 消息")
            return
        
        # 构造 SDP
        sdp = self._build_sdp()
        self._last_sdp = sdp
        
        # 发送 200 OK
        try:
            resp = self._build_invite_response(self._invite_msg, sdp, 200, 'OK')
            self.sock.sendto(resp.encode(), (self.peer_ip, self.peer_port))
            self._emit_log("【200 OK】已发送")
        except Exception as e:
            self._emit_log(f"【发送 200 OK 失败】{e}")
            return
        
        # 解析原始 SDP 获取 RTP 端口
        from rtp import RTPSession
        sdp_start = self._invite_msg.find('\r\n\r\n') + 4
        orig_sdp = self._invite_msg[sdp_start:] if sdp_start > 4 else ''
        rtp_port, pt = parse_sdp(orig_sdp)
        if not rtp_port:
            rtp_port = 8000
        
        # 启动 RTP
        self.rtp = RTPSession(self.local_ip)
        self.rtp.set_remote(self.peer_ip, rtp_port, pt)
        self.rtp.start()
        
        # 启动音频
        self._start_audio()
        
        self._update_state(ANSWERED, "通话中")
    
    def _build_invite_response(self, invite_msg, sdp, code, reason):
        """构造 INVITE 响应（基于原始 INVITE 消息）"""
        # 提取原始 Via
        orig_via = self._get_header(invite_msg, 'Via') or self._get_header(invite_msg, 'v') or ''
        # 提取原始 branch
        branch_m = re.search(r'branch=([^;\s]+)', orig_via)
        branch = branch_m.group(1) if branch_m else generate_branch()
        
        # RFC 3581: 添加 rport 和 received
        via = f"SIP/2.0/UDP {self.local_ip}:{self.sip_port};branch={branch};rport;received={self.peer_ip}"
        
        # From/To
        from_hdr = self._get_header(invite_msg, 'From') or self._get_header(invite_msg, 'f') or ''
        # To 头需要添加 tag
        to_hdr = self._get_header(invite_msg, 'To') or self._get_header(invite_msg, 't') or ''
        if 'tag=' not in to_hdr:
            to_hdr = f"{to_hdr};tag={self.to_tag}"
        
        call_id = self._get_header(invite_msg, 'Call-ID') or self._get_header(invite_msg, 'i') or self.call_id or ''
        cseq = self._get_header(invite_msg, 'CSeq') or f"{self.invite_cseq} INVITE"
        
        response = f"SIP/2.0 {code} {reason}\r\n"
        response += f"{via}\r\n"
        response += f"{from_hdr}\r\n"
        response += f"{to_hdr}\r\n"
        response += f"Call-ID: {call_id}\r\n"
        response += f"CSeq: {cseq}\r\n"
        response += f"Contact: <sip:{self.local_ip}:{self.sip_port}>\r\n"
        response += f"Content-Type: application/sdp\r\n"
        response += f"Content-Length: {len(sdp)}\r\n"
        response += f"User-Agent: SIPPhone/1.0\r\n"
        response += f"Allow: INVITE, ACK, BYE, CANCEL, OPTIONS, INFO, NOTIFY\r\n"
        response += f"Supported: replaces, timer, outbound\r\n"
        response += f"\r\n"
        response += sdp
        return response
    
    def _handle_bye(self, msg, addr):
        """处理 BYE 请求"""
        self._emit_log("【收到 BYE】对方挂断")
        self._send_response(msg, addr, 200, 'OK')
        self._cleanup_call()
        self._update_state(HUNGUP, "对方已挂断")
    
    def _handle_cancel(self, msg, addr):
        """处理 CANCEL 请求"""
        self._emit_log("【收到 CANCEL】取消呼叫")
        self._send_response(msg, addr, 200, 'OK')
        self._cleanup_call()
        self._update_state(HUNGUP, "已取消")
    
    def _handle_ack(self, msg, addr):
        """处理 ACK 请求"""
        self._emit_log("【收到 ACK】")
    
    def _send_response(self, msg, addr, code, reason):
        """发送响应"""
        try:
            response = self._build_response(msg, addr, code, reason)
            self.sock.sendto(response.encode(), addr)
        except Exception as e:
            self._emit_log(f"【发送响应失败】{e}")
    
    def _build_response(self, msg, addr, code, reason, extra_body=''):
        """构造 SIP 响应"""
        from_header = self._get_header(msg, 'From') or self._get_header(msg, 'f') or ''
        to_header = self._get_header(msg, 'To') or self._get_header(msg, 't') or ''
        call_id = self._get_header(msg, 'Call-ID') or self._get_header(msg, 'i') or ''
        cseq = self._get_header(msg, 'CSeq') or ''
        via = self._get_header(msg, 'Via') or self._get_header(msg, 'v') or ''
        
        response = f"SIP/2.0 {code} {reason}\r\n"
        response += f"{via}\r\n"
        response += f"{from_header}\r\n"
        if to_header and 'tag=' not in to_header:
            to_header = to_header.rstrip() + f";tag={self.to_tag or generate_tag()}"
        response += f"{to_header}\r\n"
        response += f"{call_id}\r\n"
        response += f"{cseq}\r\n"
        if extra_body:
            response += f"Content-Type: application/sdp\r\n"
            response += f"Content-Length: {len(extra_body)}\r\n"
        response += f"User-Agent: SIPPhone/1.0\r\n"
        response += f"\r\n"
        if extra_body:
            response += extra_body
        return response
    
    def _get_header(self, msg, name):
        """提取 SIP 头部"""
        for line in msg.split('\r\n'):
            if line.lower().startswith(name.lower() + ':'):
                return line[len(name) + 1:].strip()
        return None
    
    def _extract_tag(self, header):
        """提取 tag 参数"""
        m = re.search(r'tag=([^\s;]+)', header)
        return m.group(1) if m else ''
    
    def _extract_uri(self, header):
        """提取 URI"""
        m = re.search(r'<([^>]+)>', header)
        if m:
            return m.group(1)
        m = re.search(r'sip:([^\s;]+)', header)
        return f"sip:{m.group(1)}" if m else ''
    
    def _build_sdp(self):
        """构造 SDP"""
        rtp_port = 8000
        sdp = f"v=0\r\n"
        sdp += f"o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}\r\n"
        sdp += f"s=SIPPhone\r\n"
        sdp += f"c=IN IP4 {self.local_ip}\r\n"
        sdp += f"t=0 0\r\n"
        sdp += f"m=audio {rtp_port} RTP/AVP 0\r\n"
        sdp += f"a=rtpmap:0 PCMU/8000\r\n"
        sdp += f"a=sendrecv\r\n"
        return sdp
    
    def call(self, target_ip, target_port=5060):
        """发起呼叫"""
        if self.state != IDLE:
            self._emit_log(f"【呼叫失败】当前状态: {self.state}")
            return
        
        self._update_state(CALLING, f"正在呼叫 {target_ip}")
        
        # 初始化 SIP 状态
        self.peer_ip = target_ip
        self.peer_port = target_port
        self.call_id = generate_call_id()
        self.from_tag = generate_tag()
        self.to_tag = None
        self.cseq = 1
        self.invite_cseq = 1
        self._is_incoming_call = False
        
        # 发送 INVITE
        invite = self._build_invite(target_ip, target_port)
        try:
            self.sock.sendto(invite.encode(), (target_ip, target_port))
            self._emit_log(f"【INVITE】已发送到 {target_ip}:{target_port}")
        except Exception as e:
            self._emit_log(f"【INVITE 发送失败】{e}")
            self._update_state(IDLE, "呼叫失败")
    
    def _build_invite(self, target_ip, target_port):
        """构造 INVITE"""
        branch = generate_branch()
        sdp = self._build_sdp()
        
        invite = f"INVITE sip:{target_ip} SIP/2.0\r\n"
        invite += f"Via: SIP/2.0/UDP {self.local_ip}:{self.sip_port};branch={branch}\r\n"
        invite += f"From: <sip:{self.local_ip}>;tag={self.from_tag}\r\n"
        invite += f"To: <sip:{target_ip}>\r\n"
        invite += f"Call-ID: {self.call_id}\r\n"
        invite += f"CSeq: {self.cseq} INVITE\r\n"
        invite += f"Contact: <sip:{self.local_ip}:{self.sip_port}>\r\n"
        invite += f"Max-Forwards: 70\r\n"
        invite += f"User-Agent: SIPPhone/1.0\r\n"
        invite += f"Content-Type: application/sdp\r\n"
        invite += f"Content-Length: {len(sdp)}\r\n"
        invite += f"\r\n"
        invite += sdp
        return invite
    
    def _send_ack(self, addr):
        """发送 ACK"""
        if not self.call_id:
            return
        
        branch = generate_branch()
        ack = f"ACK sip:{self.peer_ip} SIP/2.0\r\n"
        ack += f"Via: SIP/2.0/UDP {self.local_ip}:{self.sip_port};branch={branch}\r\n"
        ack += f"From: <sip:{self.local_ip}>;tag={self.from_tag}\r\n"
        ack += f"To: <sip:{self.peer_ip}>;tag={self.to_tag}\r\n"
        ack += f"Call-ID: {self.call_id}\r\n"
        ack += f"CSeq: {self.invite_cseq} ACK\r\n"
        ack += f"Max-Forwards: 70\r\n"
        ack += f"User-Agent: SIPPhone/1.0\r\n"
        ack += f"Content-Length: 0\r\n"
        ack += f"\r\n"
        try:
            self.sock.sendto(ack.encode(), addr)
            self._emit_log("【ACK】已发送")
        except Exception as e:
            self._emit_log(f"【ACK 发送失败】{e}")
    
    def hangup(self):
        """挂断通话"""
        if self.state not in (ANSWERED, CALLING, RINGING):
            return
        
        self._emit_log("【挂断】")
        
        if self.call_id and self.peer_ip:
            # 发送 BYE
            branch = generate_branch()
            cseq = self.cseq + 1
            self.cseq = cseq
            
            # 简化 Request-URI
            request_uri = f"sip:{self.peer_ip}"
            
            if self._is_incoming_call:
                # 来电场景：To 是 peer, From 是本机
                from_uri = f"<sip:{self.local_ip}>;tag={self.to_tag}"
                to_uri = f"<sip:{self.peer_ip}>;tag={self.from_tag}"
            else:
                # 主叫场景：To 是 peer, From 是本机
                from_uri = f"<sip:{self.local_ip}>;tag={self.from_tag}"
                to_uri = f"<sip:{self.peer_ip}>;tag={self.to_tag or ''}"
            
            bye = f"BYE {request_uri} SIP/2.0\r\n"
            bye += f"Via: SIP/2.0/UDP {self.local_ip}:{self.sip_port};branch={branch}\r\n"
            bye += f"From: {from_uri}\r\n"
            bye += f"To: {to_uri}\r\n"
            bye += f"Call-ID: {self.call_id}\r\n"
            bye += f"CSeq: {cseq} BYE\r\n"
            bye += f"Max-Forwards: 70\r\n"
            bye += f"User-Agent: SIPPhone/1.0\r\n"
            bye += f"Content-Length: 0\r\n"
            bye += f"\r\n"
            
            try:
                self.sock.sendto(bye.encode(), (self.peer_ip, self.peer_port))
                self._emit_log("【BYE】已发送")
            except Exception as e:
                self._emit_log(f"【BYE 发送失败】{e}")
            
            # 主叫场景下，如果是 CALLING 状态，发送 CANCEL
            if not self._is_incoming_call and self.state == CALLING:
                cancel_branch = generate_branch()
                cancel = f"CANCEL {request_uri} SIP/2.0\r\n"
                cancel += f"Via: SIP/2.0/UDP {self.local_ip}:{self.sip_port};branch={cancel_branch}\r\n"
                cancel += f"From: <sip:{self.local_ip}>;tag={self.from_tag}\r\n"
                cancel += f"To: <sip:{self.peer_ip}>\r\n"
                cancel += f"Call-ID: {self.call_id}\r\n"
                cancel += f"CSeq: 1 CANCEL\r\n"
                cancel += f"Max-Forwards: 70\r\n"
                cancel += f"User-Agent: SIPPhone/1.0\r\n"
                cancel += f"Content-Length: 0\r\n"
                cancel += f"\r\n"
                try:
                    self.sock.sendto(cancel.encode(), (self.peer_ip, self.peer_port))
                except:
                    pass
        
        self._cleanup_call()
        self._update_state(HUNGUP, "已挂断")
    
    def _start_audio(self):
        """启动音频"""
        try:
            from audio_android import create_audio
            
            def on_audio_data(data):
                """接收到麦克风数据"""
                if self.rtp:
                    self.rtp.send_audio(data)
            
            self.audio = create_audio()
            self.audio.start(on_record=on_audio_data)
            
            # 启动 RTP 接收线程，将接收到的音频写入播放缓冲
            threading.Thread(target=self._audio_play_loop, daemon=True).start()
            self._emit_log("【音频】已启动")
        except Exception as e:
            self._emit_log(f"【音频启动失败】{e}")
    
    def _audio_play_loop(self):
        """音频播放循环"""
        while self.running and self.rtp and self.audio:
            try:
                # 从 RTP 接收音频
                if hasattr(self.rtp, 'get_audio'):
                    data = self.rtp.get_audio()
                    if data:
                        self.audio.write(data)
                else:
                    time.sleep(0.02)
            except Exception as e:
                self._emit_log(f"【音频播放异常】{e}")
                break
    
    def _cleanup_call(self):
        """清理通话状态"""
        if self.rtp:
            try:
                self.rtp.stop()
            except:
                pass
            self.rtp = None
        
        if self.audio:
            try:
                self.audio.stop()
            except:
                pass
            self.audio = None
    
    def destroy(self):
        """销毁"""
        self._cleanup_call()
        self.stop()
