from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import os
import logging
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)

class SendGridEmailBackend(EmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.host = os.getenv('SENDGRID_SMTP_HOST', 'smtp.sendgrid.net')
        self.port = int(os.getenv('SENDGRID_SMTP_PORT', 587))
        self.username = os.getenv('SENDGRID_USERNAME', 'apikey')
        self.password = os.getenv('SENDGRID_API_KEY')
        self.use_tls = True
        self.from_email = os.getenv('DEFAULT_FROM_EMAIL')

        if not self.password:
            logger.error("SENDGRID_API_KEY is not set")
        if not self.from_email:
            logger.error("DEFAULT_FROM_EMAIL is not set")

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        encoding = email_message.encoding or settings.DEFAULT_CHARSET
        from_email = email_message.from_email or self.from_email
        recipients = email_message.recipients()
        
        try:
            self.connection.sendmail(from_email, recipients, email_message.message().as_bytes())
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            if not self.fail_silently:
                raise
            return False 