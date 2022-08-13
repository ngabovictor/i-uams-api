# -*- coding: utf-8 -*-
from django.conf import settings
import africastalking
from decouple import config


username = config("AFRICASTALKING_USERNAME")
api_key = config("AFRICASTALKING_APIKEY")

africastalking.initialize(username, api_key)
sms_backend = africastalking.SMS
