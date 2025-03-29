from flask import Flask, Response
from utils.feature_point_detector import FeaturePointDetector
from flask_cors import CORS
from main.main import f_detector
from flask import current_app
# TODO 解决资源上下文问题
app = Flask(__name__)
CORS(app)

# 接收get请求返回流式视频流 左
@app.route('/f_detector/video_feed2')
def f_d_feed_right():
    global f_detector
    if f_detector is not None:
        with app.app_context():
            return Response(f_detector.show_right(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)