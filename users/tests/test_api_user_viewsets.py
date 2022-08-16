from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User, Verification


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
