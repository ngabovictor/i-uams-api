import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User, Verification


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

