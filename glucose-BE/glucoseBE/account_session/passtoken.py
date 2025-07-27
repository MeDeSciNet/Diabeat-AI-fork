from rest_framework.permissions import AllowAny  # 引入 AllowAny
from .Serializer import CustomLoginSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status

class CustomLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = CustomLoginSerializer(data=request.data)
        if serializer.is_valid():
                user = serializer.validated_data
                refresh = RefreshToken.for_user(user)
                refresh['username'] = user.username
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'username': str(user.username),  # new field
                    'message': "request successful",
                    "success": True                  
                }, status=status.HTTP_200_OK )
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)