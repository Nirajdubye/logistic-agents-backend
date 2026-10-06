import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


class EmailService:

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_email = os.getenv("SMTP_EMAIL", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        is_html: bool = True
    ):
        """
        Sends an email using configured SMTP settings.
        """
        try:
            if not self.smtp_email or not self.smtp_password:
                return {
                    "success": False,
                    "message": "SMTP credentials are not configured in environment."
                }

            message = MIMEMultipart()
            message["From"] = self.smtp_email
            message["To"] = recipient_email
            message["Subject"] = subject

            content_type = "html" if is_html else "plain"
            message.attach(MIMEText(body, content_type))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.sendmail(self.smtp_email, recipient_email, message.as_string())
            server.quit()

            return {
                "success": True,
                "message": f"Email sent successfully to {recipient_email}"
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
