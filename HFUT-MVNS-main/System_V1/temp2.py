import torch

# 加载 .pth 文件
model = torch.load('utils/road_model_maxmIOU75.pth')

# 保存为 .pt 文件
torch.save(model, 'utils/road_model_maxmIOU75.pt')