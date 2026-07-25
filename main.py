"""KilimoSmart CLI prototype.

Simulates dialing a USSD short code (e.g. *384*7#) from a feature phone.
Each screen is printed CON (session continues, expects more input) or END
(session terminates), mirroring how a real USSD gateway like Africa's
Talking or Safaricom would drive this same session logic over SMS/USSD.
"""

from kilimosmart.data_store import MockDataProvider
from kilimosmart.recommendation import RecommendationEngine
from kilimosmart.repository import FarmerRepository
from kilimosmart.session import USSDSession
from kilimosmart.sms import SMSSimulator

USSD_CODE = "*384*7#"


def run_session(phone: str, repo: FarmerRepository, data: MockDataProvider, engine: RecommendationEngine, sms: SMSSimulator) -> None:
    session = USSDSession(phone, repo, data, engine, sms)
    print(session.start())
    while not session.is_done():
        user_input = input("> ")
        print(session.handle(user_input))


def main() -> None:
    repo = FarmerRepository()
    data = MockDataProvider()
    engine = RecommendationEngine(data)
    sms = SMSSimulator()

    print("=" * 50)
    print(" KilimoSmart - USSD/SMS Prototype Simulator")
    print(f" Dial: {USSD_CODE}")
    print("=" * 50)

    while True:
        phone = input("\nEnter your phone number to dial in (or 'quit'): ").strip()
        if phone.lower() in ("quit", "exit"):
            print("Kwaheri!")
            break
        if not phone:
            continue
        run_session(phone, repo, data, engine, sms)


if __name__ == "__main__":
    main()
