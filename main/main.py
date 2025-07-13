'''
    现在我要接九个接口，也就是对应着9个程序
    现在目前的操作
    在某个页面中点击了打开摄像头，那么摄像头处于被调用状态
    并且现在所有的页面的img-src都是指向5002端口
    所以现在我需要把端口分化
'''

# 确保eventlet的monkey_patch在其他所有导入之前
import eventlet
eventlet.monkey_patch()

import os
import time
import datetime
import json
import atexit
import cv2
import numpy as np
import logging
from typing import Callable
from flask import Flask, request, jsonify, Response, send_from_directory, abort, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# 设置logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 引入各类视频流
try:
    from utils.disparity_estimator import DisparityEstimator
    from utils.gesture_point_recognition import GesturePointRecognition
    from utils.gesture_recognizer import GestureRecognizer
    from utils.moblie_net_SSD_detector import OakDMobileNetSSD
    from utils.person_detection_tracker_on_video import PersonDetectionTrackerOnVideo
    from utils.spatial_object_tracker_on_RGB import SpatialObjectTracker
    from utils.feature_point_detector import FeaturePointDetector
    from utils.feature_point_tracker import FeaturePointTracker
    from utils.enhanced_detector import EnhancedDetector
    
    # 检查各个类是否成功导入
    modules_available = {
        'DisparityEstimator': 'DisparityEstimator' in locals(),
        'GesturePointRecognition': 'GesturePointRecognition' in locals(),
        'GestureRecognizer': 'GestureRecognizer' in locals(),
        'OakDMobileNetSSD': 'OakDMobileNetSSD' in locals(),
        'PersonDetectionTrackerOnVideo': 'PersonDetectionTrackerOnVideo' in locals(),
        'SpatialObjectTracker': 'SpatialObjectTracker' in locals(),
        'FeaturePointDetector': 'FeaturePointDetector' in locals(),
        'FeaturePointTracker': 'FeaturePointTracker' in locals()
    }
    
    # 只有当所有模块都成功导入时，才将video_modules_available设为True
    video_modules_available = all(modules_available.values())
    
    if not video_modules_available:
        missing_modules = [module for module, available in modules_available.items() if not available]
        print(f"以下模块导入失败: {', '.join(missing_modules)}")
except Exception as e:
    print(f"导入视频流模块时出错: {e}")
    print("部分功能可能不可用")
    video_modules_available = False
    modules_available = {
        'DisparityEstimator': False,
        'GesturePointRecognition': False,
        'GestureRecognizer': False,
        'OakDMobileNetSSD': False,
        'PersonDetectionTrackerOnVideo': False,
        'SpatialObjectTracker': False,
        'FeaturePointDetector': False,
        'FeaturePointTracker': False
    }

# 导入轨迹追踪和碰撞预警管理器
try:
    from utils.trajectory_collision_manager import trajectory_collision_manager
    print("轨迹追踪和碰撞预警管理器导入成功")
except Exception as e:
    print(f"导入轨迹追踪和碰撞预警管理器失败: {e}")
    trajectory_collision_manager = None

# 导入设备管理器
from utils.device_manager import device_manager

# 创建通用的线程化视频流函数
def create_threaded_video_stream(stream_id: str, source_func: Callable, response_headers: dict = None):
    """创建线程化的视频流响应"""
    def generate():
        client_id = None
        try:
            # 获取或创建视频流
            stream = thread_manager.get_stream(stream_id)
            if stream is None:
                stream = thread_manager.create_stream(stream_id, source_func, max_buffer_size=5)
            
            # 添加客户端连接
            client_id = stream.add_client()
            
            while True:
                # 非阻塞获取帧
                frame_data = stream.get_frame(timeout=0.1)
                
                if frame_data is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                else:
                    # 没有帧时短暂休眠
                    time.sleep(0.033)  # ~30fps
                    
        except GeneratorExit:
            # 客户端断开连接
            pass
        except Exception as e:
            logger.error(f"视频流 {stream_id} 生成错误: {e}")
        finally:
            # 清理客户端连接
            if client_id and stream:
                stream.remove_client(client_id)
    
    # 设置响应头
    headers = {
        'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Connection': 'keep-alive'
    }
    
    if response_headers:
        headers.update(response_headers)
    
    return Response(generate(), headers=headers)

# 导入线程管理器
try:
    from utils.thread_manager import thread_manager
    print("线程管理器导入成功")
except Exception as e:
    print(f"导入线程管理器失败: {e}")
    thread_manager = None

# 添加防重复请求机制
request_timestamps = {
    'd_estimator': {'start': 0, 'stop': 0},
    'f_detector': {'start': 0, 'stop': 0},
    'f_tracker': {'start': 0, 'stop': 0},
    'g_recognition': {'start': 0, 'stop': 0},
    'g_recognizer': {'start': 0, 'stop': 0},
    'm_detector': {'start': 0, 'stop': 0},
    'p_video': {'start': 0, 'stop': 0},
    's_RGB': {'start': 0, 'stop': 0},
}
MIN_REQUEST_INTERVAL = 1.0  # 最小请求间隔时间（秒）

d_estimator = None
f_detector = None
f_tracker = None
g_recognition = None
g_recognizer = None
m_detector = None
p_video = None
s_RGB = None
enhanced_detector = None  # 增强检测器

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# 通用视频流处理函数（移除旧版本，使用新的线程管理器）

# 添加响应头，禁用缓存
@app.after_request
def add_header(response):
    """
    添加响应头，禁用缓存
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# 检查请求频率，防止重复请求
def check_request_rate(module, action):
    """
    检查请求频率，防止重复请求
    返回 True 表示请求可以处理
    返回 False 表示请求应该被拒绝
    """
    current_time = time.time()
    last_request_time = request_timestamps.get(module, {}).get(action, 0)
    
    if current_time - last_request_time < MIN_REQUEST_INTERVAL:
        print(f"请求过于频繁: {module}/{action}")
        return False
    
    # 更新时间戳
    if module in request_timestamps:
        request_timestamps[module][action] = current_time
    
    return True

try:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:wangzishu@localhost:3306/Guidelight_UserData'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用对象修改追踪（可选）
    if 'db' not in globals():
        db = SQLAlchemy(app)
    db_available = True
except Exception as e:
    print(f"数据库连接错误: {e}")
    print("使用SQLite作为备用数据库")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if 'db' not in globals():
        db = SQLAlchemy(app)
    db_available = False


# 用户数据类
class userdata(db.Model):
    __tablename__ = 'userdata'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    category = db.Column(db.String(120), nullable=False)

# 位置信息表模型
class LocationData(db.Model):
    __tablename__ = 'location'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    longitude = db.Column(db.Float(precision=53), nullable=False)
    latitude = db.Column(db.Float(precision=53), nullable=False)
    
    def to_dict(self):
        """将模型转换为字典"""
        return {
            'id': self.id,
            'time': self.time.isoformat() if self.time else None,
            'timestamp': time.mktime(self.time.timetuple()) if self.time else None,
            'lng': self.longitude,
            'lat': self.latitude
        }


# 检测用户是否存在
def exist(username):
    user = userdata.query.filter_by(name=username).first()
    if user:
        return True
    return False


# 注册
'''
    POST /register
    json:
    {
        "username": "admin",
        "password": "admin",
        "category": "admin"
    }
'''

# 注册
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    category = data.get('category')
    print(username, password, category)
    # 在这里进行注册逻辑，比如检查用户名是否已存在，密码是否符合要求等
    # 如果注册成功，返回一个包含成功信息的JSON响应
    # 如果注册失败，返回一个包含错误信息的JSON响应
    if exist(username):
        return jsonify({'message': '用户名已存在'}), 201
    else:
        new_user = userdata(name=username, password=generate_password_hash(password), category=category)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': '注册成功'}), 201


# 登录
@app.route('/login', methods=['POST'])
def login():
    # 接收消息
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    print(username, password)
    # 检查用户名和密码是否正确
    try:
        if exist(username):
            print("开始登录")

        user = userdata.query.filter_by(name=username).first()
        if check_password_hash(user.password, password):
            # 记录操作的所有信息到另一个数据库
            new_log = userdata(name=username, password='', category="login")
            db.session.add(new_log)
            db.session.commit()
            return jsonify({'message': '登录成功'}), 200
    except Exception as e:
        print(f"登录失败: {str(e)}")
        return jsonify({'message': f'登录失败: {str(e)}'}), 500
    return jsonify({'message': '用户名或密码错误'}), 201


# 工作日志（历史操作记录）
'''
    json:
    {
        "username": "admin",
        created_at: "admin",
        "category": "admin"
        
    }
    
'''


@app.route('/record', methods=['POST'])
def record():
    # 接收消息
    data = request.get_json()
    username = data.get('username')
    users = userdata.query.filter_by(name=username).all()
    if users:
        # 将查询结果转换为字典形式
        user_data = [{'id': user.id, 'name': user.name, 'password': user.password, 'category': user.category,
                      'created_at': user.created_at} for user
                     in users]
        return jsonify(user_data)
    else:
        print('No users found')
        return jsonify({'message': f'No users found with name {username}'}), 404

# 位置相关API
@app.route('/location', methods=['GET'])
def get_location():
    """获取最新位置信息"""
    try:
        # 获取最新的位置记录
        latest_location = LocationData.query.order_by(LocationData.time.desc()).first()
        
        if latest_location:
            return jsonify({
                "code": 200,
                "data": [latest_location.to_dict()]
            })
        else:
            # 如果没有位置记录，返回默认位置（合肥工业大学屯溪路校区）
            default_location = {
                "name": "合肥工业大学",
                "lng": 117.283042,  # 经度
                "lat": 31.844786,   # 纬度
                "timestamp": time.time()
            }
            return jsonify({
                "code": 200,
                "data": [default_location]
            })
    except Exception as e:
        print(f"获取位置信息失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"获取位置信息失败: {str(e)}"
        }), 500

@app.route('/location/current', methods=['GET'])
def get_current_location():
    """获取当前位置"""
    try:
        print("请求当前位置接口...")
        
        # 使用正确的方法检查表是否存在
        from sqlalchemy import inspect
        if not inspect(db.engine).has_table('location'):
            print("位置数据表不存在，尝试创建...")
            db.create_all()
            print("数据库表创建完成")
            
            # 添加一条默认记录
            default_location = LocationData(
                longitude=117.283042,
                latitude=31.844786,
                time=datetime.now()
            )
            db.session.add(default_location)
            db.session.commit()
            print("添加了默认位置记录")
        
        # 获取最新位置
        latest_location = LocationData.query.order_by(LocationData.time.desc()).first()
        
        if latest_location:
            print(f"找到最新位置记录: ID={latest_location.id}, 经度={latest_location.longitude}, 纬度={latest_location.latitude}")
            return jsonify({
                "code": 200,
                "data": latest_location.to_dict(),
                "message": "获取当前位置成功"
            })
        else:
            print("没有找到位置记录，返回默认位置")
            # 默认位置
            default_location = {
                "name": "合肥工业大学",
                "lng": 117.283042,
                "lat": 31.844786,
                "timestamp": time.time()
            }
            return jsonify({
                "code": 200,
                "data": default_location,
                "message": "使用默认位置"
            })
    except Exception as e:
        db.session.rollback()
        error_msg = f"获取当前位置失败: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "message": error_msg
        }), 500

@app.route('/location/history', methods=['GET'])
def get_location_history():
    """获取位置历史记录"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', default=50, type=int)
        
        # 查询最近的位置记录
        locations = LocationData.query.order_by(LocationData.time.desc()).limit(limit).all()
        
        # 转换为字典列表
        location_list = [loc.to_dict() for loc in locations]
        
        return jsonify({
            "code": 200,
            "data": location_list,
            "message": f"获取了{len(location_list)}条位置记录"
        })
    except Exception as e:
        print(f"获取位置历史记录失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"获取位置历史记录失败: {str(e)}"
        }), 500

