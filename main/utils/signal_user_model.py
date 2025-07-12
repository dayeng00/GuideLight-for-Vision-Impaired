#!/usr/bin/env python
# coding: utf-8

# # 1DCNN_Embed_BiGRU

# In[1]:


import tensorflow as tf
from tensorflow.keras import datasets, layers, models, utils
from tensorflow import keras
import math
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Dropout,Conv1D,MaxPooling1D,Concatenate
from tensorflow.keras.utils import to_categorical,plot_model
import random
from PIL import Image
from skimage import io,transform
import seaborn as sns
import pylab
from scipy import signal
import warnings

warnings.filterwarnings("ignore")
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'


import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import os
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))
sign_motion = pd.read_csv("/kaggle/input/all-0414/All_04.14.csv")
sign_motion.columns


# In[2]:


sign_motion.drop(['Gra_x','Gra_y','Gra_z'],axis=1,inplace=True)


# In[3]:


# sign_motion = sign_motion.loc[:,['label','cell_num','dBm', 'gps_num','Latitude', 'Longitude', 'Altitude', 'wifi_num','SNR','RSSI','Acc_x', 'Acc_y', 'Acc_z', 'Gyr_x', 'Gyr_y', 'Gyr_z', 'Mag_x', 'Mag_y','Mag_z', 'Ori_w', 'Ori_x', 'Ori_y', 'Ori_z','LAcc_x', 'LAcc_y', 'LAcc_z', 'Pressure']]


# In[4]:


temp = sign_motion.copy(deep=False)
temp = temp['cell_id'].unique()
index = np.arange(len(temp))
temp = dict(zip(temp,index))
t = np.array(sign_motion['cell_id'])
for i,e in enumerate(t):
    if e in temp.keys():
        t[i] = temp[e]
t = pd.DataFrame(t)
t.columns = ['cell_id']
cell = t
cell.value_counts()


# In[5]:


temp = sign_motion.copy(deep=False)
temp = temp['gps_id'].unique()
index = np.arange(len(temp))
temp = dict(zip(temp,index))
t = np.array(sign_motion['gps_id'])
for i,e in enumerate(t):
    if e in temp.keys():
        t[i] = temp[e]
t = pd.DataFrame(t)
t.columns = ['gps_id']
gps = t
gps.value_counts()


# In[6]:


temp = sign_motion.copy(deep=False)
temp = temp['wifi_id'].unique()
index = np.arange(len(temp))
temp = dict(zip(temp,index))
t = np.array(sign_motion['wifi_id'])
for i,e in enumerate(t):
    if e in temp.keys():
        t[i] = temp[e]
t = pd.DataFrame(t)
t.columns = ['wifi_id']
wifi = t
wifi.value_counts()


# In[7]:


sign_motion = sign_motion.drop(['cell_id','gps_id','wifi_id'],axis=1)
sign_motion = pd.concat([sign_motion,cell,gps,wifi],axis=1)
sign_motion.head(2)


# In[8]:


def FFT(signal):
    N = 60                        # 采样点数

    fft_data = np.fft.fft(signal)
    # 这里幅值要进行一定的处理，才能得到与真实的信号幅值相对应
    fft_amp0 = np.array(np.abs(fft_data)/N*2)   # 用于计算双边谱
    direct=fft_amp0[0]
    fft_amp0[0]=0.5*direct
    N_2 = int(N/2)
    fft_amp1 = fft_amp0[0:N_2]  # 单边谱

    return fft_amp1


# In[9]:


# def DataGenerator(data,window = 60):

