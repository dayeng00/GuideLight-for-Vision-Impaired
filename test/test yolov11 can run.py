from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("../ultralytics-main/ultralytics/cfg/models/11/yolo11s.yaml")
    model.train()