@app.route('/location/add', methods=['POST'])
def add_location():
    """添加新的位置信息"""
    try:
        data = request.get_json()
        
        # 验证必要参数
        if not data or 'lng' not in data or 'lat' not in data:
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: 经度(lng)和纬度(lat)"
            }), 400
        
        # 创建新的位置记录
        new_location = LocationData(
            longitude=float(data['lng']),
            latitude=float(data['lat']),
            time=datetime.now()
        )
        
        # 保存到数据库
        db.session.add(new_location)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "data": new_location.to_dict(),
            "message": "位置信息已添加"
        })
    except Exception as e:
        db.session.rollback()
        print(f"添加位置信息失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"添加位置信息失败: {str(e)}"
        }), 500

@app.route('/location/set', methods=['POST'])
def set_current_location():
    """设置当前位置"""
    try:
        data = request.get_json()
        
        # 验证必要参数
        if not data or 'lng' not in data or 'lat' not in data:
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: 经度(lng)和纬度(lat)"
            }), 400
        
        # 创建新的位置记录
        new_location = LocationData(
            longitude=float(data['lng']),
            latitude=float(data['lat']),
            time=datetime.now()
        )
        
        # 保存到数据库
        db.session.add(new_location)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "data": new_location.to_dict(),
            "success": True,
            "message": "当前位置已更新"
        })
    except Exception as e:
        db.session.rollback()
        print(f"设置当前位置失败: {str(e)}")
        return jsonify({
            "code": 500,
            "success": False,
            "message": f"设置当前位置失败: {str(e)}"
        }), 500

@app.route('/location/delete/<int:location_id>', methods=['DELETE'])
def delete_location(location_id):
    """删除指定位置记录"""
    try:
        location = LocationData.query.get(location_id)
        
        if not location:
            return jsonify({
                "code": 404,
                "message": f"未找到ID为{location_id}的位置记录"
            }), 404
        
        db.session.delete(location)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "位置记录已删除"
        })
    except Exception as e:
        db.session.rollback()
        print(f"删除位置记录失败: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"删除位置记录失败: {str(e)}"
        }), 500

# 位置模拟器控制接口
@app.route('/location/speed', methods=['POST'])
def set_speed():
    """设置移动速度"""
    try:
        data = request.get_json()
        
        if not data or 'speed' not in data:
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: speed"
            }), 400
        
        speed = float(data['speed'])
        
        # 这里可以添加更多的处理逻辑，例如保存速度到全局变量
        # ...
        
        return jsonify({
            "code": 200,
            "data": {"speed": speed},
            "success": True,
            "message": f"速度已设置为 {speed} m/s"
        })
    except Exception as e:
        print(f"设置速度失败: {str(e)}")
        return jsonify({
            "code": 500,
            "success": False,
            "message": f"设置速度失败: {str(e)}"
        }), 500

@app.route('/location/destination', methods=['POST'])
def set_destination():
    """设置目的地"""
    try:
        data = request.get_json()
        
        if not data or 'lat' not in data or 'lng' not in data:
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: 经度(lng)和纬度(lat)"
            }), 400
        
        lat = float(data['lat'])
        lng = float(data['lng'])
        
        # 这里可以添加更多的处理逻辑，例如计算路径等
        # ...
        
        return jsonify({
            "code": 200,
            "data": {"lat": lat, "lng": lng},
            "success": True,
            "message": "目的地已设置"
        })
    except Exception as e:
        print(f"设置目的地失败: {str(e)}")
        return jsonify({
            "code": 500,
            "success": False,
            "message": f"设置目的地失败: {str(e)}"
        }), 500

