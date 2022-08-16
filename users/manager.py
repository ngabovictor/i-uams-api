"""
Custom User Manager for Nexin projects
"""

from django.contrib.auth.models import UserManager as UManager


class UserManager(UManager):
    """
    Customises Django User Manager, by replacing the required username with phone,
    Creating users require the phone not username.
    """

    def _create_user(self, phone_number, email=None, password=None, **extra_fields):
        """
        Creates and saves a User with the given phone_number, email and password.
        """
        if not phone_number:
            raise ValueError('The given phone number must be set')

        if not phone_number.startswith("+"):
            raise ValueError('The given phone number must start with a country code')

        user = self.model(phone_number=phone_number, email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, email, password, **extra_fields)

    def create_superuser(self, phone_number, password, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone_number, email, password, **extra_fields)
