import smtplib
import ssl

import pytest

from app import email_sender
from app.errors import ApiError


class FakeSMTP:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.tls_context = None
        self.credentials = None
        self.message = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def starttls(self, context):
        self.tls_context = context

    def login(self, username, password):
        self.credentials = (username, password)

    def send_message(self, message):
        self.message = message


@pytest.fixture()
def smtp_settings(monkeypatch):
    monkeypatch.setattr(email_sender.settings, "email_smtp_host", "smtp.server.example")
    monkeypatch.setattr(email_sender.settings, "email_smtp_port", 587)
    monkeypatch.setattr(email_sender.settings, "email_smtp_starttls", True)
    monkeypatch.setattr(email_sender.settings, "email_smtp_ssl", False)
    monkeypatch.setattr(email_sender.settings, "email_smtp_username", "smtp-user")
    monkeypatch.setattr(email_sender.settings, "email_smtp_password", "smtp-password")
    monkeypatch.setattr(email_sender.settings, "email_from_address", "sender@example.test")


def test_smtp_sender_uses_configured_provider_starttls_and_authentication(monkeypatch, smtp_settings):
    servers = []

    def smtp(*args, **kwargs):
        server = FakeSMTP(*args, **kwargs)
        servers.append(server)
        return server

    monkeypatch.setattr(email_sender.smtplib, "SMTP", smtp)

    email_sender.SmtpEmailSender().send("person@example.test", "Code", "Your code is 123456")

    server = servers[0]
    assert server.args == ("smtp.server.example", 587)
    assert server.kwargs["timeout"] == 15
    assert isinstance(server.tls_context, ssl.SSLContext)
    assert server.credentials == ("smtp-user", "smtp-password")
    assert server.message["To"] == "person@example.test"
    assert "123456" in server.message.get_content()


def test_smtp_sender_uses_authenticated_address_when_from_address_is_empty(monkeypatch, smtp_settings):
    servers = []
    monkeypatch.setattr(email_sender.settings, "email_from_address", "")
    monkeypatch.setattr(
        email_sender.smtplib,
        "SMTP",
        lambda *args, **kwargs: servers.append(FakeSMTP(*args, **kwargs)) or servers[-1],
    )

    email_sender.SmtpEmailSender().send("person@example.test", "Code", "body")

    assert servers[0].message["From"] == "smtp-user"


def test_smtp_sender_reports_missing_credentials(monkeypatch):
    monkeypatch.setattr(email_sender.settings, "email_smtp_host", "smtp.server.example")
    monkeypatch.setattr(email_sender.settings, "email_from_address", "sender@example.test")
    monkeypatch.setattr(email_sender.settings, "email_smtp_username", "")
    monkeypatch.setattr(email_sender.settings, "email_smtp_password", "")

    with pytest.raises(ApiError) as error:
        email_sender.SmtpEmailSender().send("person@example.test", "Code", "body")

    assert error.value.code == "EMAIL_DELIVERY_UNAVAILABLE"
    assert "EMAIL_SMTP_USERNAME" in error.value.message
    assert "Gmail" not in error.value.message


def test_smtp_sender_supports_implicit_tls(monkeypatch, smtp_settings):
    servers = []
    monkeypatch.setattr(email_sender.settings, "email_smtp_starttls", False)
    monkeypatch.setattr(email_sender.settings, "email_smtp_ssl", True)
    monkeypatch.setattr(
        email_sender.smtplib,
        "SMTP_SSL",
        lambda *args, **kwargs: servers.append(FakeSMTP(*args, **kwargs)) or servers[-1],
    )

    email_sender.SmtpEmailSender().send("person@example.test", "Code", "body")

    assert servers[0].args == ("smtp.server.example", 587)
    assert isinstance(servers[0].kwargs["context"], ssl.SSLContext)
    assert servers[0].tls_context is None


@pytest.mark.parametrize(
    ("failure", "expected_code", "message_fragment"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), "EMAIL_SMTP_AUTH_FAILED", "provider rejected"),
        (smtplib.SMTPConnectError(421, b"connection refused"), "EMAIL_SMTP_CONNECTION_FAILED", "connect"),
        (smtplib.SMTPRecipientsRefused({"person@example.test": (550, b"invalid recipient")}), "EMAIL_DELIVERY_FAILED", "recipient"),
    ],
)
def test_smtp_sender_maps_provider_failures(monkeypatch, smtp_settings, failure, expected_code, message_fragment):
    class FailedSMTP(FakeSMTP):
        def __enter__(self):
            raise failure

    monkeypatch.setattr(email_sender.smtplib, "SMTP", FailedSMTP)

    with pytest.raises(ApiError) as error:
        email_sender.SmtpEmailSender().send("person@example.test", "Code", "body")

    assert error.value.code == expected_code
    assert message_fragment.lower() in error.value.message.lower()
