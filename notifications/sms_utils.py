SENDER_ID = 'FydMee'
from .utils import sms_backend


def send_message(phone_number, message, sender=SENDER_ID):
    """
    :param str phone_number: Recipient phone number (should not start with a +)
    :param str message: SMS Message to be sent
    :param str sender: Custom SenderID/Name
    """

    sms_backend.send(message=message, recipients=[phone_number], sender_id=sender)
