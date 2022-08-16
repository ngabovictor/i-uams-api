import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from users.models import User, Verification
from django.utils import timezone
from datetime import datetime


class TestAuthentication(TestCase):
    """
    Test authentication process
    Request verification code: User requests OTP code, when no user, one shall be created
    Login: Login with username and OTP code
    Invalidate OTP: After login, the verification code shall be invalid
    """

    def setUp(self):
        self.user = User(
            phone_number="+111111111111",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe"
        )
        self.user.set_password("Testing@2")
        self.user.save()

        self.verification = Verification(
            user=self.user
        )

        self.verification.save()

        self.client = APIClient()

    def test_request_verification_code(self):
        data = {
            "username": "+000000000000"
        }

        response = self.client.post('/auth/request-verification-code', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().keys()), 1)
        self.assertTrue("detail" in response.json())
        self.assertEqual(Verification.objects.filter(user__phone_number="+000000000000").count(), 1)
        self.assertEqual(User.objects.filter(phone_number="+000000000000").count(), 1)

    def test_login_with_otp(self):
        data = {
            "username": "+111111111111",
            "code": self.verification.code,
            "password": "Testing@2"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue("token" in response.json())
        self.assertEqual(response.json()['first_name'], "John")
        self.assertEqual(response.json()['last_name'], "Doe")
        self.assertEqual(response.json()['email'], "email@xyz.com")
        self.assertEqual(response.json()['phone_number'], "+111111111111")
        self.assertTrue(Verification.objects.get(code=self.verification.code).is_used)
        self.assertFalse(Verification.objects.get(code=self.verification.code).is_valid)

    def test_login_with_wrong_otp(self):
        data = {
            "username": "+111111111111",
            "code": "INVALID",
            "password": "Testing@2"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid verification code")

    def test_login_with_invalid_otp(self):
        self.verification.is_valid = False
        self.verification.save()

        data = {
            "username": "+111111111111",
            "code": self.verification.code,
            "password": "Testing@2"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid verification code")

    def test_login_with_wrong_password(self):
        data = {
            "username": "+111111111111",
            "code": self.verification.code,
            "password": "Wrong password"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid credentials")

    def test_login_with_used_otp(self):
        self.verification.is_used = True
        self.verification.save()

        data = {
            "username": "+111111111111",
            "code": self.verification.code,
            "password": "Testing@2"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid verification code")

    def test_login_with_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        data = {
            "username": "+111111111111",
            "code": self.verification.code,
            "password": "Testing@2"
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "The account is not active")

    def test_login_with_no_user(self):
        self.user.is_active = False
        self.user.save()

        data = {
            "username": "+333333333333",
            "code": self.verification.code
        }

        response = self.client.post("/auth/verify-authentication", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "No account found")

    def test_generate_login_link_with_unverified_email(self):
        data = {
            "email": self.user.email
        }
        response = self.client.post("/auth/generate-magic-link", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'],
                         "The email address is not verified. Use other login methods and verify your account first")

    def test_generate_login_link_with_invalid_email(self):
        data = {
            "email": "wrong"
        }
        response = self.client.post("/auth/generate-magic-link", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid email address")

    def test_generate_login_link_with_invalid_account(self):
        data = {
            "email": "wrong@account.com"
        }
        response = self.client.post("/auth/generate-magic-link", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Account with the email is not found")

    def test_generate_login_link(self):
        self.user.is_email_verified = True
        self.user.save()

        data = {
            "email": self.user.email
        }
        response = self.client.post("/auth/generate-magic-link", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['detail'], "Login link has been sent to the email address")

    def test_login_link(self):
        response = self.client.get(f"/auth/login-with-magic-link?login_id={self.verification.id}")

        verification = Verification.objects.get(id=self.verification.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue('token' in response.json())
        self.assertTrue(verification.is_used)
        self.assertFalse(verification.is_valid)

    def test_login_link_with_invalid_otp(self):
        self.verification.is_valid = False
        self.verification.save()

        response = self.client.get(f"/auth/login-with-magic-link?login_id={self.verification.id}")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "The login link is invalid")

    def test_login_link_with_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.get(f"/auth/login-with-magic-link?login_id={self.verification.id}")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'],
                         "The account is not active. Please activate your account and try again")

    def test_change_password(self):
        data = {
            "username": self.user.phone_number,
            "code": self.verification.code,
            "password": "Kigali@2022"
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['detail'], "Password has been changed successfully")

    def test_change_password_with_invalid_otp(self):
        self.verification.is_valid = False
        self.verification.save()
        data = {
            "username": self.user.phone_number,
            "code": self.verification.code,
            "password": "Kigali@2022"
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid verification code")

    def test_change_password_with_invalid_user(self):
        data = {
            "username": "wrong@user.com",
            "code": self.verification.code,
            "password": "Kigali@2022"
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "No account found")

    def test_change_password_with_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        data = {
            "username": self.user.phone_number,
            "code": self.verification.code,
            "password": "Kigali@2022"
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "The account is not active")

    def test_change_password_with_no_password(self):
        data = {
            "username": self.user.phone_number,
            "code": self.verification.code,
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Password not provided")

    def test_change_password_with_invalid_password(self):
        data = {
            "username": self.user.phone_number,
            "code": self.verification.code,
            "password": "test"
        }
        response = self.client.post("/auth/verify-change-password", data=data)

        self.assertEqual(response.status_code, 400)

    def test_logout(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        response = self.client.get("/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['detail'], "Signed out")

    def test_logout_with_anonymous_user(self):
        response = self.client.get("/auth/logout")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], "You are not allowed to perform this operation")


class TestVerifications(TestCase):
    """
    Test verifications:
    - User account verification
    - Email address verification
    """

    def setUp(self):
        self.user = User(
            phone_number="+111111111111",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe"
        )
        self.user.set_password("Testing@2")
        self.user.save()

        self.verification = Verification(
            user=self.user
        )

        self.verification.save()

        self.client = APIClient()

    def test_upload_verification_data(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        f = open("users/tests/test_image.png", "rb")
        image = SimpleUploadedFile(
            name="nid.jpg", content=f.read(), content_type="image/png"
        )

        data = {
            "nid_number": "999999999999999",
            "nid_document": image
        }

        response = self.client.post("/verifications/upload-verification-documents", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['detail'], "The verification in underway")

        user = User.objects.get(id=self.user.id)

        self.assertEqual(user.verification_status, "PENDING VERIFICATION")
        self.assertEqual(user.nid_number, "999999999999999")
        self.assertIsNotNone(user.nid_document)

    def test_upload_verification_data_for_verified_user(self):
        self.user.verification_status = "VERIFIED"
        self.user.save()
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        f = open("users/tests/test_image.png", "rb")
        image = SimpleUploadedFile(
            name="nid.jpg", content=f.read(), content_type="image/png"
        )

        data = {
            "nid_number": "999999999999999",
            "nid_document": image
        }

        response = self.client.post("/verifications/upload-verification-documents", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "The user account status is VERIFIED")

        self.user.verification_status = "PENDING VERIFICATION"
        self.user.save()

        response = self.client.post("/verifications/upload-verification-documents", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "The user account status is PENDING VERIFICATION")

    def test_upload_verification_data_with_invalid_data(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        f = open("users/tests/test_image.png", "rb")
        image = SimpleUploadedFile(
            name="nid.jpg", content=f.read(), content_type="image/png"
        )

        data = {
            "nid_number": "999999999999999",
        }

        response = self.client.post("/verifications/upload-verification-documents", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "National ID or National ID image is not provided")

        data = {
            "nid_document": image
        }

        response = self.client.post("/verifications/upload-verification-documents", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "National ID or National ID image is not provided")

    def test_verify_account(self):
        self.user.verification_status = "PENDING VERIFICATION"
        self.user.save()

        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=True
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(self.user.id),
            "verification_status": "VERIFIED"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['detail'], "Account has been verified")

        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.verification_status, "VERIFIED")

    def test_verify_account_verified_user(self):
        self.user.verification_status = "VERIFIED"
        self.user.save()

        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=True
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(self.user.id),
            "verification_status": "VERIFIED"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "User with VERIFIED cannot be verified")

    def test_verify_account_unverified_user(self):
        self.user.verification_status = "NOT VERIFIED"
        self.user.save()

        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=True
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(self.user.id),
            "verification_status": "VERIFIED"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "User with NOT VERIFIED cannot be verified")

    def test_verify_account_invalid_user(self):
        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=True
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(uuid.uuid4()),
            "verification_status": "VERIFIED"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Account with the id is not found")

    def test_verify_account_invalid_status(self):
        self.user.verification_status = "PENDING VERIFICATION"
        self.user.save()

        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=True
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(self.user.id),
            "verification_status": "PENDING VERIFICATION"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid status is provided")

    def test_verify_account_not_admin_user(self):
        self.user.verification_status = "PENDING VERIFICATION"
        self.user.save()

        admin_user = User(
            phone_number="+2222222222222",
            email="admin@xyz.com",
            first_name="Admin",
            last_name="User",
            is_staff=False
        )
        admin_user.set_password("Testing@2")
        admin_user.save()

        verification = Verification(user=admin_user)

        self.client.login(
            username="+2222222222222",
            code=verification.code,
            password="Testing@2")

        data = {
            "user": str(self.user.id),
            "verification_status": "PENDING VERIFICATION"
        }

        response = self.client.post("/verifications/verify-account", data=data)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail'], "You don't have permissions to perform this operation")

    def test_verify_email(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        self.verification.channel = "EMAIL"
        self.verification.save()

        data = {
            "code": self.verification.code
        }

        response = self.client.post("/verifications/verify-email", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_email_verified'])

    def test_verify_email_invalid_otp(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        self.verification.is_used = True
        self.verification.save()

        data = {
            "code": self.verification.code
        }

        response = self.client.post("/verifications/verify-email", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Invalid verification code")

    def test_verify_email_verified_user(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        self.verification.channel = "EMAIL"
        self.verification.save()

        self.user.is_email_verified = True
        self.user.save()

        data = {
            "code": self.verification.code
        }

        response = self.client.post("/verifications/verify-email", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], "Email is already verified")


class TestUsersList(TestCase):
    """
    Test users list viewset:
    - List as staff
    - List as regular user
    """

    def setUp(self):
        self.user1 = User(
            phone_number="+111111111111",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe",
            is_staff=True
        )
        self.user1.set_password("Testing@2")
        self.user1.save()

        self.user2 = User(
            phone_number="+2222222222222",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe"
        )
        self.user2.set_password("Testing@2")
        self.user2.save()

        self.verification = Verification(
            user=self.user1
        )

        self.verification2 = Verification(
            user=self.user2
        )

        self.verification2.save()

        self.client = APIClient()

    def test_list_users_as_admin(self):
        self.client.login(
            username="+111111111111",
            code=self.verification.code,
            password="Testing@2")

        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)

    def test_list_users(self):
        self.client.login(
            username="+2222222222222",
            code=self.verification2.code,
            password="Testing@2")

        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_list_users_unauthenticated(self):
        self.client.logout()

        response = self.client.get("/users")
        self.assertEqual(response.status_code, 403)


class TestUsersDetail(TestCase):
    """
    Test users detail viewset:
    - Retrieve
    - Update user
    """

    def setUp(self):
        self.user1 = User(
            phone_number="+111111111111",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe",
            is_staff=True
        )
        self.user1.set_password("Testing@2")
        self.user1.save()

        self.user2 = User(
            phone_number="+2222222222222",
            email="email@xyz.com",
            first_name="John",
            last_name="Doe"
        )
        self.user2.set_password("Testing@2")
        self.user2.save()

        self.verification = Verification(
            user=self.user1
        )

        self.verification2 = Verification(
            user=self.user2
        )

        self.verification2.save()

        self.client = APIClient()

    def test_get_user_self(self):
        self.client.login(
            username="+2222222222222",
            code=self.verification2.code,
            password="Testing@2")

        response = self.client.get(f"/users/{self.user2.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], str(self.user2.id))

    def test_get_user_unauthorized(self):
        self.client.login(
            username="+2222222222222",
            code=self.verification2.code,
            password="Testing@2")

        response = self.client.get(f"/users/{self.user1.id}")
        self.assertEqual(response.status_code, 404)

    def test_update_user(self):
        self.client.login(
            username="+2222222222222",
            code=self.verification2.code,
            password="Testing@2")

        f = open("users/tests/test_image.png", "rb")
        image = SimpleUploadedFile(
            name="nid.jpg", content=f.read(), content_type="image/png"
        )

        data = {
            "first_name": "updated",
            "last_name": "updated",
            "email": "updated@email.com",
            "marital_status": "SINGLE",
            "gender": "MALE",
            "profile_photo": image,
            "nid_number": "99999999999999",
            "nid_document": image,
            "nationality": "RW",
            "is_email_verified": True,
            "birthdate": datetime(2000, 1, 1).isoformat().split("T")[0]
        }

        response = self.client.patch(f"/users/{self.user2.id}", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], str(self.user2.id))
        self.assertEqual(response.json()['first_name'], "updated")
        self.assertEqual(response.json()['last_name'], "updated")
        self.assertEqual(response.json()['marital_status'], "SINGLE")
        self.assertEqual(response.json()['gender'], "MALE")
        self.assertIsNotNone(response.json()['profile_photo'])
        self.assertEqual(response.json()['nationality'], "Rwanda")
        self.assertFalse(response.json()['is_email_verified'])
        self.assertEqual(response.json()['email'], "updated@email.com")
        self.assertIn("2000-01-01", response.json()['birthdate'])
        self.assertIsNotNone(response.json()['age'])

        user = User.objects.get(id=self.user2.id)

        self.assertNotEqual(user.nid_number, "99999999999999")
