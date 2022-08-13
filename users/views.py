from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from .models import User, Verification
from .serializers import UserMiniSerializer, VerificationSerializer
from .utils import is_username_phone_number, is_username_email
from notifications.tasks.tasks_sms import send_sms_task
from notifications.tasks.tasks_email import send_email_task
from .tasks.tasks_verification import schedule_expiration


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


class AuthenticationViewset(ViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        permission_classes = [AllowAny]
        if self.action == 'logout':
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path="request-verification-code", name='request_verification_code')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Email or phone number'),
            },
            required=['username']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Verification code sent to email or phone number",
                examples={
                    "application/json": {
                        "detail": "Verification code has been sent to username"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account lookup exception: Wrong email, phone, inactive account, account with no password "
                            "or password reset enforcement active",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login "
                    },
                }
            ),
        })
    def request_verification_code(self, request):
        username = request.data.get("username")

        filter_params = {}

        if is_username_phone_number(username=username):
            filter_params = {
                "phone_number": username
            }

        elif is_username_email(username=username):
            filter_params = {
                "email": username
            }

        if not bool(filter_params):
            return Response({"detail": "Valid email or phone number is not supplied"}, status=400)

        if request.data.get("country_code"):
            filter_params["country_code"] = request.data.get("country_code")

        user = User.objects.filter(**filter_params).first()

        if not user:
            user = User(**filter_params)
            user.set_unusable_password()

            try:
                user.save()
            except Exception as e:
                return Response({"detail": str(e)}, status=400)

        if not user.is_active:
            return Response({"detail": "The account is not active"}, status=400)

        verification, _ = Verification.objects.get_or_create(
            user=user,
            is_valid=True,
            is_used=False
        )

        schedule_expiration.delay(verification_code=verification.code)

        message = "{code} is your UAMS verification code. It expires in 5 minutes.".format(code=verification.code)

        if is_username_phone_number(username):
            send_sms_task.delay(phone_numbers=[username], message=message)
        if is_username_email(username):
            subject = "UAMS Authentication"
            email_message = "<p><b>{code}</b> is your UAMS verification code. It expires in 5 minutes.</p>".format(
                code=verification.code)
            send_email_task.delay(emails=[username], subject=subject, message=email_message)

        return Response(
            {"detail": "Verification code has been sent to {username}.".format(username=username)},
            status=200)