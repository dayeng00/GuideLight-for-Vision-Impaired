'''
    现在我要接九个接口，也就是对应着9个程序
    现在目前的操作
    在某个页面中点击了打开摄像头，那么摄像头处于被调用状态
    并且现在所有的页面的img-src都是指向5002端口
    所以现在我需要把端口分化
'''

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
# 引入各类视频流
from utils.disparity_estimator import DisparityEstimator
from utils.gesture_point_recognition import GesturePointRecognition
from utils.gesture_recognizer import GestureRecognizer
from utils.moblie_net_SSD_detector import OakDMobileNetSSD
from utils.person_detection_tracker_on_video import PersonDetectionTrackerOnVideo
from utils.spatial_object_tracker_on_RGB import SpatialObjectTracker
# from test_f_detector import FeaturePointStreaming
# from test_f_tracker import FeaturePointTrackerStreaming

d_estimator = None
f_detector = None
f_tracker = None
g_recognition = None
g_recognizer = None
m_detector = None
p_video = None
s_RGB = None

app = Flask(__name__, static_folder="static", template_folder="static")
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:wangzishu@localhost:3306/userdata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用对象修改追踪（可选）

# 初始化 SQLAlchemy
db = SQLAlchemy(app)


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


# 主页路由，返回 Vue 主页
@app.route("/")
def serve_index():
    return send_from_directory(app.template_folder, "index.html")


# 处理 Vue 生成的静态资源
@app.route("/<path:path>")
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)


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
    if d_estimator is None:
        d_estimator = DisparityEstimator()
    return jsonify({'message': 'Cameras started'}), 200


# 停止视差估计摄像头占用
@app.route('/d_estimator/stop_cameras', methods=['POST'])
def d_stop():
    global d_estimator
    if d_estimator is not None:
        d_estimator.shutdown()
        d_estimator.close()


