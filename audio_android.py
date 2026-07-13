"""
Android 音频处理模块
使用 pyjnius 调用 Android AudioRecord/AudioTrack
"""
import threading
import struct
import os
import sys
from queue import Queue

# 尝试导入 pyjnius（仅在 Android 上可用）
try:
    from jnius import autoclass
    PYJNIUS_AVAILABLE = True
except ImportError:
    PYJNIUS_AVAILABLE = False
    print("pyjnius 不可用，请使用 pyaudio 替代或在 Android 上运行")


class AndroidAudio:
    """Android 音频录制/播放类"""
    
    SAMPLE_RATE = 8000
    CHANNELS = 1
    SAMPLE_SIZE = 2  # 16-bit
    BUFFER_SIZE = 160  # 20ms @ 8kHz
    
    def __init__(self):
        self.is_recording = False
        self.is_playing = False
        self._record_thread = None
        self._play_thread = None
        self._play_buffer = bytearray()
        self._play_lock = threading.Lock()
        
        # 回调
        self.on_record = None  # 接收到麦克风数据时回调
        
        if not PYJNIUS_AVAILABLE:
            print("警告: pyjnius 不可用，Android 音频功能将不可用")
            return
        
        try:
            self.AudioRecord = autoclass('android.media.AudioRecord')
            self.AudioTrack = autoclass('android.media.AudioTrack')
            self.MediaRecorder = autoclass('android.media.MediaRecorder$AudioSource')
            self.AudioFormat = autoclass('android.media.AudioFormat')
            self.AudioManager = autoclass('android.media.AudioManager')
            
            # PCM_16BIT
            self.ENCODING_PCM_16BIT = self.AudioFormat.ENCODING_PCM_16BIT
            self.CHANNEL_IN_MONO = self.AudioFormat.CHANNEL_IN_MONO
            self.CHANNEL_OUT_MONO = self.AudioFormat.CHANNEL_OUT_MONO
            
            # 获取最小缓冲区大小
            self.min_buf_size = self.AudioRecord.getMinBufferSize(
                self.SAMPLE_RATE,
                self.CHANNEL_IN_MONO,
                self.ENCODING_PCM_16BIT
            )
            if self.min_buf_size == -1 or self.min_buf_size == -2:
                self.min_buf_size = self.BUFFER_SIZE * 4
                
        except Exception as e:
            print(f"Android 音频初始化失败: {e}")
            PYJNIUS_AVAILABLE = False
    
    def start(self, on_record=None):
        """启动音频（录音+播放）"""
        if not PYJNIUS_AVAILABLE:
            return False
        
        self.on_record = on_record
        
        # 启动播放
        try:
            self.audio_track = self.AudioTrack(
                self.MODE_STREAM if hasattr(self, 'MODE_STREAM') else 1,
                self.SAMPLE_RATE,
                self.CHANNEL_OUT_MONO,
                self.ENCODING_PCM_16BIT,
                self.min_buf_size * 2,
                1  # MODE_STREAM
            )
            self.audio_track.play()
            self.is_playing = True
            self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
            self._play_thread.start()
        except Exception as e:
            print(f"启动播放失败: {e}")
            return False
        
        # 启动录音
        try:
            self.audio_record = self.AudioRecord(
                self.MediaRecorder.VOICE_COMMUNICATION,
                self.SAMPLE_RATE,
                self.CHANNEL_IN_MONO,
                self.ENCODING_PCM_16BIT,
                self.min_buf_size * 2
            )
            self.audio_record.startRecording()
            self.is_recording = True
            self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self._record_thread.start()
        except Exception as e:
            print(f"启动录音失败: {e}")
            return False
        
        return True
    
    def stop(self):
        """停止音频"""
        self.is_recording = False
        self.is_playing = False
        
        if hasattr(self, 'audio_record') and self.audio_record:
            try:
                self.audio_record.stop()
                self.audio_record.release()
            except:
                pass
            self.audio_record = None
        
        if hasattr(self, 'audio_track') and self.audio_track:
            try:
                self.audio_track.stop()
                self.audio_track.release()
            except:
                pass
            self.audio_track = None
    
    def _record_loop(self):
        """录音线程循环"""
        while self.is_recording and hasattr(self, 'audio_record') and self.audio_record:
            try:
                buf = bytearray(self.min_buf_size)
                read_size = self.audio_record.read(buf, 0, self.min_buf_size)
                if read_size > 0 and self.on_record:
                    audio_data = bytes(buf[:read_size])
                    self.on_record(audio_data)
            except Exception as e:
                print(f"录音异常: {e}")
                break
    
    def _play_loop(self):
        """播放线程循环"""
        while self.is_playing and hasattr(self, 'audio_track') and self.audio_track:
            try:
                with self._play_lock:
                    if len(self._play_buffer) >= self.BUFFER_SIZE * 2:
                        chunk = bytes(self._play_buffer[:self.BUFFER_SIZE * 2])
                        del self._play_buffer[:self.BUFFER_SIZE * 2]
                    else:
                        chunk = b'\x00' * (self.BUFFER_SIZE * 2)
                
                if len(chunk) == self.BUFFER_SIZE * 2:
                    self.audio_track.write(chunk, 0, len(chunk))
            except Exception as e:
                print(f"播放异常: {e}")
                break
    
    def write(self, audio_data):
        """写入要播放的音频数据"""
        with self._play_lock:
            self._play_buffer.extend(audio_data)
    
    def clear_buffer(self):
        """清空播放缓冲"""
        with self._play_lock:
            self._play_buffer = bytearray()


