"""
WebSocket管理器
实现实时通信功能，支持视频流、音频流和数据传输
"""

import asyncio
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
import base64
import cv2
import numpy as np
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import eventlet

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self, app: Flask):
        """
        初始化WebSocket管理器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='eventlet',
            logger=True,
            engineio_logger=True
        )
        
        # 连接管理
        self.connected_clients: Dict[str, Dict] = {}
        self.rooms: Dict[str, List[str]] = {}
        
        # 数据处理器
        self.data_processors: Dict[str, Callable] = {}
        
        # 实时数据流
        self.video_streams: Dict[str, Any] = {}
        self.audio_streams: Dict[str, Any] = {}
        
        # 状态管理
        self.is_running = False
        self.processing_thread = None
        
        # 注册事件处理器
        self._register_events()
        
    def _register_events(self):
        """注册WebSocket事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """处理客户端连接"""
            client_id = self._get_client_id()
            self.connected_clients[client_id] = {
                'connected_at': time.time(),
                'subscriptions': set(),
                'user_info': {}
            }
            
            logger.info(f"客户端连接: {client_id}")
            emit('connected', {'client_id': client_id})
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """处理客户端断开连接"""
            client_id = self._get_client_id()
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
                
                # 从所有房间中移除
                for room_name, clients in self.rooms.items():
                    if client_id in clients:
                        clients.remove(client_id)
                        
            logger.info(f"客户端断开连接: {client_id}")
            
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """处理加入房间"""
            client_id = self._get_client_id()
            room_name = data.get('room')
            
            if room_name:
                join_room(room_name)
                
                if room_name not in self.rooms:
                    self.rooms[room_name] = []
                    
                if client_id not in self.rooms[room_name]:
                    self.rooms[room_name].append(client_id)
                    
                logger.info(f"客户端 {client_id} 加入房间 {room_name}")
                emit('joined_room', {'room': room_name})
                
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """处理离开房间"""
            client_id = self._get_client_id()
            room_name = data.get('room')
            
            if room_name:
                leave_room(room_name)
                
                if room_name in self.rooms and client_id in self.rooms[room_name]:
                    self.rooms[room_name].remove(client_id)
                    
                logger.info(f"客户端 {client_id} 离开房间 {room_name}")
                emit('left_room', {'room': room_name})
                
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """处理订阅数据流"""
            client_id = self._get_client_id()
            stream_type = data.get('stream_type')
            
            if client_id in self.connected_clients and stream_type:
                self.connected_clients[client_id]['subscriptions'].add(stream_type)
                logger.info(f"客户端 {client_id} 订阅数据流: {stream_type}")
                emit('subscribed', {'stream_type': stream_type})
                
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """处理取消订阅"""
            client_id = self._get_client_id()
            stream_type = data.get('stream_type')
            
            if client_id in self.connected_clients and stream_type:
                self.connected_clients[client_id]['subscriptions'].discard(stream_type)
                logger.info(f"客户端 {client_id} 取消订阅数据流: {stream_type}")
                emit('unsubscribed', {'stream_type': stream_type})
                
        @self.socketio.on('request_data')
        def handle_request_data(data):
            """处理数据请求"""
            client_id = self._get_client_id()
            data_type = data.get('data_type')
            
            if data_type in self.data_processors:
                try:
                    result = self.data_processors[data_type](data)
                    emit('data_response', {
                        'data_type': data_type,
                        'result': result,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    logger.error(f"数据处理失败: {e}")
                    emit('error', {'message': str(e)})
                    
        @self.socketio.on('audio_data')
        def handle_audio_data(data):
            """处理音频数据"""
            client_id = self._get_client_id()
            audio_base64 = data.get('audio_data')
            
            if audio_base64:
                # 处理音频数据
                self._process_audio_data(client_id, audio_base64)
                
        @self.socketio.on('control_command')
        def handle_control_command(data):
            """处理控制命令"""
            client_id = self._get_client_id()
            command = data.get('command')
            params = data.get('params', {})
            
            logger.info(f"收到控制命令: {command} from {client_id}")
            
            # 处理控制命令
            result = self._process_control_command(command, params)
            emit('command_response', {
                'command': command,
                'result': result,
                'timestamp': time.time()
            })
    
    def _get_client_id(self) -> str:
        """获取客户端ID"""
        from flask import request
        return request.sid
    
    def _process_audio_data(self, client_id: str, audio_base64: str):
        """处理音频数据"""
        try:
            # 解码音频数据
            audio_data = base64.b64decode(audio_base64)
            
            # 这里可以集成语音识别功能
            # 例如调用speech_processor进行处理
            
            # 模拟语音识别结果
            recognition_result = {
                'text': '语音识别结果',
                'confidence': 0.95,
                'timestamp': time.time()
            }
            
            self.socketio.emit('speech_recognition_result', recognition_result, room=client_id)
            
        except Exception as e:
            logger.error(f"音频数据处理失败: {e}")
            self.socketio.emit('error', {'message': f'音频处理失败: {str(e)}'}, room=client_id)
    
    def _process_control_command(self, command: str, params: Dict) -> Dict:
        """处理控制命令"""
        try:
            if command == 'start_camera':
                camera_type = params.get('camera_type')
                # 这里可以调用相应的摄像头启动逻辑
                return {'success': True, 'message': f'摄像头 {camera_type} 已启动'}
                
            elif command == 'stop_camera':
                camera_type = params.get('camera_type')
                # 这里可以调用相应的摄像头停止逻辑
                return {'success': True, 'message': f'摄像头 {camera_type} 已停止'}
                
            elif command == 'start_navigation':
                destination = params.get('destination')
                # 这里可以调用导航服务
                return {'success': True, 'message': f'导航到 {destination} 已启动'}
                
            elif command == 'process_3d_audio':
                azimuth_pitch_data = params.get('azimuth_pitch_data', [])
                # 这里可以调用3D音频处理
                return {'success': True, 'message': '3D音频处理完成'}
                
            else:
                return {'success': False, 'message': f'未知命令: {command}'}
                
        except Exception as e:
            logger.error(f"控制命令处理失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def register_data_processor(self, data_type: str, processor: Callable):
        """注册数据处理器"""
        self.data_processors[data_type] = processor
        logger.info(f"注册数据处理器: {data_type}")
    
    def broadcast_data(self, data_type: str, data: Any, room: Optional[str] = None):
        """广播数据到所有订阅的客户端"""
        if room:
            # 发送到指定房间
            self.socketio.emit(data_type, data, room=room)
        else:
            # 发送到所有订阅的客户端
            for client_id, client_info in self.connected_clients.items():
                if data_type in client_info['subscriptions']:
                    self.socketio.emit(data_type, data, room=client_id)
    
    def send_to_client(self, client_id: str, event: str, data: Any):
        """发送数据到指定客户端"""
        if client_id in self.connected_clients:
            self.socketio.emit(event, data, room=client_id)
    
    def start_video_stream(self, stream_name: str, video_source):
        """启动视频流"""
        if stream_name in self.video_streams:
            logger.warning(f"视频流 {stream_name} 已存在")
            return
        
        self.video_streams[stream_name] = {
            'source': video_source,
            'active': True,
            'thread': threading.Thread(target=self._video_stream_worker, args=(stream_name, video_source))
        }
        
        self.video_streams[stream_name]['thread'].daemon = True
        self.video_streams[stream_name]['thread'].start()
        
        logger.info(f"视频流 {stream_name} 已启动")
    
    def stop_video_stream(self, stream_name: str):
        """停止视频流"""
        if stream_name in self.video_streams:
            self.video_streams[stream_name]['active'] = False
            
            # 等待线程结束
            if self.video_streams[stream_name]['thread'].is_alive():
                self.video_streams[stream_name]['thread'].join(timeout=1)
            
            del self.video_streams[stream_name]
            logger.info(f"视频流 {stream_name} 已停止")
    
    def _video_stream_worker(self, stream_name: str, video_source):
        """视频流工作线程"""
        try:
            while self.video_streams.get(stream_name, {}).get('active', False):
                # 获取视频帧
                frame = self._get_video_frame(video_source)
                
                if frame is not None:
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # 广播视频帧
                    self.broadcast_data('video_frame', {
                        'stream_name': stream_name,
                        'frame_data': frame_base64,
                        'timestamp': time.time()
                    })
                
                # 控制帧率
                time.sleep(1/30)  # 30 FPS
                
        except Exception as e:
            logger.error(f"视频流 {stream_name} 工作线程错误: {e}")
    
    def _get_video_frame(self, video_source):
        """获取视频帧"""
        # 这里应该根据video_source的类型获取实际的视频帧
        # 暂时返回None
        return None
    
    def start_real_time_processing(self):
        """启动实时数据处理"""
        if self.is_running:
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._real_time_processing_worker)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("实时数据处理已启动")
    
    def stop_real_time_processing(self):
        """停止实时数据处理"""
        self.is_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1)
        
        logger.info("实时数据处理已停止")
    
    def _real_time_processing_worker(self):
        """实时数据处理工作线程"""
        while self.is_running:
            try:
                # 生成模拟数据
                system_status = {
                    'timestamp': time.time(),
                    'collision_probability': np.random.random() * 100,
                    'detected_objects': [
                        {
                            'name': 'person',
                            'distance': np.random.random() * 50,
                            'angle': np.random.random() * 360
                        }
                    ],
                    'system_health': {
                        'cpu_usage': np.random.random() * 100,
                        'memory_usage': np.random.random() * 100,
                        'gpu_usage': np.random.random() * 100
                    }
                }
                
                # 广播系统状态
                self.broadcast_data('system_status', system_status)
                
                # 生成3D音频数据
                audio_data = {
                    'timestamp': time.time(),
                    'azimuth_pitch_data': [
                        ['person', 15.0, -5.0, 150.0]
                    ],
                    'audio_visualization': {
                        'left_channel': [np.random.random() * 100 for _ in range(20)],
                        'right_channel': [np.random.random() * 100 for _ in range(20)]
                    }
                }
                
                # 广播音频数据
                self.broadcast_data('audio_data', audio_data)
                
                # 等待2秒
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"实时数据处理错误: {e}")
                time.sleep(1)
    
    def get_status(self) -> Dict:
        """获取WebSocket管理器状态"""
        return {
            'connected_clients': len(self.connected_clients),
            'active_rooms': len(self.rooms),
            'video_streams': len(self.video_streams),
            'audio_streams': len(self.audio_streams),
            'is_running': self.is_running,
            'data_processors': list(self.data_processors.keys())
        }
    
    def run(self, host='0.0.0.0', port=5001, debug=False):
        """运行WebSocket服务"""
        logger.info(f"WebSocket服务启动在 {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)


# 全局WebSocket管理器实例
websocket_manager = None

def init_websocket_manager(app: Flask) -> WebSocketManager:
    """初始化WebSocket管理器"""
    global websocket_manager
    websocket_manager = WebSocketManager(app)
    return websocket_manager

def get_websocket_manager() -> Optional[WebSocketManager]:
    """获取WebSocket管理器实例"""
    return websocket_manager 