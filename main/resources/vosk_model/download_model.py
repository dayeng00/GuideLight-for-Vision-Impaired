"""
下载Vosk中文语音识别模型
"""

import os
import sys
import urllib.request
import zipfile
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 可用的中文模型
MODELS = {
    'small': {
        'name': 'vosk-model-small-cn-0.22',
        'url': 'https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip',
        'size': '38M'
    },
    'standard': {
        'name': 'vosk-model-cn-0.22',
        'url': 'https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip',
        'size': '1.1G'
    }
}

def download_model(model_type='small'):
    """
    下载并解压Vosk中文模型
    
    Args:
        model_type: 模型类型，'small'或'standard'
    """
    if model_type not in MODELS:
        logger.error(f"不支持的模型类型: {model_type}，支持的类型有: {', '.join(MODELS.keys())}")
        return False
    
    model = MODELS[model_type]
    model_name = model['name']
    model_url = model['url']
    model_size = model['size']
    
    # 创建模型目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"开始下载 {model_name} 模型 (大小: {model_size})...")
    logger.info(f"下载地址: {model_url}")
    
    # 下载模型
    zip_path = os.path.join(current_dir, f"{model_name}.zip")
    try:
        # 创建进度条
        def report_progress(blocknum, blocksize, totalsize):
            percent = min(int(blocknum * blocksize * 100 / totalsize), 100)
            sys.stdout.write(f"\r下载进度: {percent}% [{blocknum * blocksize}/{totalsize} bytes]")
            sys.stdout.flush()
        
        # 如果用户指定了不下载，则跳过下载步骤
        if '--no-download' not in sys.argv:
            urllib.request.urlretrieve(model_url, zip_path, report_progress)
            print("\n下载完成！")
            
            # 解压模型
            logger.info(f"正在解压模型文件到: {current_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(current_dir)
            
            # 将模型文件移动到当前目录
            model_dir = os.path.join(current_dir, model_name)
            for item in os.listdir(model_dir):
                s = os.path.join(model_dir, item)
                d = os.path.join(current_dir, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            # 清理
            shutil.rmtree(model_dir)
            os.remove(zip_path)
            
            logger.info(f"模型 {model_name} 已成功下载并解压!")
        else:
            logger.info("跳过下载步骤，仅复制现有模型文件")
        
        # 复制模型到vosk_audio目录
        vosk_audio_model_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'utils', 'vosk_audio', 'model')
        
        # 确保目标目录存在
        os.makedirs(vosk_audio_model_dir, exist_ok=True)
        
        logger.info(f"正在复制模型文件到: {vosk_audio_model_dir}")
        
        # 复制模型文件
        for item in os.listdir(current_dir):
            s = os.path.join(current_dir, item)
            d = os.path.join(vosk_audio_model_dir, item)
            
            # 跳过Python脚本和其他非模型文件
            if item.endswith('.py') or item == 'README.md' or item == 'requirements.txt':
                continue
                
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
                logger.info(f"已复制目录: {item}")
            else:
                shutil.copy2(s, d)
                logger.info(f"已复制文件: {item}")
        
        logger.info(f"模型文件已成功复制到: {vosk_audio_model_dir}")
        return True
        
    except Exception as e:
        logger.error(f"下载、解压或复制模型时出错: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

def main():
    """主函数"""
    print("Vosk中文语音识别模型下载工具")
    print("===========================")
    print("可用的模型:")
    for key, model in MODELS.items():
        print(f" - {key}: {model['name']} (大小: {model['size']})")
    
    model_type = input("\n请选择要下载的模型类型 [small/standard] (默认: small): ").strip().lower() or 'small'
    if model_type not in MODELS:
        print(f"不支持的模型类型: {model_type}，将使用默认的small模型")
        model_type = 'small'
    
    print(f"\n将下载 {model_type} 模型 ({MODELS[model_type]['name']}, 大小: {MODELS[model_type]['size']})")
    confirm = input("是否继续? [y/N]: ").strip().lower()
    
    if confirm == 'y':
        success = download_model(model_type)
        if success:
            print("\n模型下载和安装完成！")
            print("现在可以在语音识别中使用Vosk进行离线识别了。")
        else:
            print("\n模型下载或安装失败。请检查网络连接后重试。")
    else:
        print("\n已取消下载。")

if __name__ == "__main__":
    main() 