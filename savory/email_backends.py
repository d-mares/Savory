from django.core.mail.backends.base import BaseEmailBackend
from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential
import os
import logging

logger = logging.getLogger(__name__)

class AzureCommunicationEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.connection = None
        self.connection_string = os.getenv('AZURE_COMMUNICATION_CONNECTION_STRING')
        self.sender_address = os.getenv('AZURE_EMAIL_SENDER_ADDRESS')
        
        if not self.connection_string:
            logger.error("AZURE_COMMUNICATION_CONNECTION_STRING is not set")
        if not self.sender_address:
            logger.error("AZURE_EMAIL_SENDER_ADDRESS is not set")

    def open(self):
        if self.connection is None:
            try:
                self.connection = EmailClient.from_connection_string(self.connection_string)
                return True
            except Exception as e:
                logger.error(f"Failed to open connection: {str(e)}")
                if not self.fail_silently:
                    raise
                return False
        return False

    def close(self):
        self.connection = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        if not self.connection:
            self.open()
            if not self.connection:
                return 0

        num_sent = 0
        for message in email_messages:
            try:
                email_content = {
                    "subject": message.subject,
                    "plainText": message.body,
                    "html": message.alternatives[0][0] if message.alternatives else None
                }

                recipients = {
                    "to": [{"address": addr} for addr in message.to],
                    "cc": [{"address": addr} for addr in message.cc] if message.cc else None,
                    "bcc": [{"address": addr} for addr in message.bcc] if message.bcc else None
                }

                email_message = {
                    "content": email_content,
                    "recipients": recipients,
                    "senderAddress": self.sender_address
                }

                logger.info(f"Attempting to send email from {self.sender_address} to {message.to}")
                poller = self.connection.begin_send(email_message)
                result = poller.result()
                if result:
                    num_sent += 1
                    logger.info(f"Successfully sent email to {message.to}")
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                if not self.fail_silently:
                    raise
        return num_sent 