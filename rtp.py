"""
RTP sender/receiver for G.711 audio (PCMU/PCMA)
"""
import socket, struct, time, random, threading

# Import both decoders
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from g711a import alaw_decode, ulaw_decode

class RTPSession:
    def __init__(self, local_ip, local_port, remote_ip, remote_port, payload_type=0):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.payload_type = payload_type  # 0 = PCMU, 8 = PCMA
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.seq_num = random.randint(0, 65535)
        self.timestamp = random.randint(0, 0xFFFFFFFF)
        self._silence_start = None  # track continuous silence
        self.on_silence_timeout = None  # callback when silence exceeds threshold
        self.on_voice_detected = None  # callback() when real speech detected
        self._voice_start = None  # track continuous voice
        self.sample_rate = 8000
        self.frame_size = 160  # 20ms of 8000Hz = 160 samples
        self.packet_count = 0
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((local_ip, local_port))
        self.sock.settimeout(0.5)
        
        self.running = False
        self.on_audio = None  # callback(pcm_samples) for received audio
        self.on_timeout = None  # callback() when no RTP for 5 seconds
        self._recv_thread = None
        self._last_recv_time = 0
        self._timeout_threshold = 15.0  # 15 seconds
    
    def start(self):
        self.running = True
        self._last_recv_time = time.time()
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
    
    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        if self._recv_thread:
            self._recv_thread.join(timeout=1)
    
    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if len(data) < 12:
                    continue
                self._last_recv_time = time.time()
                
                # Parse RTP header
                pt = data[1] & 0x7F  # Payload type from byte 1
                seq = struct.unpack('>H', data[2:4])[0]
                if self.packet_count % 100 == 0:
                    print(f"[RTP] Recv packet from {addr}, seq={seq}, pt={pt}")
                
                if self.on_audio:
                    payload = data[12:]
                    if payload:
                        # Debug: print first 5 packets raw payload
                        if self.packet_count < 5:
                            import os
                            debug_log = os.path.join(os.path.dirname(__file__), 'rtp_debug.log')
                            with open(debug_log, 'a') as f:
                                f.write(f"pkt#{self.packet_count} hex={payload[:20].hex()} unique={len(set(payload))} len={len(payload)}\n")
                        # 只接受 PCMU (pt=0),拒绝 PCMA (pt=8)
                        is_silence = False
                        if pt == 0:  # PCMU
                            unique = len(set(payload[:80]))  # check first 80 bytes (10ms)
                            is_silence = unique <= 2  # only 1-2 unique values = silence
                        else:
                            print(f"[RTP] 丢弃非 PCMU 包, pt={pt}")
                            continue  # 跳过非 PCMU 包
                            unique = len(set(payload[:80]))
                            is_silence = unique <= 2
                        
                        if is_silence:
                            if self._silence_start is None:
                                self._silence_start = time.time()
                            elif time.time() - self._silence_start > 5 and self.on_silence_timeout:
                                print(f"[RTP] 5s continuous silence - likely not answered")
                                try: self.on_silence_timeout()
                                except: pass
                                self._silence_start = None  # prevent re-trigger
                        else:
                            self._silence_start = None  # reset on real audio
                        
                        # Decode based on payload type
                        if pt == 0:
                            samples = ulaw_decode(payload)  # PCMU
                        elif pt == 8:
                            samples = alaw_decode(payload)  # PCMA
                        else:
                            continue  # Unknown codec, skip
                        
                        # Voice activity detection: real speech has higher energy than IVR prompts
                        if not is_silence and self.on_voice_detected:
                            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                            if rms > 200:  # threshold: ~-26dB, real speech is typically 500-3000
                                if self._voice_start is None:
                                    self._voice_start = time.time()
                                elif time.time() - self._voice_start > 0.5:  # 0.5s sustained voice
                                    print(f"[RTP] Voice detected (rms={rms:.0f})")
                                    try: self.on_voice_detected()
                                    except: pass
                                    self.on_voice_detected = None  # fire once
                                    self._voice_start = None
                            else:
                                self._voice_start = None  # too quiet, reset
                        
                        self.on_audio(samples)
            except socket.timeout:
                # Check for timeout
                elapsed = time.time() - self._last_recv_time
                if self._last_recv_time > 0 and elapsed > self._timeout_threshold:
                    print(f"[RTP] Timeout! No data for {elapsed:.1f}s")
                    if self.on_timeout:
                        try:
                            self.on_timeout()
                        except Exception as e:
                            print(f"[RTP] on_timeout error: {e}")
                        self._last_recv_time = time.time()  # prevent multiple triggers
                continue
            except OSError:
                break
            except Exception as e:
                pass  # ignore decode errors
    
    def send_audio(self, alaw_data):
        """Send G.711a encoded audio as RTP"""
        m_bit = 0
        header = struct.pack('>BBHII',
            0x80,
            (m_bit << 7) | self.payload_type,
            self.seq_num,
            self.timestamp,
            self.ssrc
        )
        try:
            self.sock.sendto(header + alaw_data, (self.remote_ip, self.remote_port))
            self.packet_count += 1
            if self.packet_count % 500 == 0:  # Log every 500 packets (~10 seconds)
                print(f"[RTP] Sent {self.packet_count} packets to {self.remote_ip}:{self.remote_port}")
        except Exception as e:
            pass
        
        self.seq_num = (self.seq_num + 1) & 0xFFFF
        self.timestamp = (self.timestamp + self.frame_size) & 0xFFFFFFFF
