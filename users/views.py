from django.contrib.auth import logout, authenticate
from django.contrib.auth.password_validation import validate_password, password_changed
from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_post_parameters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
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
    ordering = "-date_joined"
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


class VerificationsViewset(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path="upload-verification-documents",
            name='upload-verification-documents')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'nid_document': openapi.Schema(type=openapi.TYPE_FILE, description='National ID image'),
                'nid_number': openapi.Schema(type=openapi.TYPE_STRING, description='National ID number'),
            },
            required=['nid_document', 'nid_number']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Data uploaded successfully",
                examples={
                    "application/json": {
                        "detail": "The verification in underway"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "National ID or National ID image is not provided | The user account status is VERIFIED"
                    },
                }
            ),
        })
    def upload_verification_data(self, request):
        """
        Upload account verification data
        """
        nid_document = request.data.get('nid_document')
        nid = request.data.get('nid_number')

        if not nid_document or not nid:
            return Response({"detail": "National ID or National ID image is not provided"}, status=400)

        if request.user.verification_status == "VERIFIED" or request.user.verification_status == "PENDING VERIFICATION":
            return Response({"detail": f"The user account status is {request.user.verification_status}"}, status=400)

        user = request.user

        user.nid_document = nid_document
        user.nid_number = nid
        user.verification_status = "PENDING VERIFICATION"
        user.save()

        return Response({"detail": "The verification in underway"}, status=200)

    @action(detail=False, methods=['post'], url_path="verify-account", name='verify-account')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user': openapi.Schema(type=openapi.TYPE_STRING, description='User ID'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Verification status'),
            },
            required=['user', 'status']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Account verification is updated",
                examples={
                    "application/json": {
                        "detail": "Account verification is updated"
                    }
                }
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Account/verification is failed",
                examples={
                    "application/json": {
                        "detail": "You don't have permissions to perform this operation"
                    },
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "Account with the id is not found | Verification status is not provided"
                    },
                }
            ),
        })
    def verify_account(self, request):
        """
        Verify account
        """
        if not request.user.is_staff:
            return Response({"detail": "You don't have permissions to perform this operation"}, status=403)

        user_id = request.data.get("user")

        user = User.objects.filter(id=user_id, is_active=True).first()

        if not user:
            return Response({"detail": "Account with the id is not found"}, status=400)

        if user.verification_status != "PENDING VERIFICATION":
            return Response({"detail": f"User with {user.verification_status} cannot be verified"}, status=400)

        verification_status = request.data.get("verification_status")

        if not verification_status:
            return Response({"detail": "Verification status is not provided"}, status=400)

        accepted_statues = ("UNVERIFIED", "VERIFIED")

        if verification_status not in accepted_statues:
            return Response({"detail": "Invalid status is provided"}, status=400)

        user.verification_status = verification_status
        user.save()

        """
        Notify user about the verification status
        """
        if user.email:
            subject = "Account verification status"
            message = f"<p>Your account verification status has been changed to {verification_status}</p>"
            emails = [user.email]
            send_email_task.delay(emails=emails, subject=subject, message=message)

        return Response({"detail": "Account has been verified"}, status=200)

    @action(detail=False, methods=['post'], url_path="verify-email", name='verify-email')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='Verification code'),
            },
            required=['code']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Verification code has been verified",
                examples={
                    "application/json": {
                        "id": "string",
                        "first_name": "string",
                        "last_name": "string",
                        "phone_number": "string",
                        "email": "string",
                        "is_email_verified": "boolean",
                        "nationality": "string",
                        "is_active": "boolean",
                        "is_staff": "boolean",
                        "birthdate": "string",
                        "marital_status": "string",
                        "gender": "string",
                        "verification_status": "string",
                        "profile_photo": "boolean",
                        "age": "number"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid verification code"
                    },
                }
            ),
        })
    def verify_email(self, request):

        """
        Verify email address
        """

        code = request.data.get("code")

        verification = Verification.objects.filter(code=code, is_valid=True, is_used=False, user=request.user,
                                                   channel="EMAIL").first()

        if not verification:
            return Response({"detail": "Invalid verification code"}, status=400)

        if request.user.is_email_verified:
            return Response({"detail": "Email is already verified"}, status=400)

        user = request.user
        user.is_email_verified = True
        user.save()

        context = {
            "request": request
        }

        data = UserMiniSerializer(user, context=context).data

        verification.is_valid = False
        verification.is_used = True
        verification.save()
        return Response(data, status=200)


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
        """
        Request an OTP code for various uses
        """
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

        message = "{code} is your UAMS verification code. It expires in 5 minutes.".format(code=verification.code)

        if is_username_phone_number(username):
            verification.channel = "PHONE_NUMBER"
            verification.save()
            send_sms_task.delay(phone_numbers=[username], message=message)
        if is_username_email(username):
            verification.channel = "EMAIL"
            verification.save()
            subject = "UAMS Authentication"
            email_message = "<p><b>{code}</b> is your UAMS verification code. It expires in 5 minutes.</p>".format(
                code=verification.code)
            send_email_task.delay(emails=[username], subject=subject, message=email_message)

        schedule_expiration.delay(verification_code=verification.code)

        return Response(
            {"detail": "Verification code has been sent to {username}.".format(username=username)},
            status=200)

    @action(detail=False, methods=['post'], url_path="verify-otp", name='verify-otp')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Email or phone number'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='Verification code'),
            },
            required=['username', 'code']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Verification code has been verified",
                examples={
                    "application/json": {
                        "id": "string",
                        "first_name": "string",
                        "last_name": "string",
                        "phone_number": "string",
                        "email": "string",
                        "is_email_verified": "boolean",
                        "nationality": "string",
                        "is_active": "boolean",
                        "is_staff": "boolean",
                        "birthdate": "string",
                        "marital_status": "string",
                        "gender": "string",
                        "verification_status": "string",
                        "profile_photo": "boolean",
                        "age": "number",
                        "token": "string"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid verification code"
                    },
                }
            ),
        })
    def verify_otp(self, request):

        """
        Login with username, password and OTP code
        """
        code = request.data.get("code")
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

        user = User.objects.filter(**filter_params).first()

        if not user:
            return Response({"detail": "No account found"}, status=400)
        if not user.is_active:
            return Response({"detail": "The account is not active"}, status=400)

        verification = Verification.objects.filter(code=code, is_valid=True, is_used=False, user=user).first()

        if not verification:
            return Response({"detail": "Invalid verification code"}, status=400)

        verification.is_used = True
        verification.save()

        return Response({"detail": "OTP verified"}, status=200)

    @action(detail=False, methods=['post'], url_path="authenticate", name='authenticate')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Email or phone number'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='Verification code'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            },
            required=['username', 'code', 'password']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Verification code has been verified",
                examples={
                    "application/json": {
                        "id": "string",
                        "first_name": "string",
                        "last_name": "string",
                        "phone_number": "string",
                        "email": "string",
                        "is_email_verified": "boolean",
                        "nationality": "string",
                        "is_active": "boolean",
                        "is_staff": "boolean",
                        "birthdate": "string",
                        "marital_status": "string",
                        "gender": "string",
                        "verification_status": "string",
                        "profile_photo": "boolean",
                        "age": "number",
                        "token": "string"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid verification code"
                    },
                }
            ),
        })
    def perform__authentication(self, request):

        """
        Login with username, password and OTP code
        """
        code = request.data.get("code")
        username = request.data.get("username")
        password = request.data.get("password")

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

        user = User.objects.filter(**filter_params).first()

        if not user:
            return Response({"detail": "No account found"}, status=400)
        if not user.is_active:
            return Response({"detail": "The account is not active"}, status=400)

        user = authenticate(username=username, password=password, request=request)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        verification = Verification.objects.filter(code=code, is_valid=True, is_used=True, user=user).first()

        if not verification:
            return Response({"detail": "Invalid verification code"}, status=400)

        context = {
            "request": request
        }

        data = UserMiniSerializer(user, context=context).data

        token, _ = Token.objects.get_or_create(
            user=user
        )
        data["token"] = token.key

        verification.is_valid = False
        verification.is_used = True
        verification.save()
        return Response(data, status=200)

    @action(detail=False, methods=['post'], url_path="verify-change-password", name='verify-change-password')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Email or phone number'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='Verification code'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            },
            required=['username', 'code', 'password']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Verification code has been verified",
                examples={
                    "application/json": {
                        "detail": "Verification is approved. Please continue login"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid verification code"
                    },
                }
            ),
        })
    def verify_change_password(self, request):

        """
        Change password with OTP
        """

        code = request.data.get("code")
        username = request.data.get("username")
        password = request.data.get("password")

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

        user = User.objects.filter(**filter_params).first()

        if not user:
            return Response({"detail": "No account found"}, status=400)
        if not user.is_active:
            return Response({"detail": "The account is not active"}, status=400)

        if not password:
            return Response({"detail": "Password not provided"}, status=400)

        verification = Verification.objects.filter(code=code, is_valid=True, is_used=False, user=user).first()

        if not verification:
            return Response({"detail": "Invalid verification code"}, status=400)

        """
        Validate password
        """

        try:
            validate_password(password=password, user=user)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)

        user.set_password(password)
        user.save()

        verification.is_valid = False
        verification.is_used = True
        verification.save()

        password_changed(password, user)
        Token.objects.filter(user=user).delete()

        return Response({"detail": "Password has been changed successfully"}, status=200)

    @action(detail=False, methods=['post'], url_path="generate-magic-link", name='generate-magic-link')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
            },
            required=['email']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Login link generated successfully",
                examples={
                    "application/json": {
                        "detail": "Login link has been sent to the email address"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid email code"
                    },
                }
            ),
        })
    def generate_magic_link(self, request):
        """
        Generates login link and send it to verified email
        """

        email = request.data.get("email")

        if not email or not is_username_email(email):
            return Response({"detail": "Invalid email address"}, status=400)

        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"detail": "Account with the email is not found"}, status=400)

        if not user.is_active:
            return Response(
                {"detail": "The account with the email address is not active. Activate your account to continue"},
                status=400)

        if not user.is_email_verified:
            return Response(
                {"detail": "The email address is not verified. Use other login methods and verify your account first"},
                status=400)

        verification = Verification(user=user, is_valid=True, is_used=False)
        verification.save()

        """
        Send login link
        
        """

        link = f"http://localhost:4200/login-with-link/{verification.id}"

        subject = "UAMS Authentication"
        message = f"<p>Please click this link to login: <a href=\"{link}\">{link}</a></p>"
        emails = [email]

        send_email_task.delay(emails=emails, subject=subject, message=message)

        return Response({"detail": "Login link has been sent to the email address"}, status=200)

    @action(detail=False, methods=['get'], url_path="login-with-magic-link", name='login-with-magic-link')
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Login is successful",
                examples={
                    "application/json": {
                        "id": "string",
                        "first_name": "string",
                        "last_name": "string",
                        "phone_number": "string",
                        "email": "string",
                        "is_email_verified": "boolean",
                        "nationality": "string",
                        "is_active": "boolean",
                        "is_staff": "boolean",
                        "birthdate": "string",
                        "marital_status": "string",
                        "gender": "string",
                        "verification_status": "string",
                        "profile_photo": "boolean",
                        "age": "number"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Account/verification code exception",
                examples={
                    "application/json": {
                        "detail": "No account found | The account is not active | This account must reset password "
                                  "before login | Invalid email code"
                    },
                }
            ),
        })
    def signin_with_magic_link(self, request):
        """
        Authenticate with login link
        """
        verification_id = request.query_params.get("login_id")
        verification = Verification.objects.filter(id=verification_id, is_used=False, is_valid=True).first()

        if not verification:
            return Response({"detail": "The login link is invalid"}, status=400)

        user = verification.user

        if not user.is_active:
            return Response({"detail": "The account is not active. Please activate your account and try again"},
                            status=400)

        token, _ = Token.objects.get_or_create(user=user)

        context = {
            "request": request
        }
        data = UserMiniSerializer(instance=user, context=context).data
        data['token'] = token.key

        verification.is_valid = False
        verification.is_used = True
        verification.save()

        return Response(data, status=200)

    @action(detail=False, methods=['get'], url_path="logout", name='logout')
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Successfully signed out",
                examples={
                    "application/json": {
                        "detail": "Signed out"
                    }
                }
            )
        })
    def signout(self, request):
        if request.user.is_anonymous:
            return Response({"detail": "You are not allowed to perform this operation"}, status=401)
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({"detail": "Signed out"}, status=200)
