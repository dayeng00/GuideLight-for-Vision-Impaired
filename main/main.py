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
    video_modules_available = True
except Exception as e:
    print(f"导入视频流模块时出错: {e}")
    print("部分功能可能不可用")
    video_modules_available = False


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

try:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:wangzishu@localhost:3306/userdata'
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
    if exist(username):
        user = userdata.query.filter_by(name=username).first()
        if check_password_hash(user.password, password):
            # 记录操作的所有信息到另一个数据库
            new_log = userdata(name=username, password='', category="login")
            db.session.add(new_log)
            db.session.commit()
            return jsonify({'message': '登录成功'}), 200

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


# 启动视差估计摄像头占用
@app.route('/d_estimator/start_cameras', methods=['POST'])
def d_start():
    global d_estimator
    try:
        if d_estimator is None:
            d_estimator = DisparityEstimator()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止视差估计摄像头占用
@app.route('/d_estimator/stop_cameras', methods=['POST'])
def d_stop():
    global d_estimator
    try:
        if d_estimator is not None:
            d_estimator.shutdown()
            d_estimator = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
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
    try:
        if f_detector is None:
            f_detector = FeaturePointDetector()
            f_detector.run()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500

# 停止特征点识别摄像头占用
@app.route('/f_detector/stop_cameras', methods=['POST'])
def f_d_stop():
    global f_detector
    try:
        if f_detector is not None:
            f_detector.shutdown()
            f_detector = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500

# 接收get请求返回流式视频流 左
@app.route('/f_detector/video_feed1')
def f_d_feed_left():
    global f_detector
    if f_detector is not None:
        return Response(f_detector.show_left(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")
    
# 接收get请求返回流式视频流 左
@app.route('/f_detector/video_feed2')
def f_d_feed_right():
    global f_detector
    if f_detector is not None:
        return Response(f_detector.show_right(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")


# # f_tracker
# @app.route('f_tracker/start_camera', methods=['POST'])
# def f_t_start():
#     global f_tracker
#     if f_tracker is None:
#         # 启动摄像头 处理视频流
#         f_tracker = FeaturePointTracker()
#         f_tracker.run()
#         return jsonify({'message':'Camera started'}), 200
    
# # f_tracker stop using this
# @app.route('f_tracker/stop_camera', methods=['POST'])
# def f_t_stop():
#     global f_tracker
#     if f_tracker is not None:
#         # 调用shutdown函数 中断摄像头控制
#         f_tracker.shut_down()
        
#         return jsonify({'message': "Camera stoped"}), 200
    
# @app.route('f_tracker/video_feed1')
# def f_t_feed_left():
#     # 返回视频流
#     global f_tracker
#     if f_tracker is not None:
#         return Response(f_tracker.show_left(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('f_tracker/video_feed2')
# def f_t_feed_right():
#     # 返回视频流
#     global f_tracker
#     if f_tracker is not None:
#         return Response(f_tracker.show_right(), mimetype='multipart/x-mixed-replace; boundary=frame')



# 启动 手势特征点 识别摄像头占用
@app.route('/g_recognition/start_cameras', methods=['POST'])
def g_start():
    global g_recognition
    try:
        if g_recognition is None:
            g_recognition = GesturePointRecognition()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止 手势特征点 识别摄像头占用
@app.route('/g_recognition/stop_cameras', methods=['POST'])
def g_stop():
    global g_recognition
    try:
        if g_recognition is not None:
            g_recognition.shutdown()
            g_recognition = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
    except Exception as e:
        return jsonify({'message': f'停止失败: {str(e)}'}), 500


# 接收get请求返回流式视频流
@app.route('/g_recognition/video_feed')
def g_feed():
    global g_recognition
    if g_recognition is not None:
        return Response(g_recognition.run(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        abort(404, description="视频流未初始化")


# 启动手势类别判断摄像头占用
@app.route('/g_recognizer/start_cameras', methods=['POST'])
def r_start():
    global g_recognizer
    try:
        if g_recognizer is None:
            g_recognizer = GestureRecognizer()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        print(f"启动失败: {str(e)}")
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止手势类别判断摄像头占用
@app.route('/g_recognizer/stop_cameras', methods=['POST'])
def r_stop():
    global g_recognizer
    try:
        if g_recognizer is not None:
            g_recognizer.shutdown()
            g_recognizer = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
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
    try:
        if m_detector is None:
            m_detector = OakDMobileNetSSD()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止MobileNetSSD 目标检测摄像头占用
@app.route('/m_detector/stop_cameras', methods=['POST'])
def m_stop():
    global m_detector
    try:
        if m_detector is not None:
            m_detector.shutdown()
            m_detector = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
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
    try:
        if p_video is None:
            p_video = PersonDetectionTrackerOnVideo()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止人像追踪摄像头占用
@app.route('/p_video/stop_cameras', methods=['POST'])
def p_stop():
    global p_video
    try:
        if p_video is not None:
            p_video.shutdown()
            p_video = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
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


# 启动RGB摄像头占用
@app.route('/s_RGB/start_cameras', methods=['POST'])
def s_start():
    global s_RGB
    try:
        if s_RGB is None:
            s_RGB = SpatialObjectTracker()
        return jsonify({'message': 'Cameras started'}), 200
    except Exception as e:
        return jsonify({'message': f'启动失败: {str(e)}'}), 500


# 停止RGB摄像头占用
@app.route('/s_RGB/stop_cameras', methods=['POST'])
def s_stop():
    global s_RGB
    try:
        if s_RGB is not None:
            s_RGB.shutdown()
            s_RGB = None
            return jsonify({'message': 'Cameras stopped'}), 200
        return jsonify({'message': 'Cameras already stopped'}), 200
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
    global d_estimator, f_detector, g_recognition, g_recognizer, m_detector, p_video, s_RGB
    
    for camera in [d_estimator, f_detector, g_recognition, g_recognizer, m_detector, p_video, s_RGB]:
        if camera is not None:
            try:
                camera.shutdown()
            except:
                pass

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
