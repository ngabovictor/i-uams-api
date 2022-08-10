from django.core.exceptions import ObjectDoesNotExist
import random
import string


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