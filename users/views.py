from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import User, Verification
from .serializers import UserMiniSerializer, VerificationSerializer


class UserListViewset(GenericAPIView, ListModelMixin):
    serializer_class = UserMiniSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.none()
    filter_fields = (
    "id", "email", "phone_number", "nationality", "marital_status", "gender", "verification_status", "is_active",
    "is_staff")
    search_fields = (
    "id", "first_name", "last_name", "email", "phone_number", "nationality", "marital_status", "gender",
    "verification_status")
    ordering_fields = (
    "date_joined", "first_name", "last_name", "birthdate", "nationality", "gender", "verification_status")

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserDetailViewset(GenericAPIView, RetrieveModelMixin, UpdateModelMixin):
    serializer_class = UserMiniSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.none()

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
