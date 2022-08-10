"""
Backend that allows authentication using phone_number and phone_number
"""
from django.contrib.auth.backends import ModelBackend

from users.models import User, Verification


class PasswordlessAuthBackend(ModelBackend):
    """Log in without providing a password.

    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        code = kwargs.get("verification_code")
        vc = Verification.objects.filter(code=code, is_used=False, is_valid=True, user__username=username).first()

        try:
            user = User.objects.get(username=username, is_active=True)

            if user and vc:
                vc.is_used = True
                vc.is_valid = False
                vc.save()
                return user
            return None
        except:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class Backend(ModelBackend):

    def authenticate(self, request=None, **kwargs):
        """
        Returns a user with the given credentials
        :param request: Request object passed to the backend
        :param kwargs: Contains credentials to find user
        :return: User if credentials are found
        """
        username = kwargs.get('username')  # Contains phone_number or email
        password = kwargs.get('password')

        # Trying phone_number
        user = User.objects.filter(phone_number=username).first()

        # Trying email
        if not user:
            user = User.objects.filter(email=username).first()

        # Trying username
        if not user:
            user = User.objects.filter(username=username).first()

        if user:
            if user.check_password(password) and user.is_active:
                return user

        return None

    def get_user(self, user_id):
        """
        Returns instance of the user, when given the user_id
        :param uuid user_id: User id, the current primary key
        :return: User if found and None otherwise
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
