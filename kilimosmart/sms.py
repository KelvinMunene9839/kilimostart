"""Simulates outbound SMS delivery.

A real deployment would call an SMS gateway (e.g. Africa's Talking) here;
for the prototype we print what would have been sent so the USSD/SMS
story is visible end-to-end without needing telecom credentials.
"""


class SMSSimulator:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, phone: str, message: str) -> None:
        self.sent.append((phone, message))
        print(f"[SMS -> {phone}] {message}")
