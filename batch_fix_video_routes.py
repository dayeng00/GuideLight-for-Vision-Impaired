#!/usr/bin/env python3
"""
批量修复所有视频流路由的响应头
"""

import re

def fix_video_routes():
    """修复所有视频流路由的响应头"""
    main_py_path = "main/main.py"
    
    print("🔧 批量修复视频流路由的响应头...")
    
    # 读取原文件
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义需要修复的视频流路由函数
    video_routes = [
        'f_d_feed_left', 'f_d_feed_right', 'f_d_feed',
        'f_t_feed_left', 'f_t_feed_right', 'f_t_feed',
        'g_recognition_feed', 'r_feed', 'm_feed', 'enhanced_detector_feed'
    ]
    
    for route in video_routes:
        print(f"  修复路由: {route}")
        
        # 查找函数定义
        pattern = f'def {route}\\(\\):'
        match = re.search(pattern, content)
        
        if match:
            # 找到函数开始位置
            func_start = match.start()
            
            # 查找return create_threaded_video_stream的模式
            return_pattern = r'return create_threaded_video_stream\([^)]+\)'
            
            # 在函数范围内查找return语句
            func_content = content[func_start:]
            next_def = re.search(r'\ndef ', func_content[1:])
            func_end = next_def.start() + 1 if next_def else len(func_content)
            func_content = func_content[:func_end]
            
            return_match = re.search(return_pattern, func_content)
            
            if return_match:
                # 找到return语句的位置
                return_start = func_start + return_match.start()
                return_end = func_start + return_match.end()
                
                # 获取原始的return语句
                original_return = content[return_start:return_end]
                
                # 构建新的return语句
                new_return = f'''response = Response({original_return[7:]})  # 移除"return "
        response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response'''
                
                # 替换内容
                content = content[:return_start] + new_return + content[return_end:]
                print(f"    ✅ 已修复 {route}")
            else:
                print(f"    ⚠️ 未找到 {route} 的return语句")
        else:
            print(f"    ⚠️ 未找到 {route} 函数定义")
    
    # 写回文件
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 批量修复完成")

def main():
    """主函数"""
    print("🚀 开始批量修复视频流路由...")
    fix_video_routes()
    print("✅ 所有视频流路由已修复")

if __name__ == "__main__":
    main() 