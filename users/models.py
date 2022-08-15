from django.db import models
from django.contrib.auth.models import AbstractUser, Group
import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from users.manager import UserManager
from .utils import generate_code, generate_digits_code


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    phone_number = PhoneNumberField(unique=True)
    username = models.CharField(null=True, blank=True, max_length=30, editable=False)
    email = models.EmailField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    nationality = CountryField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    marital_statuses = [
        ('SINGLE', 'SINGLE'),
        ('MARRIED', 'MARRIED'),
        ('DIVORCED', 'DIVORCED'),
        ('WIDOWED', 'WIDOWED')
    ]
    marital_status = models.CharField(max_length=30, choices=marital_statuses, null=True, blank=True)

    genders = [
        ('MALE', 'MALE'),
        ('FEMALE', 'FEMALE'),
    ]
    gender = models.CharField(max_length=30, choices=genders, null=True, blank=True)
    profile_photo = models.ImageField(upload_to="profile-photos", null=True, blank=True)

    verification_statuses = [
        ('UNVERIFIED', 'UNVERIFIED'),
        ('PENDING VERIFICATION', 'PENDING VERIFICATION'),
        ('VERIFIED', 'VERIFIED')
    ]
    verification_status = models.CharField(max_length=30, choices=verification_statuses, default="UNVERIFIED")
    nid_number = models.CharField(max_length=30, null=True, blank=True)
    nid_document = models.ImageField(upload_to="nid_documents", null=True, blank=True)

    USERNAME_FIELD = 'phone_number'

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.phone_number


class Verification(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    code = models.CharField(max_length=6, default=generate_digits_code, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_valid = models.BooleanField(default=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.user.phone_number}"


@receiver(post_save, sender=Verification)
def post_save_verification(sender, instance=None, created=False, **kwargs):
    from users.tasks.tasks_verification import schedule_expiration
    if created and instance:
        schedule_expiration.delay(str(instance.id))