#     steps = int(len(data) / window)    # 确定每轮有多少个batch
#     print(steps)
#     X1 = []
#     X2 = []
#     X3 = []
#     X4 = []
#     X5 = []
#     y = []
#     for i in range(steps):
#         batch_list = data[(i * window) : (i * window) + window]
#         if max(batch_list['label']) != min(batch_list['label']):
#             continue
#         else:
#             x_1 = FFT(np.asarray(batch_list["Acc_x"]))
#             x_2 = FFT(np.asarray(batch_list["Acc_y"]))
#             x_3 = FFT(np.asarray(batch_list["Acc_z"]))
#             x_4 = FFT(np.asarray(batch_list["Gyr_x"]))
#             x_5 = FFT(np.asarray(batch_list["Gyr_y"]))
#             x_6 = FFT(np.asarray(batch_list["Gyr_z"]))
#             x_7 = FFT(np.asarray(batch_list["Mag_x"]))
#             x_8 = FFT(np.asarray(batch_list["Mag_y"]))
#             x_9 = FFT(np.asarray(batch_list["Mag_z"]))
#             x_10 = FFT(np.asarray(batch_list["Ori_w"]))
#             x_11 = FFT(np.asarray(batch_list["Ori_x"]))
#             x_12 = FFT(np.asarray(batch_list["Ori_y"]))
#             x_13 = FFT(np.asarray(batch_list["Ori_z"]))
#             x_14 = FFT(np.asarray(batch_list["LAcc_x"]))
#             x_15 = FFT(np.asarray(batch_list["LAcc_y"]))
#             x_16 = FFT(np.asarray(batch_list["LAcc_z"]))
#             x_17 = FFT(np.asarray(batch_list["Pressure"]))

#             im1 = np.vstack((x_1,x_2,x_3,x_4,x_5,x_6,x_7,x_8,x_9,x_10,x_11,x_12,x_13,x_14,x_15,x_16,x_17))
#             im1 = np.transpose(im1)
# #             im1 = np.reshape(im1,(30,17,1))

#             im2 = np.asarray(batch_list.iloc[:,1:10]) # 信号
# #             im2 = np.reshape(im2,(60,9,1))

#             im3 = np.array(batch_list['cell_id']).astype('float64')
#             im4 = np.array(batch_list['gps_id']).astype('float64')
#             im5 = np.array(batch_list['wifi_id']).astype('float64')


#             X1.append(im1)
#             X2.append(im2)
#             X3.append(im3)
#             X4.append(im4)
#             X5.append(im5)


#             batch_y = batch_list.iloc[:,0].mode()-1
#             y.append(batch_y)

#     random.seed(50)
#     random.shuffle(X1)
#     random.seed(50)
#     random.shuffle(X2)
#     random.seed(50)
#     random.shuffle(X3)
#     random.seed(50)
#     random.shuffle(X4)
#     random.seed(50)
#     random.shuffle(X5)
#     random.seed(50)
#     random.shuffle(y)
#     y = np.array(y)
#     y = to_categorical(y)
#     X1 = np.array(X1)
#     X2 = np.array(X2)
#     X3 = np.array(X3)
#     X4 = np.array(X4)
#     X5 = np.array(X5)
#     print(X1.shape)
#     print(y.shape)

#     return X1,X2,X3,X4,X5,y

# data1,data2,data3,data4,data5,target = DataGenerator(sign_motion)


# In[10]:


def DataGenerator(data,window = 60):

    steps = int(len(data) / window)    # 确定每轮有多少个batch
    print(steps)
    X1 = []
    X2 = []
    X3 = []
    X4 = []
    y = []
    for i in range(steps):
        batch_list = data[(i * window) : (i * window) + window]
        if max(batch_list['label']) != min(batch_list['label']):
            continue
        else:
            im1 = np.array(batch_list['cell_id']).astype('float64')
            im2 = np.array(batch_list['gps_id']).astype('float64')
            im3 = np.array(batch_list['wifi_id']).astype('float64')
            im4 =  np.array(batch_list.iloc[:,1:-3]).astype('float64')

            X1.append(im1)
            X2.append(im2)
            X3.append(im3)
#             im4 = np.reshape(im4,(60,26,1))
            X4.append(im4)

            batch_y = batch_list.iloc[:,0].mode()-1
            y.append(batch_y)
#     l = int(split_rate*len(X4))
    random.seed(50)
    random.shuffle(X1)
    random.seed(50)
    random.shuffle(X2)
    random.seed(50)
    random.shuffle(X3)
    random.seed(50)
    random.shuffle(X4)
    random.seed(50)
    random.shuffle(y)
    y = np.array(y)
    y = to_categorical(y)
    X1 = np.array(X1)
    X2 = np.array(X2)
    X3 = np.array(X3)
    X4 = np.array(X4)
    print(X4.shape)
    print(y.shape)

#     X_test,y_test = X4[l:],y[l:]
    return X1,X2,X3,X4,y

data1,data2,data3,data4, target = DataGenerator(sign_motion)


# In[11]:


import tensorflow as tf
from tensorflow.keras.layers import Dropout, Dense, GRU, LSTM
import matplotlib.pyplot as plt
from tensorflow.keras.callbacks import *
from tensorflow.keras.initializers import *
from tensorflow.keras.layers import *
from tensorflow.keras.models import *
from tensorflow.python.keras.layers import Layer

