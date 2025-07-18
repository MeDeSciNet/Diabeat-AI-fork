from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadedImage
from torchvision import transforms
from PIL import Image
import torch
import torch.nn as nn
import numpy as np
import random
from torchvision import models

# 載入模型
hidden_units = 512
dropout_rate = 0.2

def set_seed(seed=42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False  # 可能會影響效能，但能保證一致性


set_seed(42)  # 設定固定種子

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# model = models.resnet18(pretrained=False)  ## pretrained parameter is deprecated, and maybe removed in future
model = models.resnet18(weights=None)  # new version test

model.fc = nn.Sequential(
    nn.Linear(model.fc.in_features, hidden_units),
    nn.ReLU(),
    nn.Dropout(dropout_rate),
    nn.Linear(hidden_units, 1)
)
model.load_state_dict(torch.load('AIchat/dish_model1.pth', map_location=device))
model = model.to(device)
model.eval()

# 定義轉換
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # 固定大小，避免隨機縮放影響結果
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

class PredictView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # 獲取圖片
        image_file = request.FILES['image']
        uploaded_image = UploadedImage(image=image_file)
        uploaded_image.save()

        # 處理圖片
        image = Image.open(uploaded_image.image.path).convert('RGB')
        image = transform(image)
        image = image.unsqueeze(0).to(device)

        # 預測
        with torch.no_grad():
            output = model(image).item()

        return Response({'predicted_value': output})
