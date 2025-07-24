# views.py
import torch
import pandas as pd
import joblib
import torch.nn as nn
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pathlib import Path

# 定義神經網路架構，需與訓練時相同
class DiabetesNet(nn.Module):
    def __init__(self, input_dim):
        super(DiabetesNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 2)  # 二元分類，輸出 2 個類別分數

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# 載入前處理器（使用訓練時儲存的 preprocessor）
grandparent = Path(__file__).parent.parent
preprocessor = joblib.load(grandparent / 'AIchat/preprocessor.joblib')

# 利用一筆 dummy 資料推算前處理後的特徵數量
dummy_data = pd.DataFrame([{
    'gender': 'male',
    'age': 0,
    'hypertension': 0,
    'heart_disease': 0,
    'smoking_history': 'never smoked',
    'bmi': 0.0,
    'HbA1c_level': 0.0,
    'blood_glucose_level': 0.0
}])
input_dim = preprocessor.transform(dummy_data).shape[1]

# 載入模型參數
model = DiabetesNet(input_dim=input_dim)
model.load_state_dict(torch.load(grandparent / 'AIchat/diabetes_model.pth', map_location=torch.device('cpu')))
model.eval()

@api_view(['POST'])
def predict_diabetes(request):
    """
    接收 POST 請求，輸入資料格式需包含下列欄位：
      - gender
      - age
      - hypertension
      - heart_disease
      - smoking_history
      - bmi
      - HbA1c_level
      - blood_glucose_level
    回傳預測結果（0 或 1）
    """
    required_fields = ['gender', 'age', 'hypertension', 'heart_disease', 'smoking_history', 'bmi', 'HbA1c_level', 'blood_glucose_level']
    data = request.data

    # 檢查是否缺少必要欄位
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return Response({'error': f"缺少欄位: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST)
    
    # 將輸入資料轉換成 DataFrame，欄位順序需與前處理器一致
    new_data = pd.DataFrame([{
        'gender': data['gender'],
        'age': data['age'],
        'hypertension': data['hypertension'],
        'heart_disease': data['heart_disease'],
        'smoking_history': data['smoking_history'],
        'bmi': data['bmi'],
        'HbA1c_level': data['HbA1c_level'],
        'blood_glucose_level': data['blood_glucose_level']
    }])
    
    # 使用前處理器轉換資料
    X_new = preprocessor.transform(new_data)
    X_new_tensor = torch.tensor(X_new, dtype=torch.float32)
    
    with torch.no_grad():
        output = model(X_new_tensor)
        _, prediction = torch.max(output, 1)
    
    # 回傳預測結果（例如：0 代表無糖尿病，1 代表有糖尿病）
    return Response({'prediction': int(prediction.item())})
