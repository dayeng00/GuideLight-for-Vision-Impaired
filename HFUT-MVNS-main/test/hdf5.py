"""
测试hdf5环境是否配置好
"""

import h5py

# 创建一个 HDF5 文件并写入数据
with h5py.File('test.h5', 'w') as f:
    data = f.create_dataset('data', data=[1, 2, 3, 4, 5])
    print(data[:])

# 读取 HDF5 文件中的数据
with h5py.File('test.h5', 'r') as f:
    data = f['data'][:]
    print(data)

