from django.core.exceptions import ObjectDoesNotExist
import random
import string

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import (
    UserAttributeSimilarityValidator,
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
)


def is_username_email(username):
    """

    :param str username: Username to check if it's an email address
    :return: bool
    """
    if not username:
        return False

    return "@" and "." in username


def is_username_phone_number(username):
    """

    :param str username: Username to check if it's a phone number
    :return: bool
    """
    if not username:
        return False

    username = username.replace(" ", "")
    username = username.replace("(", "")
    username = username.replace(")", "")
    username = username.replace("-", "")

    for c in string.ascii_letters:
        if c in username:
            return False
    return username.startswith("+")


def validate_password(raw_password: str, request):
    password_validators = [
        UserAttributeSimilarityValidator,
        CommonPasswordValidator,
        MinimumLengthValidator,
        NumericPasswordValidator
    ]

    try:
        for validator in password_validators:
            validator().validate(raw_password)
        return True, 200
    except ValidationError as e:
        messages.error(request, str(e))
        return e, 400


def generate_code(digits=6):
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=digits))
    return key


def generate_digits_code(length=6):
    key = ''.join(random.choices(string.digits, k=length))
    return key


def get_object_or_none(model, kwargs):
    try:
        obj = model.objects.get(**kwargs)
        return obj
    except ObjectDoesNotExist:
        return None