def evaluate_model(X_train,y_train,X_test,y_test,i):

    # cell
    model1 = tf.keras.Sequential([
        tf.keras.layers.Embedding(1500,12,input_length=60),
    ]) 
    # gps
    model2 = tf.keras.Sequential([
        tf.keras.layers.Embedding(35,6,input_length=60),
    ]) 
    # wifi
    model3 = tf.keras.Sequential([
        tf.keras.layers.Embedding(470,9,input_length=60),
    ]) 

    model4 = tf.keras.Sequential([Input(shape=(60,26))]) 

    x1 = layers.Concatenate(axis=-1)([model1.output,model2.output,model3.output,model4.output])
    x1 = tf.keras.layers.Conv1D(32, 7, activation='relu',padding="same")(x1)
    x1 = tf.keras.layers.MaxPooling1D(2,1)(x1)
    x1 = tf.keras.layers.Conv1D(64, 5, activation='relu',padding="same")(x1)
    x1 = tf.keras.layers.MaxPooling1D(2,1)(x1)
    x1 = tf.keras.layers.Bidirectional(GRU(100,return_sequences=True))(x1)
    x1 = Dropout(0.2)(x1)
    x1 = tf.keras.layers.Bidirectional(GRU(128))(x1)
    x1 = Dropout(0.2)(x1)
    x1 = Dense(8,activation='softmax')(x1)

    model = keras.Model(inputs=[model1.input,model2.input,model3.input,model4.input], outputs=x1, name="model")


    opt = tf.keras.optimizers.Adam(0.001)
    model.compile(optimizer=opt,
              loss='categorical_crossentropy',
              metrics=['acc'])
    if i == 1:
        print(model.summary())
        tf.keras.utils.plot_model(model,to_file='model.png',show_shapes=True)

    print("\n\n--------------------开始第{}次验证--------------------".format(i))

    history = model.fit(X_train, y_train,
          batch_size=128,
          epochs=100,
          validation_data=(X_test,y_test),
          verbose=1)
    model.save("model_{}.h5".format(i))

    p1 = model.predict(X_train)
    ohpre1 = np.argmax(p1, axis=1)
    y_train = np.argmax(y_train,axis=1)
    train_s = f1_score(y_train,ohpre1,average='weighted')

    pres = model.predict(X_test)
    ohpres = np.argmax(pres, axis=1)
    y_test = np.argmax(y_test, axis=1)
    test_s = f1_score(y_test,ohpres,average='weighted')

    cm = confusion_matrix(y_test,ohpres)
    cm1 = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm1 = np.round(cm1,2)

    return model,history,train_s,test_s,cm,cm1


# In[12]:


# k-折交叉验证（此处设置k=5）
# 将训练集的再抽出一部分做验证集
from sklearn import datasets
from sklearn.model_selection import KFold,StratifiedKFold,cross_val_score
from sklearn.utils.multiclass import unique_labels
from sklearn.metrics import confusion_matrix,precision_score,recall_score,f1_score
from keras.models import load_model

train_scores = []
test_scores = []
History = []
CM = []
CM1 = []

kf = KFold(n_splits = 5, shuffle=False)    # 5折



i = 0
for (train_ind, test_ind),(target1,target2) in zip(kf.split(data1),kf.split(target)):     # 将数据划分为k折

    i = i + 1
    X_train = [data1[train_ind],data2[train_ind],data3[train_ind],data4[train_ind],] #,data3[train_ind],data4[train_ind],data5[train_ind]
    y_train = target[target1]
    X_val = [data1[test_ind],data2[test_ind],data3[test_ind],data4[test_ind]] #,data5[test_ind]#选取的训练集数据下标
    y_val = target[target2]


    model,history,train_s,test_s,cm,cm1 = evaluate_model(X_train,y_train,X_val,y_val,i)

    History.append(history)
    history_df = pd.DataFrame(history.history)
    history_df.to_csv('history_{}.csv'.format(i),index=False)

    train_scores.append(train_s)
    test_scores.append(test_s)
    CM.append(cm)
    CM1.append(cm1)


# In[13]:


