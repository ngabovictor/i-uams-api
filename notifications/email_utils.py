from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings

sg = SendGridAPIClient(settings.SENDGRID_API_KEY)


def send_email(emails, subject, message, from_email):
    """
    :param list[str] emails: list of email addresses
    :param str subject: Email subject
    :param str message: Email message to be sent to recipients
    :return: void
    """

    message = Mail(
        from_email=from_email,
        to_emails=emails,
        subject=subject,
        html_content=message
    )
    try:
        response = sg.send(message)
    except Exception as e:
        print(e)