# 接收get请求返回流式视频流
@app.route('/d_estimator/video_feed')
def d_feed():
    global d_estimator
    if d_estimator is not None:
        return Response(d_estimator.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


# # 启动特征点识别摄像头占用
# @app.route('/f_detector/start_cameras', methods=['POST'])
# def f_d_start():
#     global f_detector
#     if f_detector is None:
#         f_detector = FeaturePointStreaming()
#     return jsonify({'message': 'Cameras started'}), 200
#
#
# # 停止特征点识别摄像头占用
# @app.route('/f_detector/stop_cameras', methods=['POST'])
# def f_d_stop():
#     global f_detector
#     if f_detector is not None:
#         f_detector.shutdown()
#         f_detector.close()
#
#
# # 接收get请求返回流式视频流1
# @app.route('/f_detector/video_feed1')
# def f_d_feed_1():
#     global f_detector
#     if f_detector is not None:
#         return Response(f_detector.show_left(), mimetype='multipart/x-mixed-replace; boundary=frame')
#
#
# # 接收get请求返回流式视频流2
# @app.route('/f_detector/video_feed2')
# def f_d_feed_2():
#     global f_detector
#     if f_detector is not None:
#         return Response(f_detector.show_right(), mimetype='multipart/x-mixed-replace; boundary=frame')
#
#
# # 启动特征点识别摄像头占用
# @app.route('/f_tracker/start_cameras', methods=['POST'])
# def f_t_start():
#     global f_tracker
#     if f_tracker is None:
#         f_tracker = FeaturePointTrackerStreaming()
#     return jsonify({'message': 'Cameras started'}), 200
#
#
# # 停止特征点识别摄像头占用
# @app.route('/f_tracker/stop_cameras', methods=['POST'])
# def f_t_stop():
#     global f_tracker
#     if f_tracker is not None:
#         f_tracker.shutdown()
#         f_tracker.close()
#
#
# # 接收get请求返回流式视频流1
# @app.route('/f_tracker/video_feed1')
# def f_t_feed_1():
#     global f_tracker
#     if f_tracker is not None:
#         return Response(f_tracker.show_left(), mimetype='multipart/x-mixed-replace; boundary=frame')
#
#
# # 接收get请求返回流式视频流2
# @app.route('/f_tracker/video_feed2')
# def f_t_feed_2():
#     global f_tracker
#     if f_tracker is not None:
#         return Response(f_tracker.show_right(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 启动手势特征点识别摄像头占用
@app.route('/g_recognition/start_cameras', methods=['POST'])
def g_start():
    global g_recognition
    if g_recognition is None:
        g_recognition = GesturePointRecognition()
    return jsonify({'message': 'Cameras started'}), 200


# 停止手势特征点识别摄像头占用
@app.route('/g_recognition/stop_cameras', methods=['POST'])
def g_stop():
    global g_recognition
    if g_recognition is not None:
        g_recognition.shutdown()
        g_recognition.close()


# 接收get请求返回流式视频流
@app.route('/g_recognition/video_feed')
def g_feed():
    global g_recognition
    if g_recognition is not None:
        return Response(g_recognition.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 启动手势类别判断摄像头占用
@app.route('/g_recognizer/start_cameras', methods=['POST'])
def r_start():
    global g_recognizer
    if g_recognizer is None:
        g_recognizer = GestureRecognizer()
    return jsonify({'message': 'Cameras started'}), 200


# 停止手势类别判断摄像头占用
@app.route('/g_recognizer/stop_cameras', methods=['POST'])
def r_stop():
    global g_recognizer
    if g_recognizer is not None:
        g_recognizer.shutdown()
        g_recognizer.close()


# 接收get请求返回流式视频流
@app.route('/g_recognizer/video_feed')
def r_feed():
    global g_recognizer
    if g_recognizer is not None:
        return Response(g_recognizer.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 启动MobileNetSSD 目标检测摄像头占用
@app.route('/m_detector/start_cameras', methods=['POST'])
def m_start():
    global m_detector
    if m_detector is None:
        m_detector = OakDMobileNetSSD()
    return jsonify({'message': 'Cameras started'}), 200


# 停止MobileNetSSD 目标检测摄像头占用
@app.route('/m_detector/stop_cameras', methods=['POST'])
def m_stop():
    global m_detector
    if m_detector is not None:
        m_detector.shutdown()
        m_detector.close()


# 接收get请求返回流式视频流
@app.route('/m_detector/video_feed')
def m_feed():
    global m_detector
    if m_detector is not None:
        return Response(m_detector.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 启动人像追踪摄像头占用
@app.route('/p_video/start_cameras', methods=['POST'])
def p_start():
    global p_video
    if p_video is None:
        p_video = PersonDetectionTrackerOnVideo()
    return jsonify({'message': 'Cameras started'}), 200


# 停止人像追踪摄像头占用
@app.route('/p_video/stop_cameras', methods=['POST'])
def p_stop():
    global p_video
    if p_video is not None:
        p_video.shutdown()
        p_video.close()


# 接收get请求返回流式视频流
@app.route('/p_video/video_feed')
def p_feed():
    global p_video
    if p_video is not None:
        return Response(p_video.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 启动RGB摄像头占用
@app.route('/s_RGB/start_cameras', methods=['POST'])
def s_start():
    global s_RGB
    if s_RGB is None:
        s_RGB = SpatialObjectTracker()
    return jsonify({'message': 'Cameras started'}), 200


# 停止RGB摄像头占用
@app.route('/s_RGB/stop_cameras', methods=['POST'])
def s_stop():
    global s_RGB
    if s_RGB is not None:
        s_RGB.shutdown()
        s_RGB.close()


# 接收get请求返回流式视频流
@app.route('/s_RGB/video_feed')
def s_feed():
    global s_RGB
    if s_RGB is not None:
        return Response(s_RGB.run(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, host="localhost", port=5000)
