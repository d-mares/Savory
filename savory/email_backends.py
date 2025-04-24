from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import os
import logging
from django.core.mail.message import sanitize_address
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.template.loader import render_to_string

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
        
        try:
            # Create a multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_message.subject
            msg['From'] = email_message.from_email or self.from_email
            msg['To'] = ', '.join(email_message.recipients())
            
            # Add text version
            if email_message.body:
                text_part = MIMEText(email_message.body, 'plain')
                msg.attach(text_part)
            
            # Add HTML version if available
            if hasattr(email_message, 'alternatives') and email_message.alternatives:
                for content, mimetype in email_message.alternatives:
                    if mimetype == 'text/html':
                        html_part = MIMEText(content, 'html')
                        msg.attach(html_part)
                        break
            
            # If no HTML content was found in alternatives, try to render the template
            if not any(mimetype == 'text/html' for _, mimetype in email_message.alternatives):
                # Get the template name from the email message
                template_name = getattr(email_message, 'template_name', None)
                if template_name:
                    # Render the template with the context
                    context = getattr(email_message, 'context', {})
                    html_content = render_to_string(template_name, context)
                    html_part = MIMEText(html_content, 'html')
                    msg.attach(html_part)
            
            # Send the email
            self.connection.sendmail(
                msg['From'],
                email_message.recipients(),
                msg.as_bytes()
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            if not self.fail_silently:
                raise
            return False 