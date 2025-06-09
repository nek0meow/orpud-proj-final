from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserProfile, Interest
from .serializers import UserProfileSerializer, InterestSerializer

class UserProfileDetailAPI(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

class InterestListAPI(generics.ListAPIView):
    queryset = Interest.objects.all()
    serializer_class = InterestSerializer
    permission_classes = [permissions.IsAuthenticated]

class SetUserInterestsAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        interest_ids = request.data.get('interest_ids', [])
        profile.interests.set(Interest.objects.filter(id__in=interest_ids))
        profile.save()
        return Response({'status': 'ok'})

class SetUserCustomTagsAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        tags = request.data.get('custom_tags', [])
        profile.custom_tags = tags
        profile.save()
        return Response({'status': 'ok'}) 