# 启动视差估计摄像头占用
@app.route('/d_estimator/start_cameras', methods=['POST'])
def d_start():
    global d_estimator
    
    # 检查请求频率
    if not check_request_rate('d_estimator', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if d_estimator is None:
            d_estimator = DisparityEstimator()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止视差估计摄像头占用
@app.route('/d_estimator/stop_cameras', methods=['POST'])
def d_stop():
    global d_estimator
    
    # 检查请求频率
    if not check_request_rate('d_estimator', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if d_estimator is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(d_estimator, 'd_estimator')
            d_estimator = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/d_estimator/video_feed')
def d_feed():
    """使用多线程管理器获取深度估计器视频流"""
    print("请求深度估计器视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if d_estimator is None:
        return jsonify({"error": "深度估计器未初始化"}), 503
    
    try:
        stream_id = f"d_estimator_{id(d_estimator)}"
        return create_threaded_video_stream(stream_id, d_estimator.run)
    except Exception as e:
        logger.error(f"深度估计器视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500


# 启动特征点识别摄像头占用
@app.route('/f_detector/start_cameras', methods=['POST'])
def f_d_start():
    global f_detector
    print("f_d_start")
    
    # 检查请求频率
    if not check_request_rate('f_detector', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    # 检查模块是否可用
    if not modules_available.get('FeaturePointDetector', False):
        return jsonify({'message': 'FeaturePointDetector模块不可用，请检查后端环境'}), 500
    
    try:
        if f_detector is None:
            f_detector = FeaturePointDetector(headless=True)
            f_detector.start()  # 使用start方法而不是run方法，确保在单独线程中执行
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        else:
            return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        print(f"启动失败: {str(e)}")
        return jsonify({'message': f'启动失败: {str(e)}'}), 500

# 停止特征点识别摄像头占用
@app.route('/f_detector/stop_cameras', methods=['POST'])
def f_d_stop():
    global f_detector
    print("f_d_stop")
    
    # 检查请求频率
    if not check_request_rate('f_detector', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if f_detector is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(f_detector, 'f_detector')
            f_detector = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500

# 接收get请求返回流式视频流 左
@app.route('/f_detector/video_feed_left')
def f_d_feed_left():
    """使用多线程管理器获取左侧视频流"""
    print("请求左侧视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if f_detector is None:
        return jsonify({"error": "特征点检测器未初始化"}), 503
    
    try:
        stream_id = f"f_detector_left_{id(f_detector)}"
        return create_threaded_video_stream(stream_id, f_detector.show_left)
    except Exception as e:
        logger.error(f"左侧视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500
    
# 接收get请求返回流式视频流 右
@app.route('/f_detector/video_feed_right')
def f_d_feed_right():
    """使用多线程管理器获取右侧视频流"""
    print("请求右侧视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if f_detector is None:
        return jsonify({"error": "特征点检测器未初始化"}), 503
    
    try:
        stream_id = f"f_detector_right_{id(f_detector)}"
        return create_threaded_video_stream(stream_id, f_detector.show_right)
    except Exception as e:
        logger.error(f"右侧视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500


# f_tracker
@app.route('/f_tracker/start_cameras', methods=['POST'])
def f_t_start():
    global f_tracker
    print("f_t_start")
    
    # 检查请求频率
    if not check_request_rate('f_tracker', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if f_tracker is None:
            # 启动摄像头 处理视频流，使用无头模式
            f_tracker = FeaturePointTracker(camera_size=720, motion_estimation="hardware_accelerated", headless=True)
            f_tracker.start()  # 使用start方法启动线程
            return jsonify({'message':'摄像头已启动', 'timestamp': time.time()}), 200
        else:
            return jsonify({'message':'摄像头已经在运行中', 'timestamp': time.time()}), 200
    except Exception as e:
        print(f"启动失败: {str(e)}")
        return jsonify({'message': f'启动失败: {str(e)}'}), 500
    
# f_tracker stop
@app.route('/f_tracker/stop_cameras', methods=['POST'])
def f_t_stop():
    global f_tracker
    print("f_t_stop")
    
    # 检查请求频率
    if not check_request_rate('f_tracker', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if f_tracker is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(f_tracker, 'f_tracker')
            f_tracker = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500
    
@app.route('/f_tracker/video_feed_left')
def f_t_feed_left():
    """使用多线程管理器获取f_tracker左侧视频流"""
    print("请求f_tracker左侧视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if f_tracker is None:
        return jsonify({"error": "特征点追踪器未初始化"}), 503
    
    try:
        stream_id = f"f_tracker_left_{id(f_tracker)}"
        return create_threaded_video_stream(stream_id, f_tracker.show_left)
    except Exception as e:
        logger.error(f"f_tracker左侧视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/f_tracker/video_feed_right')
def f_t_feed_right():
    """使用多线程管理器获取f_tracker右侧视频流"""
    print("请求f_tracker右侧视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if f_tracker is None:
        return jsonify({"error": "特征点追踪器未初始化"}), 503
    
    try:
        stream_id = f"f_tracker_right_{id(f_tracker)}"
        return create_threaded_video_stream(stream_id, f_tracker.show_right)
    except Exception as e:
        logger.error(f"f_tracker右侧视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500


# 启动 手势特征点 识别摄像头占用
@app.route('/g_recognition/start_cameras', methods=['POST'])
def g_recognition_start():
    """启动手势识别摄像头"""
    print("g_recognition_start")
    
    # 检查请求频率
    if not check_request_rate('g_recognition', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        global g_recognition
        if g_recognition is None:
            g_recognition = GesturePointRecognition(output_size=(720, 720))
            g_recognition.start()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        else:
            return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        print(f"启动摄像头失败: {str(e)}")
        return jsonify({'message': f'启动摄像头失败: {str(e)}'}), 500


# 停止 手势特征点 识别摄像头占用
@app.route('/g_recognition/stop_cameras', methods=['POST'])
def g_recognition_stop():
    """停止手势识别摄像头"""
    print("g_recognition_stop")
    
    # 检查请求频率
    if not check_request_rate('g_recognition', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        global g_recognition
        if g_recognition is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(g_recognition, 'g_recognition')
            g_recognition = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/g_recognition/video_feed')
def g_recognition_feed():
    """使用多线程管理器获取手势识别视频流"""
    print("请求手势识别视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if g_recognition is None:
        return jsonify({"error": "手势识别器未初始化"}), 503
    
    try:
        stream_id = f"g_recognition_{id(g_recognition)}"
        return create_threaded_video_stream(stream_id, g_recognition.run)
    except Exception as e:
        logger.error(f"手势识别视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500


# 启动手势类别判断摄像头占用
@app.route('/g_recognizer/start_cameras', methods=['POST'])
def r_start():
    global g_recognizer
    
    # 检查请求频率
    if not check_request_rate('g_recognizer', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if g_recognizer is None:
            g_recognizer = GestureRecognizer()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        print(f"启动失败: {str(e)}")
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止手势类别判断摄像头占用
@app.route('/g_recognizer/stop_cameras', methods=['POST'])
def r_stop():
    global g_recognizer
    
    # 检查请求频率
    if not check_request_rate('g_recognizer', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if g_recognizer is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(g_recognizer, 'g_recognizer')
            g_recognizer = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/g_recognizer/video_feed')
def r_feed():
    """使用多线程管理器获取手势类别判断视频流"""
    print("请求手势类别判断视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if g_recognizer is None:
        return jsonify({"error": "手势类别判断器未初始化"}), 503
    
    try:
        stream_id = f"g_recognizer_{id(g_recognizer)}"
        return create_threaded_video_stream(stream_id, g_recognizer.run)
    except Exception as e:
        logger.error(f"手势类别判断视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500


# 启动MobileNetSSD 目标检测摄像头占用
@app.route('/m_detector/start_cameras', methods=['POST'])
def m_start():
    global m_detector
    
    # 检查请求频率
    if not check_request_rate('m_detector', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if m_detector is None:
            m_detector = OakDMobileNetSSD()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止MobileNetSSD 目标检测摄像头占用
@app.route('/m_detector/stop_cameras', methods=['POST'])
def m_stop():
    global m_detector
    
    # 检查请求频率
    if not check_request_rate('m_detector', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if m_detector is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(m_detector, 'm_detector')
            m_detector = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/m_detector/video_feed')
def m_feed():
    global m_detector
    try:
        if m_detector is not None:
            return Response(m_detector.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
        else:
            abort(404, description="视频流未初始化")
    except Exception as e:
        return jsonify({'message': f'获取视频流失败: {str(e)}'}), 500


# 启动人像追踪摄像头占用
@app.route('/p_video/start_cameras', methods=['POST'])
def p_start():
    global p_video
    
    # 检查请求频率
    if not check_request_rate('p_video', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if p_video is None:
            p_video = PersonDetectionTrackerOnVideo()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止人像追踪摄像头占用
@app.route('/p_video/stop_cameras', methods=['POST'])
def p_stop():
    global p_video
    
    # 检查请求频率
    if not check_request_rate('p_video', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if p_video is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(p_video, 'p_video')
            p_video = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/p_video/video_feed')
def p_feed():
    global p_video
    if p_video is not None:
        return Response(p_video.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")


# 优化摄像头关闭函数
def safe_shutdown_camera(camera, camera_name):
    """
    安全关闭摄像头，加入超时保护
    返回 (成功标志, 错误信息)
    """
    import threading
    import time
    
    # 默认成功
    success = True
    error_msg = None
    
    def shutdown_with_timeout():
        nonlocal success, error_msg
        try:
            print(f"开始关闭 {camera_name} 摄像头...")
            start_time = time.time()
            
            if hasattr(camera, 'shutdown'):
                camera.shutdown()
            elif hasattr(camera, 'close'):
                camera.close()
            else:
                success = False
                error_msg = f"{camera_name} 没有关闭方法"
                return
                
            elapsed = time.time() - start_time
            print(f"{camera_name} 摄像头关闭完成，耗时 {elapsed:.2f} 秒")
        except Exception as e:
            success = False
            error_msg = str(e)
            print(f"关闭 {camera_name} 摄像头时出错: {e}")
    
    # 创建线程执行关闭操作
    shutdown_thread = threading.Thread(target=shutdown_with_timeout)
    shutdown_thread.daemon = True
    shutdown_thread.start()
    
    # 等待最多10秒
    shutdown_thread.join(10)
    
    if shutdown_thread.is_alive():
        print(f"关闭 {camera_name} 摄像头超时")
        success = False
        error_msg = f"关闭 {camera_name} 摄像头超时"
    
    return success, error_msg

# 启动RGB摄像头占用
@app.route('/s_RGB/start_cameras', methods=['POST'])
def s_start():
    global s_RGB
    
    # 检查请求频率
    if not check_request_rate('s_RGB', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if s_RGB is None:
            s_RGB = SpatialObjectTracker()
            return jsonify({'message': 'Cameras started', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already running', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止RGB摄像头占用
@app.route('/s_RGB/stop_cameras', methods=['POST'])
def s_stop():
    global s_RGB
    
    # 检查请求频率
    if not check_request_rate('s_RGB', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if s_RGB is not None:
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(s_RGB, 's_RGB')
            s_RGB = None
            
            if success:
                return jsonify({'message': 'Cameras stopped', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'摄像头已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': 'Cameras already stopped', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/s_RGB/video_feed')
def s_feed():
    global s_RGB
    if s_RGB is not None:
        return Response(s_RGB.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")


# 导入新的功能模块
try:
    from utils.yolo_processor import YOLOProcessor
    from utils.audio_processor import AudioManager
    from utils.speech_processor import SpeechProcessor
    from utils.navigation_service import NavigationService
    # 注意：trajectory_collision_manager已经在上面导入了，不要重复导入
    
    # 初始化处理器
    yolo_processor = YOLOProcessor()
    audio_manager = AudioManager()
    speech_processor = SpeechProcessor()
    navigation_service = NavigationService()
    # trajectory_collision_manager已经在上面初始化了
    
    # 启动音频管理器
    audio_manager.start()
    
    processors_available = True
    print("所有处理器初始化成功")
    
except Exception as e:
    print(f"处理器初始化失败: {e}")
    processors_available = False
    yolo_processor = None
    audio_manager = None
    speech_processor = None
    navigation_service = None
    # trajectory_collision_manager保持原有值，不设为None

# 添加主页和API健康检查
@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/utils-explorer')
def utils_explorer():
    return send_from_directory('static', 'utils-explorer.html')

# 数据库初始化函数
def init_db():
    """初始化数据库，创建所有表"""
    try:
        print("正在初始化数据库...")
        db.create_all()
        
        # 检查是否有位置数据记录
        if LocationData.query.count() == 0:
            print("没有位置记录，添加默认位置...")
            # 添加默认位置记录
            default_location = LocationData(
                longitude=117.283042,  # 合肥工业大学经度
                latitude=31.844786,    # 合肥工业大学纬度
                time=datetime.now()
            )
            db.session.add(default_location)
            db.session.commit()
            print(f"添加了默认位置记录: ID={default_location.id}")
        
        print("数据库初始化完成")
    except Exception as e:
        db.session.rollback()
        print(f"创建数据库表失败: {str(e)}")
        import traceback
        traceback.print_exc()

# 在启动时立即初始化数据库
with app.app_context():
    init_db()

# ========== 新增的智能处理API ==========

@app.route('/api/yolo/process', methods=['POST'])
def process_yolo():
    """YOLO目标检测和碰撞预警处理"""
    if not processors_available or not yolo_processor:
        return jsonify({'error': 'YOLO处理器不可用'}), 500
    
    try:
        # 这里应该从摄像头或上传的图像获取数据
        # 暂时返回状态信息
        status = yolo_processor.get_status()
        return jsonify({
            'success': True,
            'status': status,
            'collision_risk': yolo_processor.get_collision_risk_level()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/3d', methods=['POST'])
def process_3d_audio():
    """3D音频处理"""
    if not processors_available or not audio_manager:
        return jsonify({'error': '3D音频处理器不可用'}), 500
    
    try:
        data = request.get_json()
        azimuth_pitch_data = data.get('azimuth_pitch_data', [])
        audio_type = data.get('audio_type', 'beep')
        
        # 处理3D音频
        audio_manager.add_audio_data(azimuth_pitch_data, audio_type)
        
        # 获取音频可视化数据
        visualization = audio_manager.get_audio_visualization(azimuth_pitch_data, audio_type)
        
        return jsonify({
            'success': True,
            'visualization': visualization,
            'status': audio_manager.get_status()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 语音识别API
@app.route('/api/speech/recognize', methods=['POST'])
def recognize_speech():
    """
    语音识别API - 参考PYQT系统实现
    """
    try:
        data = request.get_json()
        
        if not data or 'audio_data' not in data:
            print("语音识别请求缺少音频数据")
            return jsonify({
                'success': False,
                'error': '缺少音频数据'
            }), 400
        
        audio_data = data['audio_data']
        sample_rate = data.get('sample_rate', 16000)
        
        # 检查音频数据
        if not audio_data:
            print("语音识别请求的音频数据为空")
            return jsonify({
                'success': False,
                'error': '音频数据为空'
            }), 400
        
        # 记录音频数据长度
        audio_data_length = len(audio_data) if isinstance(audio_data, str) else 0
        print(f"收到语音识别请求，音频数据长度: {audio_data_length} 字符")
        
        # 引入日志配置
        import logging
        logging.basicConfig(level=logging.DEBUG, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 引入超时机制
        import threading
        from threading import Timer
        
        response_ready = threading.Event()
        response_data = [None]
        
        def process_with_timeout():
            try:
                # 使用语音识别处理器
                from utils.speech_processor import SpeechProcessor
                
                processor = SpeechProcessor()
                print("创建SpeechProcessor实例成功")
                
                result = processor.recognize_from_base64(audio_data, sample_rate)
                print(f"语音识别处理结果: {result}")
                
                if result and result.get('success', False):
                    print(f"语音识别成功: {result.get('recognition_text', '')}")
                    response_data[0] = {
                        'success': True,
                        'recognition_text': result.get('recognition_text', ''),
                        'confidence': result.get('confidence', 0.0),
                        'command': result.get('command', {}),
                        'result': result.get('result', {}),
                        'is_simulated': result.get('is_simulated', False)
                    }
                else:
                    error_msg = result.get('error', '未知错误') if result else '语音识别失败'
                    print(f"语音识别失败: {error_msg}")
                    response_data[0] = {
                        'success': False,
                        'error': error_msg
                    }
            except Exception as processor_error:
                print(f"语音处理器错误: {str(processor_error)}")
                import traceback
                traceback.print_exc()
                
                # 尝试使用模拟响应
                try:
                    from utils.speech_processor import SpeechProcessor
                    processor = SpeechProcessor()
                    text = processor._get_simulated_response()
                    command = processor.recognizer.parse_command(text)
                    handler = processor.command_handlers.get(command['type'], processor._handle_text)
                    result = handler(command)
                    
                    response_data[0] = {
                        'success': True,
                        'recognition_text': text,
                        'command': command,
                        'result': result,
                        'is_simulated': True,
                        'note': '处理出错，使用模拟响应'
                    }
                except Exception as sim_err:
                    response_data[0] = {
                        'success': False,
                        'error': f'语音处理器错误: {str(processor_error)}'
                    }
            finally:
                # 标记处理完成
                response_ready.set()
        
        # 创建并启动处理线程
        processing_thread = threading.Thread(target=process_with_timeout)
        processing_thread.daemon = True
        processing_thread.start()
        
        # 等待处理完成，最多15秒
        is_ready = response_ready.wait(timeout=15)
        
        if not is_ready:
            print("语音识别请求处理超时(15秒)")
            # 尝试使用模拟响应
            try:
                from utils.speech_processor import SpeechProcessor
                processor = SpeechProcessor()
                text = processor._get_simulated_response()
                command = processor.recognizer.parse_command(text)
                handler = processor.command_handlers.get(command['type'], processor._handle_text)
                result = handler(command)
                
                return jsonify({
                    'success': True,
                    'recognition_text': text,
                    'command': command,
                    'result': result,
                    'is_simulated': True,
                    'note': 'API处理超时，使用模拟响应'
                })
            except Exception as sim_err:
                return jsonify({
                    'success': False,
                    'error': '语音识别处理超时，请重试'
                }), 408  # 408 Request Timeout
        
        if response_data[0] is None:
            print("语音识别返回了空结果")
            # 尝试使用模拟响应
            try:
                from utils.speech_processor import SpeechProcessor
                processor = SpeechProcessor()
                text = processor._get_simulated_response()
                command = processor.recognizer.parse_command(text)
                handler = processor.command_handlers.get(command['type'], processor._handle_text)
                result = handler(command)
                
                return jsonify({
                    'success': True,
                    'recognition_text': text,
                    'command': command,
                    'result': result,
                    'is_simulated': True,
                    'note': 'API返回空结果，使用模拟响应'
                })
            except Exception as sim_err:
                return jsonify({
                    'success': False,
                    'error': '语音识别处理错误，未返回结果'
                }), 500
        
        return jsonify(response_data[0])
            
    except Exception as e:
        error_msg = str(e)
        print(f"语音识别服务错误: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # 尝试使用模拟响应
        try:
            from utils.speech_processor import SpeechProcessor
            processor = SpeechProcessor()
            text = processor._get_simulated_response()
            command = processor.recognizer.parse_command(text)
            handler = processor.command_handlers.get(command['type'], processor._handle_text)
            result = handler(command)
            
            return jsonify({
                'success': True,
                'recognition_text': text,
                'command': command,
                'result': result,
                'is_simulated': True,
                'note': 'API服务错误，使用模拟响应'
            })
        except Exception as sim_err:
            return jsonify({
                'success': False,
                'error': f'语音识别服务错误: {error_msg}'
            }), 500

@app.route('/api/speech/status', methods=['GET'])
def get_speech_status():
    """
    获取语音识别状态
    """
    try:
        from utils.speech_processor import SpeechProcessor
        
        processor = SpeechProcessor()
        status = processor.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        # logger.error(f"获取语音状态失败: {str(e)}") # logger is not defined, so commenting out
        print(f"获取语音状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取状态失败: {str(e)}'
        }), 500

# 环境分析API
@app.route('/api/yolo/analyze_environment', methods=['POST'])
def analyze_environment():
    """
    环境分析API - 基于YOLO检测结果
    """
    try:
        # 获取当前的检测结果
        if hasattr(yolo_processor, 'get_latest_detection'):
            detection_result = yolo_processor.get_latest_detection()
            
            if detection_result:
                objects = detection_result.get('objects', [])
                
                # 分析环境
                analysis_text = []
                
                # 统计对象类型
                object_counts = {}
                for obj in objects:
                    obj_type = obj.get('class', 'unknown')
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
                
                # 生成分析文本
                if object_counts:
                    for obj_type, count in object_counts.items():
                        if count == 1:
                            analysis_text.append(f"检测到1个{obj_type}")
                        else:
                            analysis_text.append(f"检测到{count}个{obj_type}")
                    
                    # 距离信息
                    nearest_objects = sorted(objects, key=lambda x: x.get('distance', float('inf')))[:3]
                    if nearest_objects:
                        nearest = nearest_objects[0]
                        distance = nearest.get('distance', 0)
                        if distance > 0:
                            analysis_text.append(f"最近的{nearest.get('class', '物体')}距离{distance:.1f}米")
                    
                    analysis = "，".join(analysis_text)
                else:
                    analysis = "当前环境中未检测到明显物体"
                
                return jsonify({
                    'success': True,
                    'analysis': analysis,
                    'objects': objects,
                    'object_counts': object_counts
                })
            else:
                return jsonify({
                    'success': True,
                    'analysis': '暂无检测数据，请确保视觉系统已启动',
                    'objects': [],
                    'object_counts': {}
                })
        else:
            return jsonify({
                'success': False,
                'error': 'YOLO检测器未初始化'
            }), 500
            
    except Exception as e:
        # logger.error(f"环境分析失败: {str(e)}") # logger is not defined, so commenting out
        print(f"环境分析失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'环境分析失败: {str(e)}'
        }), 500

# 导航API
@app.route('/api/navigation/start', methods=['POST'])
def start_navigation():
    """
    启动导航API
    """
    try:
        data = request.get_json()
        
        if not data or 'destination' not in data:
            return jsonify({
                'success': False,
                'error': '缺少目的地信息'
            }), 400
        
        destination = data['destination']
        
        # 这里可以集成真实的导航服务
        # 目前返回模拟结果
        return jsonify({
            'success': True,
            'message': f'导航已启动，目的地: {destination}',
            'destination': destination,
            'estimated_time': '15分钟',
            'distance': '1.2公里'
        })
        
    except Exception as e:
        # logger.error(f"导航启动失败: {str(e)}") # logger is not defined, so commenting out
        print(f"导航启动失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'导航启动失败: {str(e)}'
        }), 500

@app.route('/api/navigation/stop', methods=['POST'])
def stop_navigation():
    """停止导航"""
    if not processors_available or not navigation_service:
        return jsonify({'error': '导航服务不可用'}), 500
    
    try:
        navigation_service.stop_navigation()
        return jsonify({'success': True, 'message': '导航已停止'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/navigation/status', methods=['GET'])
def get_navigation_status():
    """获取导航状态"""
    if not processors_available or not navigation_service:
        return jsonify({'error': '导航服务不可用'}), 500
    
    try:
        status = navigation_service.get_navigation_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/navigation/search', methods=['POST'])
def search_destination():
    """搜索目的地"""
    if not processors_available or not navigation_service:
        return jsonify({'error': '导航服务不可用'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': '缺少搜索关键词'}), 400
        
        results = navigation_service.search_destination(query)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrated/status', methods=['GET'])
def get_integrated_status():
    """获取综合系统状态"""
    try:
        status = {
            'timestamp': time.time(),
            'processors_available': processors_available,
            'yolo_processor': yolo_processor.get_status() if yolo_processor else None,
            'audio_manager': audio_manager.get_status() if audio_manager else None,
            'speech_processor': speech_processor.get_status() if speech_processor else None,
            'navigation_service': navigation_service.get_status() if navigation_service else None,
            'cameras': {
                'd_estimator': d_estimator is not None,
                'f_detector': f_detector is not None,
                'f_tracker': f_tracker is not None,
                'g_recognition': g_recognition is not None,
                'g_recognizer': g_recognizer is not None,
                'm_detector': m_detector is not None,
                'p_video': p_video is not None,
                's_RGB': s_RGB is not None
            }
        }
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/integrated/status', methods=['GET'])
def get_integrated_status_alternative():
    """获取综合系统状态 - 兼容路径"""
    return get_integrated_status()

@app.route('/api/integrated/process_frame', methods=['POST'])
def process_integrated_frame():
    """综合处理单帧数据"""
    if not processors_available or not yolo_processor:
        return jsonify({'error': '处理器不可用'}), 500
    
    try:
        # 这里应该从摄像头获取实际的图像和深度数据
        # 暂时返回模拟数据
        
        # 模拟处理结果
        result = {
            'detections': [
                {
                    'class_name': 'person',
                    'bbox': [100, 100, 200, 300],
                    'confidence': 0.85,
                    'distance': 150.0,
                    'azimuth_angle': 15.0,
                    'pitch_angle': -5.0
                }
            ],
            'collision_risk': 0.2,
            'azimuth_pitch_data': [
                ['person', 15.0, -5.0, 150.0]
            ],
            'timestamp': time.time()
        }
        
        # 如果有检测到的对象，播放3D音频
        if result['azimuth_pitch_data'] and audio_manager:
            audio_manager.add_audio_data(result['azimuth_pitch_data'])
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    status = {
        'status': 'online',
        'modules': {
            'video_modules': video_modules_available,
            'database': db_available,
            'processors': processors_available
        },
        'cameras': {
            'd_estimator': d_estimator is not None,
            'f_detector': f_detector is not None,
            'f_tracker': f_tracker is not None,
            'g_recognition': g_recognition is not None,
            'g_recognizer': g_recognizer is not None,
            'm_detector': m_detector is not None,
            'p_video': p_video is not None,
            's_RGB': s_RGB is not None
        },
        'intelligent_processors': {
            'yolo_processor': yolo_processor is not None,
            'audio_manager': audio_manager is not None,
            'speech_processor': speech_processor is not None,
            'navigation_service': navigation_service is not None,
            'trajectory_collision_manager': trajectory_collision_manager is not None,
            'signal_user_inference': signal_user_inference is not None
        }
    }
    return jsonify(status)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500
# 确保所有摄像头在程序退出时正确关闭
def cleanup():
    global d_estimator, f_detector, f_tracker, g_recognition, g_recognizer, m_detector, p_video, s_RGB, enhanced_detector
    
    print("程序退出，正在安全关闭所有资源...")
    
    # 关闭线程管理器
    if thread_manager:
        try:
            thread_manager.shutdown()
            print("线程管理器已关闭")
        except Exception as e:
            print(f"关闭线程管理器时出错: {e}")
    
    # 关闭设备管理器
    if device_manager:
        try:
            device_manager.stop()
            print("设备管理器已关闭")
        except Exception as e:
            print(f"关闭设备管理器时出错: {e}")
    
    # 创建摄像头名称映射
    cameras = {
        'd_estimator': d_estimator,
        'f_detector': f_detector,
        'f_tracker': f_tracker,
        'g_recognition': g_recognition,
        'g_recognizer': g_recognizer,
        'm_detector': m_detector,
        'p_video': p_video,
        's_RGB': s_RGB,
        'enhanced_detector': enhanced_detector
    }
    
    # 逐个安全关闭摄像头
    for name, camera in cameras.items():
        if camera is not None:
            try:
                print(f"正在关闭 {name} 摄像头...")
                success, error_msg = safe_shutdown_camera(camera, name)
                if not success:
                    print(f"警告: {name} 关闭时出现问题: {error_msg}")
            except Exception as e:
                print(f"关闭 {name} 摄像头时出错: {str(e)}")
    
    print("所有资源已关闭")

atexit.register(cleanup)

# 添加Vosk语音识别导航接口
@app.route('/api/navigation/voice_navigate', methods=['POST'])
def voice_navigate():
    """
    使用Vosk进行语音识别并设置为导航目的地
    """
    try:
        if 'audio_file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有收到音频文件',
                'message': '请提供音频文件'
            }), 400
        
        audio_file = request.files['audio_file']
        if audio_file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空',
                'message': '请选择音频文件'
            }), 400
        
        # 保存临时音频文件
        temp_file_path = 'temp_audio.wav'
        audio_file.save(temp_file_path)
        
        # 使用Vosk进行语音识别
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            import wave
            import json
            
            # 设置日志级别
            SetLogLevel(0)
            
            # 打开音频文件
            wf = wave.open(temp_file_path, "rb")
            
            # 检查音频格式
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                return jsonify({
                    'success': False,
                    'error': '音频格式不支持',
                    'message': '音频文件必须是单声道PCM格式的WAV文件'
                }), 400
            
            # 查找模型路径
            import os
            possible_model_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'vosk_model'),
                os.path.join(os.getcwd(), 'resources', 'vosk_model'),
                os.path.join(os.getcwd(), 'main', 'resources', 'vosk_model'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'vosk_model')
            ]
            
            model_path = None
            for path in possible_model_paths:
                if os.path.exists(path) and any(os.listdir(path)):
                    model_path = path
                    break
            
            if not model_path:
                return jsonify({
                    'success': False,
                    'error': '找不到Vosk模型',
                    'message': '请先下载Vosk中文模型到resources/vosk_model目录'
                }), 500
            
            # 加载模型并创建识别器
            model = Model(model_path)
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            
            # 开始识别
            results = []
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    results.append(result.get("text", ""))
            
            # 添加最终结果
            final_result = json.loads(rec.FinalResult())
            results.append(final_result.get("text", ""))
            
            # 合并所有识别结果
            full_text = " ".join([r for r in results if r])
            
            # 如果没有识别出文字，使用speech_processor的模拟响应
            if not full_text:
                # 导入SpeechProcessor
                from utils.speech_processor import SpeechProcessor
                speech_processor = SpeechProcessor()
                full_text = speech_processor._get_simulated_response()
            
            # 解析识别结果中的导航目标
            destination = full_text
            
            # 提取可能的目的地 - 简单处理，如果有"去"或"到"之类的词，取其后的内容
            import re
            nav_patterns = [
                r'导航到(.+)',
                r'去(.+)', 
                r'前往(.+)',
                r'到(.+)去',
                r'我要去(.+)',
                r'带我去(.+)'
            ]
            
            # 尝试匹配导航模式
            for pattern in nav_patterns:
                match = re.search(pattern, full_text)
                if match:
                    destination = match.group(1).strip()
                    break
            
            # 清理临时文件
            wf.close()
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # 返回识别结果和导航目标
            return jsonify({
                'success': True,
                'recognized_text': full_text,
                'destination': destination,
                'message': f'正在导航到: {destination}'
            })
            
        except ImportError:
            # Vosk不可用，尝试使用speech_processor
            from utils.speech_processor import SpeechProcessor
            speech_processor = SpeechProcessor()
            
            with open(temp_file_path, 'rb') as f:
                audio_data = f.read()
            
            # 使用SpeechProcessor的识别功能
            result = speech_processor.recognizer.recognize_from_file(temp_file_path)
            if not result:
                result = speech_processor._get_simulated_response()
            
            # 解析命令
            command = speech_processor.recognizer.parse_command(result)
            
            # 确定目的地
            if command['type'] == 'navigation':
                destination = command.get('destination', result)
            else:
                destination = result
            
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return jsonify({
                'success': True,
                'recognized_text': result,
                'destination': destination,
                'message': f'正在导航到: {destination}',
                'using_fallback': True
            })
            
    except Exception as e:
        # 确保临时文件被删除
        import os
        if os.path.exists('temp_audio.wav'):
            os.remove('temp_audio.wav')
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '语音识别失败'
        }), 500

# ========== 轨迹追踪和碰撞预警API ==========

@app.route('/api/trajectory/start', methods=['POST'])
def start_trajectory_tracking():
    """启动轨迹追踪"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '轨迹追踪服务不可用'}), 500
    
    try:
        trajectory_collision_manager.start()
        return jsonify({
            'success': True,
            'message': '轨迹追踪已启动'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trajectory/stop', methods=['POST'])
def stop_trajectory_tracking():
    """停止轨迹追踪"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '轨迹追踪服务不可用'}), 500
    
    try:
        trajectory_collision_manager.stop()
        return jsonify({
            'success': True,
            'message': '轨迹追踪已停止'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trajectory/status', methods=['GET'])
def get_trajectory_status():
    """获取轨迹追踪状态"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '轨迹追踪服务不可用'}), 500
    
    try:
        status = trajectory_collision_manager.get_comprehensive_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/collision/risk', methods=['GET'])
def get_collision_risk():
    """获取碰撞风险 - 使用真实的轨迹碰撞管理器数据"""
    
    # 确保time模块被导入
    import time
    
    def safe_time_to_collision(time_val):
        """安全处理time_to_collision值，将Infinity转换为null"""
        if time_val is None:
            return None
        try:
            if time_val == float('inf') or time_val == float('-inf') or time_val != time_val:  # 检查NaN
                return None
            return float(time_val)
        except (ValueError, TypeError):
            return None
    
    try:
        # 首先检查轨迹碰撞管理器是否可用
        if not trajectory_collision_manager:
            print("❌ 轨迹碰撞管理器不可用")
            return jsonify({
                'success': False,
                'error': '轨迹碰撞管理器不可用',
                'detected_objects': [],
                'max_probability': 0.0,
                'risk': {
                    'level': 'low',
                    'probability': 0.0,
                    'time_to_collision': None,
                    'warning_message': '碰撞检测系统不可用',
                    'nearest_object': None
                },
                'tracks': {}
            }), 503
        
        # 检查轨迹碰撞管理器是否正在运行
        if not trajectory_collision_manager.is_running:
            print("⚠️ 轨迹碰撞管理器未运行，尝试启动...")
            
            # 尝试启动轨迹碰撞管理器
            try:
                trajectory_collision_manager.start()
                print("✅ 轨迹碰撞管理器启动成功")
                
                # 等待一小段时间让系统稳定
                time.sleep(0.5)
                
            except Exception as start_error:
                print(f"❌ 轨迹碰撞管理器启动失败: {start_error}")
                return jsonify({
                    'success': False,
                    'error': f'轨迹碰撞管理器启动失败: {str(start_error)}',
                    'detected_objects': [],
                    'max_probability': 0.0,
                    'risk': {
                        'level': 'low',
                        'probability': 0.0,
                        'time_to_collision': None,
                        'warning_message': '碰撞检测系统启动失败',
                        'nearest_object': None
                    },
                    'tracks': {}
                }), 503
        
        print("📊 从轨迹碰撞管理器获取真实碰撞数据...")
        
        # 安全获取碰撞数据
        collision_data = {}
        try:
            if hasattr(trajectory_collision_manager, 'get_collision_data'):
                collision_data = trajectory_collision_manager.get_collision_data()
            else:
                print("⚠️ 轨迹碰撞管理器缺少get_collision_data方法")
                collision_data = {'max_probability': 0.0, 'tracks': {}}
        except Exception as data_error:
            print(f"⚠️ 获取碰撞数据失败: {data_error}")
            collision_data = {'max_probability': 0.0, 'tracks': {}}
        
        # 安全获取风险信息
        risk = None
        try:
            if hasattr(trajectory_collision_manager, 'collision_warning') and trajectory_collision_manager.collision_warning:
                risk = trajectory_collision_manager.collision_warning.get_collision_risk()
            else:
                print("⚠️ 轨迹碰撞管理器缺少collision_warning属性")
        except Exception as risk_error:
            print(f"⚠️ 获取风险信息失败: {risk_error}")
            risk = None
        
        # 如果没有获取到风险信息，创建默认风险信息
        if risk is None:
            from utils.trajectory_collision_manager import CollisionRisk
            risk = CollisionRisk(
                level='low',
                probability=0.0,
                time_to_collision=float('inf'),
                warning_message='数据获取失败',
                nearest_object=None
            )
        
        # 安全获取检测到的对象
        detected_objects = []
        try:
            if hasattr(trajectory_collision_manager, 'collision_warning') and trajectory_collision_manager.collision_warning:
                detected_objects = trajectory_collision_manager.collision_warning.get_detected_objects()
            else:
                print("⚠️ 无法获取检测到的对象")
        except Exception as obj_error:
            print(f"⚠️ 获取检测对象失败: {obj_error}")
            detected_objects = []
        
        # 转换检测到的对象为API格式
        api_detected_objects = []
        for obj in detected_objects:
            try:
                api_detected_objects.append({
                    'id': getattr(obj, 'id', 0),
                    'type': getattr(obj, 'type', 'unknown'),
                    'distance': getattr(obj, 'distance', 0.0),
                    'position': list(getattr(obj, 'position', [0.0, 0.0, 0.0])),
                    'velocity': list(getattr(obj, 'velocity', [0.0, 0.0, 0.0])),
                    'confidence': getattr(obj, 'confidence', 0.0),
                    'timestamp': getattr(obj, 'timestamp', time.time())
                })
            except Exception as obj_convert_error:
                print(f"⚠️ 转换检测对象失败: {obj_convert_error}")
                continue
        
        # 计算最大碰撞概率
        max_probability = collision_data.get('max_probability', 0.0)
        
        # 如果没有检测到任何碰撞风险，使用轨迹数据计算
        if max_probability == 0.0 and collision_data.get('tracks'):
            tracks = collision_data['tracks']
            if tracks:
                # 从轨迹数据中找到最大碰撞概率
                track_probabilities = []
                for track_id, track_data in tracks.items():
                    if isinstance(track_data, dict) and 'collision_probability' in track_data:
                        track_probabilities.append(track_data['collision_probability'])
                
                if track_probabilities:
                    max_probability = max(track_probabilities)
                    print(f"📈 从轨迹数据计算得到最大碰撞概率: {max_probability:.3f}")
        
        # 构建最近物体信息
        nearest_object = None
        try:
            if hasattr(risk, 'nearest_object') and risk.nearest_object:
                nearest_object = {
                    'type': getattr(risk.nearest_object, 'type', 'unknown'),
                    'distance': getattr(risk.nearest_object, 'distance', 0.0),
                    'position': list(getattr(risk.nearest_object, 'position', [0.0, 0.0, 0.0])),
                    'confidence': getattr(risk.nearest_object, 'confidence', 0.0)
                }
            elif api_detected_objects:
                # 如果risk中没有nearest_object，从检测到的对象中找最近的
                nearest_obj = min(api_detected_objects, key=lambda obj: obj['distance'])
                nearest_object = {
                    'type': nearest_obj['type'],
                    'distance': nearest_obj['distance'],
                    'position': nearest_obj['position'],
                    'confidence': nearest_obj['confidence']
                }
        except Exception as nearest_error:
            print(f"⚠️ 构建最近物体信息失败: {nearest_error}")
            nearest_object = None
        
        print(f"💥 轨迹碰撞管理器返回数据: max_prob={max_probability:.3f}, risk_level={getattr(risk, 'level', 'unknown')}")
        print(f"📋 检测到的对象数量: {len(api_detected_objects)}")
        print(f"🎯 最近物体: {nearest_object['type'] if nearest_object else 'None'}")
        
        # 安全获取风险属性
        risk_level = getattr(risk, 'level', 'low')
        risk_probability = getattr(risk, 'probability', 0.0)
        risk_time_to_collision = getattr(risk, 'time_to_collision', float('inf'))
        risk_warning_message = getattr(risk, 'warning_message', '未知状态')
        
        # 返回真实数据
        return jsonify({
            'success': True,
            'max_probability': max_probability * 100,  # 转换为百分比
            'risk': {
                'level': risk_level,
                'probability': risk_probability * 100,  # 转换为百分比
                'time_to_collision': safe_time_to_collision(risk_time_to_collision),
                'warning_message': risk_warning_message,
                'nearest_object': nearest_object
            },
            'tracks': collision_data.get('tracks', {}),
            'detected_objects': api_detected_objects,
            'is_mock': False,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ 获取碰撞风险时出错: {e}")
        import traceback
        traceback.print_exc()
        
        # 发生错误时返回错误信息，不使用模拟数据
        return jsonify({
            'success': False,
            'error': f'获取碰撞风险失败: {str(e)}',
            'detected_objects': [],
            'max_probability': 0.0,
            'risk': {
                'level': 'low',
                'probability': 0.0,
                'time_to_collision': None,
                'warning_message': '碰撞检测系统错误',
                'nearest_object': None
            },
            'tracks': {},
            'is_mock': False,
            'error_fallback': True,
            'timestamp': time.time()
        }), 500

@app.route('/api/collision/objects', methods=['GET'])
def get_detected_objects():
    """获取检测到的对象"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '碰撞预警服务不可用'}), 500
    
    try:
        objects = trajectory_collision_manager.collision_warning.get_detected_objects()
        return jsonify({
            'success': True,
            'objects': [
                {
                    'id': obj.id,
                    'type': obj.type,
                    'position': obj.position,
                    'distance': obj.distance,
                    'velocity': obj.velocity,
                    'confidence': obj.confidence,
                    'timestamp': obj.timestamp
                }
                for obj in objects
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trajectory/data', methods=['GET'])
def get_trajectory_data():
    """获取轨迹数据"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '轨迹追踪服务不可用'}), 500
    
    try:
        data = trajectory_collision_manager.trajectory_tracker.get_trajectory_data()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trajectory/current_position', methods=['GET'])
def get_current_position():
    """获取当前位置"""
    if not processors_available or not trajectory_collision_manager:
        return jsonify({'error': '轨迹追踪服务不可用'}), 500
    
    try:
        position = trajectory_collision_manager.trajectory_tracker.get_current_position()
        if position:
            return jsonify({
                'success': True,
                'position': {
                    'lng': position.lng,
                    'lat': position.lat,
                    'timestamp': position.timestamp,
                    'speed': position.speed,
                    'direction': position.direction
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '当前位置不可用'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== 增强检测器API ==========

@app.route('/enhanced_detector/start', methods=['POST'])
def start_enhanced_detector():
    """启动增强检测器（带碰撞检测）"""
    global enhanced_detector
    
    print("🚀 启动增强检测器请求")
    
    # 检查请求频率
    if not check_request_rate('enhanced_detector', 'start'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        # 确保设备管理器已启动 - 只启动一次
        if device_manager and not device_manager.is_running():
            print("🚀 启动设备管理器...")
            if not device_manager.start():
                return jsonify({
                    'message': '设备管理器启动失败',
                    'timestamp': time.time()
                }), 500
        
        if enhanced_detector is None:
            print("🔧 创建增强检测器实例...")
            enhanced_detector = EnhancedDetector(
                camera_size=720,
                use_yolo=True,
                confidence_threshold=0.5
            )
            
            # 设置碰撞管理器
            if trajectory_collision_manager:
                print("🔗 设置碰撞管理器...")
                enhanced_detector.set_collision_manager(trajectory_collision_manager)
                trajectory_collision_manager.start()
                print("✅ 碰撞管理器已启动")
                
                # 启动后台处理 - 现在不会重复启动设备管理器
                if enhanced_detector.start_background_processing():
                    print("✅ 增强检测器后台处理已启动")
                else:
                    print("⚠️ 增强检测器后台处理启动失败")
            else:
                print("❌ 碰撞管理器不可用")
            
            return jsonify({
                'message': '增强检测器已启动',
                'timestamp': time.time(),
                'collision_tracking': trajectory_collision_manager is not None
            }), 200
        else:
            print("ℹ️ 增强检测器已在运行")
            # 如果已存在，确保后台处理在运行
            if not enhanced_detector.background_running:
                enhanced_detector.start_background_processing()
            return jsonify({'message': '增强检测器已在运行', 'timestamp': time.time()}), 200
    except Exception as e:
        print(f"❌ 启动增强检测器失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


@app.route('/enhanced_detector/stop', methods=['POST'])
def stop_enhanced_detector():
    """停止增强检测器"""
    global enhanced_detector
    
    # 检查请求频率
    if not check_request_rate('enhanced_detector', 'stop'):
        return jsonify({'message': '请求过于频繁，请稍后再试'}), 429
    
    try:
        if enhanced_detector is not None:
            # 停止碰撞管理器
            if trajectory_collision_manager:
                trajectory_collision_manager.stop()
            
            # 使用安全关闭方法
            success, error_msg = safe_shutdown_camera(enhanced_detector, 'enhanced_detector')
            enhanced_detector = None
            
            if success:
                return jsonify({'message': '增强检测器已停止', 'timestamp': time.time()}), 200
            else:
                return jsonify({'message': f'增强检测器已停止，但有警告: {error_msg}', 'timestamp': time.time()}), 200
        return jsonify({'message': '增强检测器未在运行', 'timestamp': time.time()}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


@app.route('/enhanced_detector/video_feed')
def enhanced_detector_feed():
    """使用多线程管理器获取增强检测器视频流"""
    print("请求增强检测器视频流")
    
    if not thread_manager:
        return jsonify({"error": "线程管理器未初始化"}), 500
    
    if enhanced_detector is None:
        return jsonify({"error": "增强检测器未初始化"}), 503
    
    try:
        stream_id = f"enhanced_detector_{id(enhanced_detector)}"
        return create_threaded_video_stream(stream_id, enhanced_detector.run)
    except Exception as e:
        logger.error(f"增强检测器视频流启动失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/enhanced_detector/status', methods=['GET'])
def get_enhanced_detector_status():
    """获取增强检测器状态（调试用）"""
    global enhanced_detector, trajectory_collision_manager
    
    status = {
        'enhanced_detector': {
            'exists': enhanced_detector is not None,
            'running': enhanced_detector.continue_running if enhanced_detector else False,
            'collision_manager_set': enhanced_detector.collision_manager is not None if enhanced_detector else False
        },
        'trajectory_collision_manager': {
            'exists': trajectory_collision_manager is not None,
            'running': trajectory_collision_manager.is_running if trajectory_collision_manager else False,
            'yolo_model_loaded': trajectory_collision_manager.yolo_model is not None if trajectory_collision_manager else False
        },
        'timestamp': time.time()
    }
    
    return jsonify(status), 200


@app.route('/api/streams/stats', methods=['GET'])
def get_stream_stats():
    """获取所有视频流统计信息"""
    try:
        if not thread_manager:
            return jsonify({
                'status': 'error',
                'message': '线程管理器不可用',
                'timestamp': time.time()
            }), 503
        
        stats = thread_manager.get_all_stats()
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'timestamp': time.time()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取流统计失败: {str(e)}',
            'timestamp': time.time()
        }), 500

@app.route('/api/streams/health', methods=['GET'])
def get_stream_health():
    """获取视频流健康状态"""
    try:
        from utils.stream_optimizer import get_stream_optimizer
        optimizer = get_stream_optimizer()
        stats = optimizer.get_stream_stats()
        
        # 分析健康状态
        healthy_streams = []
        unhealthy_streams = []
        
        for stream_id, stream_stats in stats.items():
            if stream_stats.get('avg_fps', 0) > 15 and stream_stats.get('frames_dropped', 0) < 10:
                healthy_streams.append({
                    'id': stream_id,
                    'fps': stream_stats.get('avg_fps', 0),
                    'status': 'healthy'
                })
            else:
                unhealthy_streams.append({
                    'id': stream_id,
                    'fps': stream_stats.get('avg_fps', 0),
                    'dropped_frames': stream_stats.get('frames_dropped', 0),
                    'status': 'unhealthy'
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'healthy_count': len(healthy_streams),
                'unhealthy_count': len(unhealthy_streams),
                'healthy_streams': healthy_streams,
                'unhealthy_streams': unhealthy_streams,
                'total_streams': len(stats)
            },
            'timestamp': time.time()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取流健康状态失败: {str(e)}',
            'timestamp': time.time()
        }), 500

# 导入全局帧缓存
try:
    from utils.global_frame_cache import get_global_frame_cache
    global_frame_cache = get_global_frame_cache()
    print("✅ 全局帧缓存导入成功")
except Exception as e:
    print(f"❌ 导入全局帧缓存失败: {e}")
    import traceback
    traceback.print_exc()
    global_frame_cache = None

# 导入环境感知处理器
try:
    from utils.environment_processor import get_environment_processor
    environment_processor = get_environment_processor()
    
    # 连接全局帧缓存
    if environment_processor and global_frame_cache:
        environment_processor.set_global_frame_cache(global_frame_cache)
        print("✅ 环境感知处理器已连接到全局帧缓存")
    else:
        print(f"⚠️ 连接失败: 环境处理器={environment_processor is not None}, 全局缓存={global_frame_cache is not None}")
    
    # 连接轨迹碰撞管理器
    if environment_processor and trajectory_collision_manager:
        environment_processor.set_trajectory_collision_manager(trajectory_collision_manager)
        print("✅ 环境感知处理器已连接到轨迹碰撞管理器")
    else:
        print(f"⚠️ 连接失败: 环境处理器={environment_processor is not None}, 轨迹碰撞管理器={trajectory_collision_manager is not None}")
    
    print("✅ 环境感知处理器导入成功")
except Exception as e:
    print(f"❌ 导入环境感知处理器失败: {e}")
    import traceback
    traceback.print_exc()
    environment_processor = None

# 确保设备管理器连接到全局帧缓存
if device_manager and global_frame_cache:
    print("🔗 确保设备管理器连接到全局帧缓存")
    # 设备管理器已经在初始化时连接了全局帧缓存
else:
    print("⚠️ 设备管理器或全局帧缓存不可用")

# ========== 用户行为识别API ==========

@app.route('/api/signal/predict', methods=['POST'])
def predict_user_behavior():
    """
    用户行为识别预测API
    """
    try:
        if not signal_inference_available or not signal_user_inference:
            return jsonify({
                'success': False,
                'error': '用户行为识别服务不可用'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少输入数据'
            }), 400
        
        # 进行预测
        result = signal_user_inference.predict(data)
        
        return jsonify({
            'success': True,
            'prediction': result,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"用户行为识别预测失败: {e}")
        return jsonify({
            'success': False,
            'error': f'预测失败: {str(e)}'
        }), 500

@app.route('/api/signal/mock_predict', methods=['POST'])
def mock_predict_user_behavior():
    """
    用户行为识别模拟预测API - 生成实时模拟数据（固定为静止状态）
    """
    try:
        import random
        import numpy as np
        
        # 行为类型列表，对应训练模型中的8个类别
        behavior_types = [
            'stationary',  # 静止
            'walking',     # 走路
            'running',     # 跑步
            'cycling',     # 自行车
            'driving',     # 汽车
            'bus',         # 公交
            'train',       # 火车
            'subway'       # 地铁
        ]
        
        # 固定为静止状态
        predicted_behavior = 'stationary'
        
        # 为静止状态生成实时变化的置信度（在高置信度范围内波动）
        base_confidence = 0.92  # 基础置信度
        confidence_variation = random.uniform(-0.05, 0.05)  # ±5% 的波动
        confidence = max(0.85, min(0.98, base_confidence + confidence_variation))
        
        # 生成模拟的传感器特征（符合静止状态的特征）
        sensor_features = {
            'acceleration': {
                'x': random.uniform(-0.1, 0.1),  # 静止时加速度接近0
                'y': random.uniform(-0.1, 0.1),
                'z': random.uniform(9.7, 9.9)    # 重力加速度
            },
            'gyroscope': {
                'x': random.uniform(-0.05, 0.05),  # 静止时陀螺仪数值很小
                'y': random.uniform(-0.05, 0.05),
                'z': random.uniform(-0.05, 0.05)
            },
            'gps_accuracy': random.uniform(3, 8),     # 较好的GPS精度
            'signal_strength': random.uniform(-65, -45)  # 较强的信号
        }
        
        # 为静止状态生成概率分布（静止概率最高，其他很低）
        other_behaviors_prob = 1 - confidence
        num_other_behaviors = len(behavior_types) - 1
        avg_other_prob = other_behaviors_prob / num_other_behaviors
        
        probabilities = {}
        for behavior in behavior_types:
            if behavior == 'stationary':
                probabilities[behavior] = confidence
            else:
                # 为其他行为分配小的随机概率
                variation = random.uniform(-0.5, 0.5) * avg_other_prob
                probabilities[behavior] = max(0.001, avg_other_prob + variation)
        
        # 确保概率总和为1
        total_prob = sum(probabilities.values())
        probabilities = {k: v / total_prob for k, v in probabilities.items()}
        
        # 模拟预测结果
        prediction_result = {
            'predicted_class': predicted_behavior,
            'predicted_class_index': behavior_types.index(predicted_behavior),
            'confidence': confidence,
            'probabilities': probabilities,
            'sensor_features': sensor_features,
            'timestamp': time.time(),
            'model_version': '1.0.0',
            'processing_time_ms': random.uniform(15, 35),  # 静止状态处理较快
            'behavior_duration': random.uniform(30, 120),  # 静止持续时间
            'movement_detected': False,  # 无运动检测
            'stability_score': random.uniform(0.9, 1.0)  # 高稳定性分数
        }
        
        return jsonify({
            'success': True,
            'prediction': prediction_result,
            'timestamp': time.time(),
            'is_mock': True,
            'behavior_fixed': 'stationary',
            'message': '模拟数据生成成功 - 固定静止状态'
        })
        
    except Exception as e:
        logger.error(f"模拟用户行为识别失败: {e}")
        return jsonify({
            'success': False,
            'error': f'模拟预测失败: {str(e)}',
            'timestamp': time.time()
        }), 500

@app.route('/api/signal/predict_batch', methods=['POST'])
def predict_user_behavior_batch():
    """
    批量用户行为识别预测API
    """
    try:
        if not signal_inference_available or not signal_user_inference:
            return jsonify({
                'success': False,
                'error': '用户行为识别服务不可用'
            }), 500
        
        data = request.get_json()
        if not data or 'data_list' not in data:
            return jsonify({
                'success': False,
                'error': '缺少数据列表'
            }), 400
        
        data_list = data['data_list']
        if not isinstance(data_list, list):
            return jsonify({
                'success': False,
                'error': '数据列表格式错误'
            }), 400
        
        # 进行批量预测
        results = signal_user_inference.predict_batch(data_list)
        
        return jsonify({
            'success': True,
            'predictions': results,
            'count': len(results),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"批量用户行为识别预测失败: {e}")
        return jsonify({
            'success': False,
            'error': f'批量预测失败: {str(e)}'
        }), 500

@app.route('/api/signal/model_info', methods=['GET'])
def get_signal_model_info():
    """
    获取用户行为识别模型信息
    """
    try:
        if not signal_inference_available or not signal_user_inference:
            return jsonify({
                'success': False,
                'error': '用户行为识别服务不可用'
            }), 500
        
        model_info = signal_user_inference.get_model_info()
        
        return jsonify({
            'success': True,
            'model_info': model_info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取模型信息失败: {str(e)}'
        }), 500

@app.route('/api/signal/predict_from_csv', methods=['POST'])
def predict_from_csv():
    """
    从CSV数据进行用户行为识别预测
    """
    try:
        if not signal_inference_available or not signal_user_inference:
            return jsonify({
                'success': False,
                'error': '用户行为识别服务不可用'
            }), 500
        
        # 检查是否有文件上传
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': '未选择文件'
                }), 400
            
            if file and file.filename.endswith('.csv'):
                # 读取CSV文件
                import pandas as pd
                from io import StringIO
                
                # 读取文件内容
                csv_content = file.read().decode('utf-8')
                df = pd.read_csv(StringIO(csv_content))
                
                # 进行预测
                result = signal_user_inference.predict(df)
                
                return jsonify({
                    'success': True,
                    'prediction': result,
                    'data_shape': df.shape,
                    'columns': df.columns.tolist(),
                    'timestamp': time.time()
                })
        
        # 如果没有文件，检查JSON数据
        data = request.get_json()
        if not data or 'csv_data' not in data:
            return jsonify({
                'success': False,
                'error': '缺少CSV数据或文件'
            }), 400
        
        # 从JSON中的CSV数据创建DataFrame
        import pandas as pd
        df = pd.DataFrame(data['csv_data'])
        
        # 进行预测
        result = signal_user_inference.predict(df)
        
        return jsonify({
            'success': True,
            'prediction': result,
            'data_shape': df.shape,
            'columns': df.columns.tolist(),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"CSV预测失败: {e}")
        return jsonify({
            'success': False,
            'error': f'CSV预测失败: {str(e)}'
        }), 500

@app.route('/api/signal/predict_from_gps', methods=['POST'])
def predict_from_gps_data():
    """
    从GPS数据文件进行用户行为识别预测
    """
    try:
        if not signal_inference_available or not signal_user_inference:
            return jsonify({
                'success': False,
                'error': '用户行为识别服务不可用'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少输入数据'
            }), 400
        
        # 模拟GPS数据格式转换
        if 'gps_data' in data:
            gps_data = data['gps_data']
            
            # 创建模拟的传感器数据
            import pandas as pd
            import numpy as np
            
            # 根据GPS数据创建模拟的传感器数据
            num_samples = len(gps_data) if isinstance(gps_data, list) else 60
            
            # 创建模拟数据
            mock_data = {
                'cell_id': np.random.randint(0, 100, num_samples),
                'gps_id': np.random.randint(0, 30, num_samples),
                'wifi_id': np.random.randint(0, 50, num_samples),
                'cell_num': np.random.randint(1, 10, num_samples),
                'dBm': np.random.uniform(-100, -50, num_samples),
                'gps_num': np.random.randint(1, 15, num_samples),
                'Latitude': np.random.uniform(31.8, 31.9, num_samples),
                'Longitude': np.random.uniform(117.2, 117.3, num_samples),
                'Altitude': np.random.uniform(10, 100, num_samples),
                'wifi_num': np.random.randint(1, 20, num_samples),
                'SNR': np.random.uniform(0, 30, num_samples),
                'RSSI': np.random.uniform(-80, -30, num_samples),
                'Acc_x': np.random.uniform(-2, 2, num_samples),
                'Acc_y': np.random.uniform(-2, 2, num_samples),
                'Acc_z': np.random.uniform(8, 12, num_samples),
                'Gyr_x': np.random.uniform(-1, 1, num_samples),
                'Gyr_y': np.random.uniform(-1, 1, num_samples),
                'Gyr_z': np.random.uniform(-1, 1, num_samples),
                'Mag_x': np.random.uniform(-50, 50, num_samples),
                'Mag_y': np.random.uniform(-50, 50, num_samples),
                'Mag_z': np.random.uniform(-50, 50, num_samples),
                'Ori_w': np.random.uniform(-1, 1, num_samples),
                'Ori_x': np.random.uniform(-1, 1, num_samples),
                'Ori_y': np.random.uniform(-1, 1, num_samples),
                'Ori_z': np.random.uniform(-1, 1, num_samples),
                'LAcc_x': np.random.uniform(-2, 2, num_samples),
                'LAcc_y': np.random.uniform(-2, 2, num_samples),
                'LAcc_z': np.random.uniform(-2, 2, num_samples),
                'Pressure': np.random.uniform(1000, 1020, num_samples)
            }
            
            df = pd.DataFrame(mock_data)
            
            # 进行预测
            result = signal_user_inference.predict(df)
            
            return jsonify({
                'success': True,
                'prediction': result,
                'note': '基于GPS数据生成的模拟传感器数据进行预测',
                'data_shape': df.shape,
                'timestamp': time.time()
            })
        
        return jsonify({
            'success': False,
            'error': '未找到GPS数据'
        }), 400
        
    except Exception as e:
        logger.error(f"GPS数据预测失败: {e}")
        return jsonify({
            'success': False,
            'error': f'GPS数据预测失败: {str(e)}'
        }), 500

@app.route('/api/signal/status', methods=['GET'])
def get_signal_inference_status():
    """
    获取用户行为识别服务状态
    """
    try:
        status = {
            'available': signal_inference_available,
            'model_loaded': signal_user_inference.model is not None if signal_user_inference else False,
            'model_path': signal_user_inference.model_path if signal_user_inference else None,
            'labels': signal_user_inference.labels if signal_user_inference else [],
            'timestamp': time.time()
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"获取用户行为识别状态失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取状态失败: {str(e)}'
        }), 500

# ========== 新增的环境感知API ==========

@app.route('/api/environment/process_frame', methods=['POST'])
def api_environment_process_frame():
    """处理单帧环境感知数据"""
    try:
        if not environment_processor:
            return jsonify({"success": False, "error": "环境感知处理器未初始化"})
        
        # 从请求中获取图像数据
        data = request.get_json()
        if not data or 'image_data' not in data:
            return jsonify({"success": False, "error": "缺少图像数据"})
        
        # 这里可以处理base64图像数据
        # 暂时返回成功状态
        return jsonify({"success": True, "message": "帧处理请求已接收"})
        
    except Exception as e:
        logger.error(f"环境感知帧处理错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/environment/status', methods=['GET'])
def api_environment_status():
    """获取环境感知处理器状态"""
    try:
        if not environment_processor:
            return jsonify({"success": False, "error": "环境感知处理器未初始化"})
        
        status = environment_processor.get_status()
        return jsonify({"success": True, "status": status})
        
    except Exception as e:
        logger.error(f"获取环境感知状态错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/environment/start', methods=['POST'])
def api_environment_start():
    """启动环境感知处理"""
    try:
        if not environment_processor:
            return jsonify({"success": False, "error": "环境感知处理器未初始化"})
        
        # 首先确保设备管理器运行
        if device_manager and not device_manager.is_running():
            print("🚀 启动设备管理器以提供真实数据...")
            device_success = device_manager.start()
            if not device_success:
                return jsonify({"success": False, "error": "设备管理器启动失败，无法获取摄像头数据"})
            
            # 等待设备稳定
            import time
            time.sleep(2)
        
        # 启动环境感知处理
        environment_processor.start_processing()
        
        return jsonify({"success": True, "message": "环境感知处理已启动，使用真实摄像头数据"})
        
    except Exception as e:
        logger.error(f"启动环境感知处理错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/environment/stop', methods=['POST'])
def api_environment_stop():
    """停止环境感知处理"""
    try:
        if environment_processor:
            environment_processor.stop_processing()
            
        # 停止设备管理器
        if device_manager and device_manager.is_running():
            print("🛑 停止设备管理器...")
            device_manager.stop()
            
        return jsonify({"success": True, "message": "环境感知处理已停止"})
        
    except Exception as e:
        logger.error(f"停止环境感知处理错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/environment/latest_result', methods=['GET'])
def api_environment_latest_result():
    """获取最新的环境感知结果"""
    try:
        if not environment_processor:
            return jsonify({"success": False, "error": "环境感知处理器未初始化"})
        
        result = environment_processor.get_latest_result()
        if result:
            return jsonify({"success": True, "result": result})
        else:
            return jsonify({"success": False, "error": "暂无处理结果"}), 404
        
    except Exception as e:
        logger.error(f"获取环境感知结果错误: {e}")
        return jsonify({"success": False, "error": str(e)})

# ========== 删除模拟数据控制API，使用真实设备数据 ==========

@app.route('/api/device/start', methods=['POST'])
def api_device_start():
    """启动设备管理器"""
    try:
        if not device_manager:
            return jsonify({"success": False, "error": "设备管理器未初始化"})
        
        if device_manager.is_running():
            return jsonify({"success": False, "error": "设备管理器已在运行"})
        
        success = device_manager.start()
        if success:
            return jsonify({"success": True, "message": "设备管理器已启动"})
        else:
            return jsonify({"success": False, "error": "设备管理器启动失败"})
        
    except Exception as e:
        logger.error(f"启动设备管理器错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/device/stop', methods=['POST'])
def api_device_stop():
    """停止设备管理器"""
    try:
        if device_manager and device_manager.is_running():
            device_manager.stop()
            
        return jsonify({"success": True, "message": "设备管理器已停止"})
        
    except Exception as e:
        logger.error(f"停止设备管理器错误: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/device/status', methods=['GET'])
def api_device_status():
    """获取设备管理器状态"""
    try:
        if not device_manager:
            return jsonify({"success": False, "error": "设备管理器未初始化"})
        
        status = {
            'is_running': device_manager.is_running(),
            'stats': device_manager.get_stats() if device_manager.is_running() else {},
            'latest_data_available': bool(device_manager.get_latest_data().get('color') is not None) if device_manager.is_running() else False
        }
        return jsonify({"success": True, "status": status})
        
    except Exception as e:
        logger.error(f"获取设备管理器状态错误: {e}")
        return jsonify({"success": False, "error": str(e)})

# 导入用户行为识别推理模块
try:
    from utils.signal_user_inference import get_signal_user_inference
    signal_user_inference = get_signal_user_inference()
    signal_inference_available = True
    print("用户行为识别推理模块导入成功")
except Exception as e:
    print(f"导入用户行为识别推理模块失败: {e}")
    signal_user_inference = None
    signal_inference_available = False

# 导入轨迹追踪和碰撞预警管理器
try:
    from utils.trajectory_collision_manager import trajectory_collision_manager
    print("轨迹追踪和碰撞预警管理器导入成功")
except Exception as e:
    print(f"导入轨迹追踪和碰撞预警管理器失败: {e}")
    trajectory_collision_manager = None

@app.route('/api/collision/start_system', methods=['POST'])
def start_collision_system():
    """启动完整的碰撞检测系统"""
    try:
        print("🚀 启动完整的碰撞检测系统...")
        
        # 1. 首先启动设备管理器
        if device_manager and not device_manager.is_running():
            print("📷 启动设备管理器...")
            device_success = device_manager.start()
            if not device_success:
                return jsonify({
                    'success': False,
                    'error': '设备管理器启动失败，无法获取摄像头数据'
                }), 500
            
            # 等待设备稳定
            time.sleep(2)
            print("✅ 设备管理器启动成功")
        else:
            print("📷 设备管理器已在运行")
        
        # 2. 启动轨迹碰撞管理器
        if trajectory_collision_manager and not trajectory_collision_manager.is_running:
            print("🎯 启动轨迹碰撞管理器...")
            trajectory_collision_manager.start()
            
            # 等待轨迹碰撞管理器稳定
            time.sleep(1)
            print("✅ 轨迹碰撞管理器启动成功")
        else:
            print("🎯 轨迹碰撞管理器已在运行")
        
        # 3. 验证系统状态
        system_status = {
            'device_manager': device_manager.is_running() if device_manager else False,
            'trajectory_collision_manager': trajectory_collision_manager.is_running if trajectory_collision_manager else False,
            'yolo_model_loaded': trajectory_collision_manager.yolo_model is not None if trajectory_collision_manager else False,
            'global_frame_cache': trajectory_collision_manager.global_frame_cache is not None if trajectory_collision_manager else False
        }
        
        all_systems_running = all(system_status.values())
        
        return jsonify({
            'success': all_systems_running,
            'message': '碰撞检测系统启动完成' if all_systems_running else '碰撞检测系统部分启动失败',
            'system_status': system_status,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ 启动碰撞检测系统时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'启动碰撞检测系统失败: {str(e)}'
        }), 500

@app.route('/api/collision/stop_system', methods=['POST'])
def stop_collision_system():
    """停止完整的碰撞检测系统"""
    try:
        print("🛑 停止完整的碰撞检测系统...")
        
        # 1. 停止轨迹碰撞管理器
        if trajectory_collision_manager and trajectory_collision_manager.is_running:
            print("🎯 停止轨迹碰撞管理器...")
            trajectory_collision_manager.stop()
            print("✅ 轨迹碰撞管理器已停止")
        
        # 2. 停止设备管理器
        if device_manager and device_manager.is_running():
            print("📷 停止设备管理器...")
            device_manager.stop()
            print("✅ 设备管理器已停止")
        
        return jsonify({
            'success': True,
            'message': '碰撞检测系统已停止',
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ 停止碰撞检测系统时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'停止碰撞检测系统失败: {str(e)}'
        }), 500

@app.route('/api/collision/system_status', methods=['GET'])
def get_collision_system_status():
    """获取碰撞检测系统状态"""
    try:
        # 检查各个组件状态
        device_status = {
            'available': device_manager is not None,
            'running': device_manager.is_running() if device_manager else False,
            'latest_data': bool(device_manager.get_latest_data().get('color') is not None) if device_manager and device_manager.is_running() else False
        }
        
        trajectory_status = {
            'available': trajectory_collision_manager is not None,
            'running': trajectory_collision_manager.is_running if trajectory_collision_manager else False,
            'yolo_model_loaded': trajectory_collision_manager.yolo_model is not None if trajectory_collision_manager else False,
            'global_frame_cache_connected': trajectory_collision_manager.global_frame_cache is not None if trajectory_collision_manager else False
        }
        
        global_cache_status = {
            'available': global_frame_cache is not None,
            'has_data': bool(global_frame_cache.get_current_frames(['color']).get('color') is not None) if global_frame_cache else False
        }
        
        # 计算整体系统健康状态
        system_healthy = (
            device_status['running'] and 
            trajectory_status['running'] and 
            trajectory_status['yolo_model_loaded'] and
            global_cache_status['has_data']
        )
        
        return jsonify({
            'success': True,
            'system_healthy': system_healthy,
            'components': {
                'device_manager': device_status,
                'trajectory_collision_manager': trajectory_status,
                'global_frame_cache': global_cache_status
            },
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"❌ 获取碰撞检测系统状态时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'获取系统状态失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    import sys
    import threading
    
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效的端口号: {sys.argv[1]}, 使用默认端口5000")
    
    def initialize_device_manager():
        """在独立线程中初始化设备管理器"""
        try:
            if device_manager:
                print("🚀 后台初始化设备管理器...")
                
                # 检查设备是否已经在运行
                if device_manager.is_running():
                    print("✅ 设备管理器已在运行")
                    return
                
                # 尝试启动设备管理器
                success = device_manager.start()
                if success:
                    print("✅ 设备管理器后台初始化成功")
                    
                    # 等待一下确保设备完全启动
                    time.sleep(2)
                    
                    # 验证设备状态
                    if device_manager.is_running():
                        print("📊 设备管理器运行状态确认成功")
                    else:
                        print("⚠️ 设备管理器状态验证失败")
                else:
                    print("⚠️ 设备管理器初始化失败，某些功能可能不可用")
                    print("   提示：请检查DepthAI设备是否正确连接")
            else:
                print("❌ 设备管理器实例不存在")
        except Exception as e:
            print(f"❌ 设备管理器初始化异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 在独立线程中启动设备管理器，避免阻塞Flask启动
    device_thread = threading.Thread(target=initialize_device_manager, daemon=True)
    device_thread.start()
    
    print(f"服务器正在运行，访问 http://localhost:{port}")
    print("设备管理器正在后台初始化...")
    
    # 启动Flask应用，设置线程模式，关闭调试模式避免重载冲突
    app.run(threaded=True, debug=False, host="localhost", port=port, use_reloader=False)
