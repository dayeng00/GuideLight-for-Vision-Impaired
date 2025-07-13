#!/usr/bin/env python
# coding: utf-8

"""
用户行为识别推理模型
基于signal_user_model.py训练的模型进行推理
"""

import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import Dense, Dropout, Conv1D, MaxPooling1D, Concatenate, GRU, Bidirectional, Input
from tensorflow.keras.utils import to_categorical
from tensorflow import keras
import numpy as np
import pandas as pd
import os
import json
import warnings
from typing import Dict, List, Tuple, Optional, Union
import logging

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalUserInference:
    """
    用户行为识别推理类
    """
    
    def __init__(self, model_path: str = None):
        """
        初始化推理模型
        
        Args:
            model_path: 训练好的模型路径，如果为None则使用默认路径
        """
        self.model = None
        self.model_path = model_path
        
        # 行为类别标签
        self.labels = ['静止', '走路', '跑步', '自行车', '汽车', '公交', '火车', '地铁']
        
        # 模型输入参数
        self.window_size = 60  # 时间窗口大小
        self.feature_size = 26  # 特征维度
        
        # 嵌入层参数（从训练代码中获取）
        self.cell_vocab_size = 1500
        self.gps_vocab_size = 35
        self.wifi_vocab_size = 470
        
        # 映射字典（用于ID编码）
        self.cell_id_map = {}
        self.gps_id_map = {}
        self.wifi_id_map = {}
        
        # 加载模型
        self._load_model()
    
    def _load_model(self):
        """
        加载训练好的模型
        """
        try:
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"从 {self.model_path} 加载模型...")
                self.model = load_model(self.model_path)
                logger.info("模型加载成功")
            else:
                # 尝试从默认路径加载
                default_paths = [
                    "model_1.h5",
                    "main/model_1.h5",
                    "main/resources/model_1.h5",
                    os.path.join(os.path.dirname(__file__), "model_1.h5"),
                    os.path.join(os.path.dirname(__file__), "../resources/model_1.h5")
                ]
                
                for path in default_paths:
                    if os.path.exists(path):
                        logger.info(f"从默认路径 {path} 加载模型...")
                        self.model = load_model(path)
                        self.model_path = path
                        logger.info("模型加载成功")
                        break
                
                if self.model is None:
                    logger.warning("未找到训练好的模型，将创建新模型结构（需要权重文件）")
                    self._create_model_structure()
        
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            logger.info("创建新模型结构...")
            self._create_model_structure()
    
    def _create_model_structure(self):
        """
        创建模型结构（与训练代码保持一致）
        """
        try:
            # cell embedding
            model1 = tf.keras.Sequential([
                tf.keras.layers.Embedding(self.cell_vocab_size, 12, input_length=self.window_size),
            ])
            
            # gps embedding
            model2 = tf.keras.Sequential([
                tf.keras.layers.Embedding(self.gps_vocab_size, 6, input_length=self.window_size),
            ])
            
            # wifi embedding
            model3 = tf.keras.Sequential([
                tf.keras.layers.Embedding(self.wifi_vocab_size, 9, input_length=self.window_size),
            ])
            
            # sensor data input
            model4 = tf.keras.Sequential([Input(shape=(self.window_size, self.feature_size))])
            
            # 连接所有输入
            x1 = Concatenate(axis=-1)([model1.output, model2.output, model3.output, model4.output])
            
            # 1D CNN层
            x1 = Conv1D(32, 7, activation='relu', padding="same")(x1)
            x1 = MaxPooling1D(2, 1)(x1)
            x1 = Conv1D(64, 5, activation='relu', padding="same")(x1)
            x1 = MaxPooling1D(2, 1)(x1)
            
            # 双向GRU层
            x1 = Bidirectional(GRU(100, return_sequences=True))(x1)
            x1 = Dropout(0.2)(x1)
            x1 = Bidirectional(GRU(128))(x1)
            x1 = Dropout(0.2)(x1)
            
            # 输出层
            x1 = Dense(8, activation='softmax')(x1)
            
            # 创建模型
            self.model = keras.Model(
                inputs=[model1.input, model2.input, model3.input, model4.input],
                outputs=x1,
                name="signal_user_model"
            )
            
            # 编译模型
            opt = tf.keras.optimizers.Adam(0.001)
            self.model.compile(
                optimizer=opt,
                loss='categorical_crossentropy',
                metrics=['acc']
            )
            
            logger.info("模型结构创建成功")
            
        except Exception as e:
            logger.error(f"创建模型结构失败: {e}")
            raise
    
    def _build_id_mappings(self, data: pd.DataFrame):
        """
        构建ID映射字典
        
        Args:
            data: 包含cell_id, gps_id, wifi_id的数据
        """
        # 构建cell_id映射
        if 'cell_id' in data.columns:
            unique_cells = data['cell_id'].unique()
            self.cell_id_map = {cell_id: idx for idx, cell_id in enumerate(unique_cells)}
        
        # 构建gps_id映射
        if 'gps_id' in data.columns:
            unique_gps = data['gps_id'].unique()
            self.gps_id_map = {gps_id: idx for idx, gps_id in enumerate(unique_gps)}
        
        # 构建wifi_id映射
        if 'wifi_id' in data.columns:
            unique_wifi = data['wifi_id'].unique()
            self.wifi_id_map = {wifi_id: idx for idx, wifi_id in enumerate(unique_wifi)}
    
    def _encode_ids(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        对ID进行编码
        
        Args:
            data: 原始数据
            
        Returns:
            编码后的数据
        """
        data_encoded = data.copy()
        
        # 编码cell_id
        if 'cell_id' in data_encoded.columns and self.cell_id_map:
            data_encoded['cell_id'] = data_encoded['cell_id'].map(self.cell_id_map).fillna(0)
        
        # 编码gps_id
        if 'gps_id' in data_encoded.columns and self.gps_id_map:
            data_encoded['gps_id'] = data_encoded['gps_id'].map(self.gps_id_map).fillna(0)
        
        # 编码wifi_id
        if 'wifi_id' in data_encoded.columns and self.wifi_id_map:
            data_encoded['wifi_id'] = data_encoded['wifi_id'].map(self.wifi_id_map).fillna(0)
        
        return data_encoded
    
    def preprocess_data(self, data: Union[pd.DataFrame, np.ndarray, dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        预处理输入数据
        
        Args:
            data: 输入数据，可以是DataFrame、numpy数组或字典
            
        Returns:
            处理后的四个输入数组 (cell_data, gps_data, wifi_data, sensor_data)
        """
        if isinstance(data, dict):
            # 如果是字典格式
            cell_data = np.array(data.get('cell_id', [0] * self.window_size)).astype('float64')
            gps_data = np.array(data.get('gps_id', [0] * self.window_size)).astype('float64')
            wifi_data = np.array(data.get('wifi_id', [0] * self.window_size)).astype('float64')
            sensor_data = np.array(data.get('sensor_data', np.zeros((self.window_size, self.feature_size)))).astype('float64')
            
        elif isinstance(data, pd.DataFrame):
            # 如果是DataFrame格式
            if len(data) < self.window_size:
                logger.warning(f"数据长度 {len(data)} 小于窗口大小 {self.window_size}，进行填充")
                # 填充数据到窗口大小
                padding_size = self.window_size - len(data)
                padding_data = pd.DataFrame(np.zeros((padding_size, len(data.columns))), columns=data.columns)
                data = pd.concat([data, padding_data], ignore_index=True)
            elif len(data) > self.window_size:
                # 取最后的窗口大小数据
                data = data.tail(self.window_size).reset_index(drop=True)
            
            # 构建映射并编码
            self._build_id_mappings(data)
            data_encoded = self._encode_ids(data)
            
            cell_data = np.array(data_encoded['cell_id']).astype('float64')
            gps_data = np.array(data_encoded['gps_id']).astype('float64')
            wifi_data = np.array(data_encoded['wifi_id']).astype('float64')
            
            # 传感器数据（除了label和id列的其他列）
            sensor_columns = [col for col in data_encoded.columns if col not in ['label', 'cell_id', 'gps_id', 'wifi_id']]
            sensor_data = np.array(data_encoded[sensor_columns]).astype('float64')
            
        else:
            raise ValueError("不支持的数据格式")
        
        # 确保数据形状正确
        if cell_data.shape[0] != self.window_size:
            cell_data = np.pad(cell_data, (0, max(0, self.window_size - cell_data.shape[0])), 'constant')[:self.window_size]
        
        if gps_data.shape[0] != self.window_size:
            gps_data = np.pad(gps_data, (0, max(0, self.window_size - gps_data.shape[0])), 'constant')[:self.window_size]
        
        if wifi_data.shape[0] != self.window_size:
            wifi_data = np.pad(wifi_data, (0, max(0, self.window_size - wifi_data.shape[0])), 'constant')[:self.window_size]
        
        if sensor_data.shape[0] != self.window_size:
            if len(sensor_data.shape) == 1:
                sensor_data = sensor_data.reshape(-1, 1)
            sensor_data = np.pad(sensor_data, ((0, max(0, self.window_size - sensor_data.shape[0])), (0, 0)), 'constant')[:self.window_size]
        
        if sensor_data.shape[1] != self.feature_size:
            if sensor_data.shape[1] < self.feature_size:
                padding = np.zeros((sensor_data.shape[0], self.feature_size - sensor_data.shape[1]))
                sensor_data = np.hstack([sensor_data, padding])
            else:
                sensor_data = sensor_data[:, :self.feature_size]
        
        # 添加批次维度
        cell_data = np.expand_dims(cell_data, axis=0)
        gps_data = np.expand_dims(gps_data, axis=0)
        wifi_data = np.expand_dims(wifi_data, axis=0)
        sensor_data = np.expand_dims(sensor_data, axis=0)
        
        return cell_data, gps_data, wifi_data, sensor_data
    
    def predict(self, data: Union[pd.DataFrame, np.ndarray, dict]) -> Dict:
        """
        进行预测
        
        Args:
            data: 输入数据
            
        Returns:
            预测结果字典
        """
        if self.model is None:
            raise ValueError("模型未加载，请先加载模型或提供模型路径")
        
        try:
            # 预处理数据
            cell_data, gps_data, wifi_data, sensor_data = self.preprocess_data(data)
            
            # 进行预测
            prediction = self.model.predict([cell_data, gps_data, wifi_data, sensor_data], verbose=0)
            
            # 解析预测结果
            predicted_class = np.argmax(prediction[0])
            confidence = float(prediction[0][predicted_class])
            
            # 构建结果
            result = {
                'predicted_class': int(predicted_class),
                'predicted_label': self.labels[predicted_class],
                'confidence': confidence,
                'probabilities': {
                    self.labels[i]: float(prediction[0][i]) for i in range(len(self.labels))
                },
                'raw_prediction': prediction[0].tolist()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise
    
    def predict_batch(self, data_list: List[Union[pd.DataFrame, np.ndarray, dict]]) -> List[Dict]:
        """
        批量预测
        
        Args:
            data_list: 输入数据列表
            
        Returns:
            预测结果列表
        """
        results = []
        for data in data_list:
            try:
                result = self.predict(data)
                results.append(result)
            except Exception as e:
                logger.error(f"批量预测中的单个样本失败: {e}")
                results.append({
                    'error': str(e),
                    'predicted_class': -1,
                    'predicted_label': 'error',
                    'confidence': 0.0
                })
        
        return results
    
    def get_model_info(self) -> Dict:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        info = {
            'model_loaded': self.model is not None,
            'model_path': self.model_path,
            'labels': self.labels,
            'window_size': self.window_size,
            'feature_size': self.feature_size,
            'cell_vocab_size': self.cell_vocab_size,
            'gps_vocab_size': self.gps_vocab_size,
            'wifi_vocab_size': self.wifi_vocab_size
        }
        
        if self.model is not None:
            info['model_summary'] = []
            self.model.summary(print_fn=lambda x: info['model_summary'].append(x))
        
        return info
    
    def save_mappings(self, filepath: str):
        """
        保存ID映射字典
        
        Args:
            filepath: 保存路径
        """
        mappings = {
            'cell_id_map': self.cell_id_map,
            'gps_id_map': self.gps_id_map,
            'wifi_id_map': self.wifi_id_map
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
        
        logger.info(f"ID映射已保存到 {filepath}")
    
    def load_mappings(self, filepath: str):
        """
        加载ID映射字典
        
        Args:
            filepath: 映射文件路径
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            self.cell_id_map = mappings.get('cell_id_map', {})
            self.gps_id_map = mappings.get('gps_id_map', {})
            self.wifi_id_map = mappings.get('wifi_id_map', {})
            
            logger.info(f"ID映射已从 {filepath} 加载")
            
        except Exception as e:
            logger.error(f"加载ID映射失败: {e}")


# 创建全局推理实例
_inference_instance = None

def get_signal_user_inference(model_path: str = None) -> SignalUserInference:
    """
    获取用户行为识别推理实例（单例模式）
    
    Args:
        model_path: 模型路径
        
    Returns:
        推理实例
    """
    global _inference_instance
    
    if _inference_instance is None:
        _inference_instance = SignalUserInference(model_path)
    
    return _inference_instance 