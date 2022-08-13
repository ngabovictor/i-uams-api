from celeryconfig import app
from notifications.sms_utils import send_message

@app.task
def send_sms_task(phone_numbers, message):
    """
    :param list[str] phone_numbers: list of phone numbers to receive sms message. Country code must be included
    :param str message: SMS message to be sent to recipients
    """
    for phone_number in phone_numbers:
        send_message(phone_number=phone_number, message=message)