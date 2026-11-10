class TestCodeSender:
    """SMS-free sender used while verification codes are displayed in the test UI."""
    def send(self, phone: str, message: str) -> None:
        return None


def get_sms_sender() -> TestCodeSender:
    return TestCodeSender()
