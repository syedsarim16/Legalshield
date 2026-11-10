import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import settings
from .errors import ApiError

log = logging.getLogger("legalshield.email")


class SmtpEmailSender:
    def send(self, recipient: str, subject: str, body: str) -> None:
        if not settings.email_smtp_username or not settings.email_smtp_password:
            raise ApiError(
                503,
                "EMAIL_DELIVERY_UNAVAILABLE",
                "SMTP credentials are missing. Set EMAIL_SMTP_USERNAME and EMAIL_SMTP_PASSWORD in the backend .env file.",
            )
        if not settings.email_smtp_host:
            raise ApiError(
                503,
                "EMAIL_DELIVERY_UNAVAILABLE",
                "SMTP host is missing. Set EMAIL_SMTP_HOST to your provider's SMTP server in the backend .env file.",
            )
        if settings.email_smtp_starttls and settings.email_smtp_ssl:
            raise ApiError(
                503,
                "EMAIL_DELIVERY_UNAVAILABLE",
                "SMTP transport is misconfigured. Enable either EMAIL_SMTP_STARTTLS or EMAIL_SMTP_SSL, not both.",
            )
        sender = settings.email_from_address or settings.email_smtp_username

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = recipient
        message.set_content(body)
        try:
            if settings.email_smtp_ssl:
                connection = smtplib.SMTP_SSL(
                    settings.email_smtp_host,
                    settings.email_smtp_port,
                    timeout=15,
                    context=ssl.create_default_context(),
                )
            else:
                connection = smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=15)
            with connection as server:
                if settings.email_smtp_starttls:
                    server.starttls(context=ssl.create_default_context())
                server.login(settings.email_smtp_username, settings.email_smtp_password)
                server.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            log.error("SMTP authentication failed (SMTP code %s).", exc.smtp_code)
            raise ApiError(
                503,
                "EMAIL_SMTP_AUTH_FAILED",
                "The SMTP provider rejected the credentials. Check EMAIL_SMTP_USERNAME and EMAIL_SMTP_PASSWORD in the backend .env file.",
            ) from exc
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as exc:
            log.error("SMTP rejected email delivery (%s).", type(exc).__name__)
            raise ApiError(
                503,
                "EMAIL_DELIVERY_FAILED",
                "The SMTP provider rejected this email. Check the configured sender address and recipient.",
            ) from exc
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError, ssl.SSLError) as exc:
            log.error("SMTP connection or TLS setup failed (%s).", type(exc).__name__)
            raise ApiError(
                503,
                "EMAIL_SMTP_CONNECTION_FAILED",
                "Could not connect securely to the configured SMTP server. Check the network, host, port, and TLS settings.",
            ) from exc
        except smtplib.SMTPException as exc:
            log.error("SMTP email delivery failed (%s).", type(exc).__name__)
            raise ApiError(
                503,
                "EMAIL_DELIVERY_FAILED",
                "The SMTP provider could not deliver this email. Check the SMTP configuration and try again.",
            ) from exc


def get_email_sender() -> SmtpEmailSender:
    return SmtpEmailSender()