class DesktopAudio:
    """桌面测试用的音频替代类（使用 pyaudio）"""
    
    def __init__(self):
        try:
            import pyaudio
            self.pa = pyaudio.PyAudio()
            self.in_stream = None
            self.out_stream = None
            self._play_buffer = bytearray()
            self._play_lock = threading.Lock()
            self._callback_count = 0
            self._playing = False
            self.PACKET_BYTES = 320
            self.PREBUFFER_PACKETS = 5
            self.running = False
            self.on_record = None
            self.silence_320 = b'\x00' * self.PACKET_BYTES
        except ImportError:
            raise ImportError("请安装 pyaudio")
    
    def start(self, on_record=None):
        self.running = True
        self.on_record = on_record
        
        # 获取默认设备
        try:
            default_input = self.pa.get_default_input_device_info()
            in_channels = min(default_input.get('maxInputChannels', 2), 2)
            self._in_channels = in_channels
        except:
            in_channels = 2
            self._in_channels = 2
        
        self.in_stream = self.pa.open(
            format=8,  # paInt16
            channels=in_channels,
            rate=8000,
            input=True,
            frames_per_buffer=160,
            stream_callback=self._in_callback
        )
        self.out_stream = self.pa.open(
            format=8,  # paInt16
            channels=1,
            rate=8000,
            output=True,
            frames_per_buffer=160,
            stream_callback=self._out_callback
        )
        self.in_stream.start_stream()
        self.out_stream.start_stream()
    
    def stop(self):
        self.running = False
        self._playing = False
        with self._play_lock:
            self._play_buffer = bytearray()
        for s in [self.in_stream, self.out_stream]:
            if s and s.is_active():
                try: s.stop_stream()
                except: pass
                try: s.close()
                except: pass
    
    def _in_callback(self, in_data, frame_count, time_info, status):
        if self.running and self.on_record:
            in_channels = getattr(self, '_in_channels', 2)
            raw = struct.unpack(f'<{len(in_data)//2}h', in_data)
            if in_channels == 2 and len(raw) == frame_count * 2:
                mono_samples = [(raw[i] + raw[i+1]) // 2 for i in range(0, len(raw), 2)]
                mono = struct.pack(f'<{len(mono_samples)}h', *mono_samples)
            else:
                mono = in_data
            self.on_record(mono)
            return (mono, 1)  # paContinue
        return (in_data if in_data else self.silence_320, 1)
    
    def _out_callback(self, in_data, frame_count, time_info, status):
        needed = frame_count * 2
        if not self.running:
            return (self.silence_320, 2)  # paAbort
        
        with self._play_lock:
            if not self._playing:
                if len(self._play_buffer) >= self.PREBUFFER_PACKETS * self.PACKET_BYTES:
                    self._playing = True
                else:
                    return (self.silence_320, 1)
            
            if len(self._play_buffer) >= needed:
                data = bytes(self._play_buffer[:needed])
                del self._play_buffer[:needed]
            else:
                data = bytes(self._play_buffer) + b'\x00' * (needed - len(self._play_buffer))
                self._play_buffer = bytearray()
        
        return (data, 1)
    
    def write(self, audio_data):
        with self._play_lock:
            self._play_buffer.extend(audio_data)
    
    def clear_buffer(self):
        with self._play_lock:
            self._play_buffer = bytearray()


def create_audio():
    """创建音频实例"""
    if PYJNIUS_AVAILABLE and sys.platform != 'win32':
        return AndroidAudio()
    else:
        return DesktopAudio()
