from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from . import jwtdecoder
from .models import BloodSugarRecord, get_time_slot
from .serializers import BloodSugarRecordSerializer
from django.contrib.auth import get_user_model
from .models import BloodSugarComparison
from .serializers import BloodSugarComparisonSerializer
from .models import UserModelConsent, UserPersonalizedModel
from .serializers import UserModelConsentSerializer, UserPersonalizedModelSerializer
from .model_service import train_personalized_model, predict_with_personalized_model, get_training_status, train_personalized_model_thread
# 在 views.py 文件頂部添加導入
import threading
User = get_user_model()


class BloodSugarRecordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        取得當前已驗證使用者的所有血糖紀錄
        """
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        records = BloodSugarRecord.objects.filter(user=user_instance).order_by('-created_at')
        serializer = BloodSugarRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        now = timezone.now()
        slot = get_time_slot(now)

        # 複製一份 request.data，以便加入系統欄位
        data = request.data.copy()
        data['time_slot'] = slot.isoformat()

        # 判斷是否有提供胰島素注射量
        insulin_injection = data.get('insulin_injection')
        has_insulin = (insulin_injection not in [None, '', 'null'])

        # 處理現有記錄覆蓋邏輯
        if not has_insulin:
            existing_record = BloodSugarRecord.objects.filter(
                user=user_instance,
                time_slot=slot,
                insulin_injection__isnull=True
            ).first()
            if existing_record:
                serializer = BloodSugarRecordSerializer(existing_record, data=data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 建立新記錄
        data['user'] = user_instance
        serializer = BloodSugarRecordSerializer(data=data)
        if serializer.is_valid():
            new_record = serializer.save(user=user_instance)
            
            # 檢查過去12小時內是否有記錄，如果有則創建比較記錄
            twelve_hours_ago = now - timedelta(hours=12)
            previous_records = BloodSugarRecord.objects.filter(
                user=user_instance,
                created_at__gte=twelve_hours_ago,
                created_at__lt=new_record.created_at
            ).order_by('-created_at')
            
            if previous_records.exists():
                previous_record = previous_records.first()
                
                # 創建比較記錄
                comparison = BloodSugarComparison(
                    user=user_instance,
                    previous_record=previous_record,
                    current_record=new_record,
                    previous_blood_glucose=previous_record.blood_glucose,
                    current_blood_glucose=new_record.blood_glucose,
                    insulin_injection=previous_record.insulin_injection,
                    carbohydrate_intake=previous_record.carbohydrate_intake,
                    time_interval=new_record.created_at - previous_record.created_at
                )
                comparison.save()
                # 創建比較記錄後，檢查是否達到訓練條件
                if comparison.user:
                    # 獲取用戶的同意狀態和比較記錄數量
                    consent = UserModelConsent.objects.filter(user=comparison.user, has_consented=True).first()
                    if consent:
                        # 檢查記錄數量是否達到閾值
                        comparison_count = BloodSugarComparison.objects.filter(user=comparison.user).count()
                        if comparison_count >= 20:
                            # 檢查用戶是否已有訓練過的模型
                            user_model = UserPersonalizedModel.objects.filter(user=comparison.user).first()
                            if not user_model or not user_model.is_trained:
                                # 使用線程進行訓練，避免阻塞
                                try:
                                    # 啟動後台訓練線程，不等待結果
                                    threading.Thread(
                                        target=lambda: train_personalized_model_thread(comparison.user),
                                        daemon=True
                                    ).start()
                                except Exception as e:
                                    print(f"啟動訓練模型線程時發生錯誤: {str(e)}")
                    # 添加以下返回語句
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                # 當序列化器驗證失敗時返回錯誤信息
                return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class BloodSugarComparisonAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        取得當前已驗證使用者的所有血糖比較紀錄
        """
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        comparisons = BloodSugarComparison.objects.filter(user=user_instance).order_by('-created_at')
        serializer = BloodSugarComparisonSerializer(comparisons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class UserModelConsentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """取得用戶是否同意模型訓練的設定"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        
        consent, created = UserModelConsent.objects.get_or_create(user=user_instance)
        serializer = UserModelConsentSerializer(consent)
        return Response(serializer.data)
    
    def post(self, request):
        """更新用戶的模型訓練同意設定"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        
        consent, created = UserModelConsent.objects.get_or_create(user=user_instance)
        
        # 從請求中獲取同意狀態
        has_consented = request.data.get('has_consented', False)
        
        # 更新同意狀態
        consent.has_consented = has_consented
        if has_consented:
            consent.consent_date = timezone.now()
        consent.save()
        
        serializer = UserModelConsentSerializer(consent)
        return Response(serializer.data)

class UserModelTrainingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """獲取用戶的模型訓練狀態"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        
        # 檢查是否有足夠的數據
        comparison_count = BloodSugarComparison.objects.filter(user=user_instance).count()
        
        # 獲取模型狀態
        model, created = UserPersonalizedModel.objects.get_or_create(user=user_instance)
        serializer = UserPersonalizedModelSerializer(model)
        
        # 獲取訓練狀態
        status_code, status_message = get_training_status(user_instance.id)
        
        # 返回模型狀態與數據準備情況
        response_data = serializer.data
        response_data['comparison_count'] = comparison_count
        response_data['has_enough_data'] = comparison_count >= 20
        
        # 添加訓練狀態
        if status_code:
            response_data['training_status'] = status_code
            response_data['training_message'] = status_message
        
        return Response(response_data)
    
    def post(self, request):
        """開始訓練用戶的個人化模型"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        
        # 檢查用戶是否已同意
        try:
            consent = UserModelConsent.objects.get(user=user_instance)
            if not consent.has_consented:
                return Response({"error": "用戶尚未同意模型訓練"}, status=status.HTTP_403_FORBIDDEN)
        except UserModelConsent.DoesNotExist:
            return Response({"error": "用戶尚未設定模型訓練同意狀態"}, status=status.HTTP_403_FORBIDDEN)
        
        # 檢查是否有足夠的數據
        comparison_count = BloodSugarComparison.objects.filter(user=user_instance).count()
        if comparison_count < 20:
            return Response({"error": f"數據不足，無法訓練模型。目前僅有 {comparison_count} 筆資料，需要至少 20 筆。"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 開始訓練模型（使用線程）
        try:
            success, message = train_personalized_model_thread(user_instance)
            if success:
                return Response({"message": message}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"message": message}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"啟動模型訓練失敗: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PersonalizedPredictionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """使用用戶的個人化模型進行預測"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usernameFromDecoder = jwtdecoder.jwtdecode(token)
        user_instance = User.objects.get(username=usernameFromDecoder)
        
        # 檢查用戶是否有訓練好的模型
        try:
            model = UserPersonalizedModel.objects.get(user=user_instance, is_trained=True)
        except UserPersonalizedModel.DoesNotExist:
            return Response({"error": "您尚未訓練個人化模型"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 獲取輸入特徵
        try:
            features = {
                '上次血糖': float(request.data.get('previous_blood_glucose')),
                '胰島素注射量': float(request.data.get('insulin_injection') or 0),
                '碳水攝取量': float(request.data.get('carbohydrate_intake') or 0),
                '時間間隔': float(request.data.get('time_interval') or 0)  # 時間間隔，單位為小時
            }
        except (ValueError, TypeError):
            return Response({"error": "輸入特徵格式不正確"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 進行預測
        try:
            predicted_blood_glucose, predicted_time = predict_with_personalized_model(user_instance, features)
            
            # 返回預測結果
            return Response({
                "predicted_blood_glucose": float(predicted_blood_glucose),
                "predicted_time": float(predicted_time),
                "model_version": model.model_version,
                "last_trained": model.last_trained,
                "model_performance": model.model_performance
            })
        except Exception as e:
            return Response({"error": f"預測過程中發生錯誤: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)