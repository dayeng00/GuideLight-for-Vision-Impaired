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
from flask import Flask, request, jsonify, Response, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
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

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# 添加响应头，禁用缓存
@app.after_request
def add_header(response):
    """
    添加响应头，禁用缓存
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
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
    db = SQLAlchemy(app)
    db_available = True
except Exception as e:
    print(f"数据库连接错误: {e}")
    print("使用SQLite作为备用数据库")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
                time=datetime.datetime.now()
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
            time=datetime.datetime.now()
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
            time=datetime.datetime.now()
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
    global d_estimator
    if d_estimator is not None:
        return Response(d_estimator.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")


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
    global f_detector
    print("请求左侧视频流")
    try:
        if f_detector is not None:
            # 添加缓存控制和必要的响应头
            response = Response(
                f_detector.show_left(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
            # 添加缓存控制头，防止浏览器缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Connection'] = 'close'
            return response
        else:
            print("视频流未初始化")
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取左侧视频流失败: {str(e)}")
        return jsonify({'message': f'获取视频流失败: {str(e)}'}), 500
    
# 接收get请求返回流式视频流 右
@app.route('/f_detector/video_feed_right')
def f_d_feed_right():
    global f_detector
    print("请求右侧视频流")
    try:
        if f_detector is not None:
            # 添加缓存控制和必要的响应头
            response = Response(
                f_detector.show_right(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
            # 添加缓存控制头，防止浏览器缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Connection'] = 'close'
            return response
        else:
            print("视频流未初始化")
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取右侧视频流失败: {str(e)}")
        return jsonify({'message': f'获取视频流失败: {str(e)}'}), 500


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
    # 返回左侧视频流
    try:
        global f_tracker
        if f_tracker is not None:
            # 添加缓存控制和必要的响应头
            response = Response(
                f_tracker.show_left(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
            # 添加缓存控制头，防止浏览器缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Connection'] = 'close'
            return response
        else:
            print("视频流未初始化")
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取左侧视频流失败: {str(e)}")
        abort(500, description=f"获取视频流失败: {str(e)}")

@app.route('/f_tracker/video_feed_right')
def f_t_feed_right():
    # 返回右侧视频流
    try:
        global f_tracker
        if f_tracker is not None:
            # 添加缓存控制和必要的响应头
            response = Response(
                f_tracker.show_right(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
            # 添加缓存控制头，防止浏览器缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Connection'] = 'close'
            return response
        else:
            print("视频流未初始化")
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取右侧视频流失败: {str(e)}")
        abort(500, description=f"获取视频流失败: {str(e)}")


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
    """获取手势识别视频流"""
    try:
        global g_recognition
        if g_recognition is not None:
            return Response(g_recognition.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
        else:
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取视频流失败: {str(e)}")
        return jsonify({'message': f'获取视频流失败: {str(e)}'}), 500


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
    try:
        print("g_recognizer is not None")
        global g_recognizer
        if g_recognizer is not None:
            return Response(g_recognizer.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
        else:
            abort(404, description="视频流未初始化")
    except Exception as e:
        print(f"获取视频流失败: {str(e)}")
        return jsonify({'message': f'获取视频流失败: {str(e)}'}), 500


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
                time=datetime.datetime.now()
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

@app.route('/api/health')
def health_check():
    status = {
        'status': 'online',
        'modules': {
            'video_modules': video_modules_available,
            'database': db_available
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
    global d_estimator, f_detector, f_tracker, g_recognition, g_recognizer, m_detector, p_video, s_RGB
    
    print("程序退出，正在安全关闭所有摄像头...")
    
    # 创建摄像头名称映射
    cameras = {
        'd_estimator': d_estimator,
        'f_detector': f_detector,
        'f_tracker': f_tracker,
        'g_recognition': g_recognition,
        'g_recognizer': g_recognizer,
        'm_detector': m_detector,
        'p_video': p_video,
        's_RGB': s_RGB
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
    
    print("所有摄像头已关闭")

atexit.register(cleanup)

if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效的端口号: {sys.argv[1]}, 使用默认端口5000")
    
    print(f"服务器正在运行，访问 http://localhost:{port}")
    app.run(threaded=True, debug=True, host="localhost", port=port)