print(train_scores)
print(test_scores)
print('\n\n训练集交叉验证 F1-score: %.3f%% (+/-%.3f)' %(np.mean(train_scores)*100, np.std(train_scores)*100))
print('\n\n验证集交叉验证 F1-score: %.3f%% (+/-%.3f)' %(np.mean(test_scores)*100, np.std(test_scores)*100))


# In[14]:


f_test = max(test_scores)
index = test_scores.index(f_test)
print("最优训练集F1-score:",train_scores[index])
print("\n最优验证集F1-score:",f_test)


# In[15]:


h_df = pd.DataFrame(History[index].history)
h_df.to_csv("History.csv",index=False)


# In[16]:


h_df.loc[:,['loss']].plot()


# In[17]:


h_df.loc[:,['acc','val_acc']].plot()


# In[18]:


from tabulate import tabulate
import matplotlib.font_manager as fm
# plt.figure(figsize=(4,3),dpi=80)
myfont = fm.FontProperties(fname=r'../input/simhei/SimHei.ttf') # 设置字体
# cm = np.around(sum(CM)/5,decimals=0)
label=['静止','走路','跑步','自行车','汽车','公交','火车','地铁']
cm = CM[index]
print(cm)
b1,b2,b3,b4 = [],[],[],[]
for i in range(len(cm)):
    tm1 = np.round((cm[i,i]/sum(cm[i,:])),2)
    tm2 = 1-tm1
    tm3 = np.round(cm[i,i]/sum(cm[:,i]),2)
    tm4 = 1-tm3
    b1.append(tm1)
    b2.append(tm2)
    b3.append(tm3)
    b4.append(tm4)

b1 = np.reshape(b1,(8,1))
b1 = pd.DataFrame(b1)
b1.columns=['正确']
b2 = np.reshape(b2,(8,1))
# b3 = np.reshape(b3,(1,8))
b3 = np.reshape(b3,(1,8))
b3 = pd.DataFrame(b3)
b3.columns=label

cm = pd.DataFrame(cm)
cm.columns = label
cm.index = label

#创建一个宽12，高6的空白图像区域
fig=plt.figure(figsize=(12,7),dpi=300,edgecolor='Black')#

##rect可以设置子图的位置与大小
rect1 = [0.10, 0.55, 0.24, 0.35] # [左, 下, 宽, 高] 规定的矩形区域 （全部是0~1之间的数，表示比例）
rect2 = [0.10, 0.448, 0.24, 0.042]#b4
rect3 = [0.35, 0.55, 0.03, 0.35]#b1
rect4 = [0.10, 0.49, 0.24, 0.042]#b3
rect5 = [0.38, 0.55, 0.03, 0.35]#b2

ax0 = plt.axes(rect1)
rect = plt.Rectangle((0.1,0.55),0.24,0.35)
ax0.add_patch(rect)
plt.xticks([])
plt.yticks([])
#在fig中添加子图ax，并赋值位置rect
ax1 = plt.axes(rect1)
sns.heatmap(cm, annot=True, fmt='g',cmap='Blues',cbar=False,mask=(cm==0))
plt.ylabel('真实标签',fontproperties=myfont,fontsize=12)
plt.xticks([])
plt.yticks(fontproperties=myfont,fontsize=9,rotation=0)

# ax2 = plt.axes(rect2)
# sns.heatmap(b4, annot=True, fmt='g',cmap='Oranges',cbar=False,linewidths=0.01,linecolor='Black')
# plt.xticks(fontproperties=myfont,fontsize=9,rotation=0)
# plt.yticks([])
# plt.xlabel('预测标签',fontproperties=myfont,fontsize=12)

ax3 = plt.axes(rect3)
sns.heatmap(b1, annot=True, fmt='g',cmap='Greens',cbar=False,linewidths=0.01,linecolor='Black')
plt.xticks([])
plt.yticks([])
ax4 = plt.axes(rect4)
sns.heatmap(b3, annot=True, fmt='g',cmap='Greens',cbar=False,linewidths=0.01,linecolor='Black')
plt.xticks(fontproperties=myfont,fontsize=9,rotation=0)
plt.yticks([])
plt.xlabel('预测标签',fontproperties=myfont,fontsize=12)
# ax5 = plt.axes(rect5)
# sns.heatmap(b2, annot=True, fmt='g',cmap='Oranges',cbar=False,linewidths=0.01,linecolor='Black')#,linewidths=0.05,linecolor='Black'
# plt.xticks([])
# plt.yticks([])
plt.show()

