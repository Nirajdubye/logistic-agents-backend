from langchain.tools import tool
from app.services.email_service import EmailService


@tool
def send_email_notification(
    recipient_email: str,
    subject: str,
    body: str
):
    """
    Send an email notification to a customer, driver, or management recipient.

    PURPOSE:
    Use this tool whenever the user requests sending an email summary, receipt,
    invoice notification, or status update to a specified email address.

    IMPORTANT:
    - Always confirm recipient email, subject, and content before calling.
    - Parameters:
      - recipient_email (str): Destination email address.
      - subject (str): Subject line of the email.
      - body (str): Body content of the email (HTML supported).
    """
    service = EmailService()
    return service.send_email(
        recipient_email=recipient_email,
        subject=subject,
        body=body
    )