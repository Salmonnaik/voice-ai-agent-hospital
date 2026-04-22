"""
outbound/sip_client.py

SIP/telephony client wrapper supporting Twilio and Plivo.
"""
import logging
import os

logger = logging.getLogger(__name__)

SIP_PROVIDER = os.getenv("SIP_PROVIDER", "twilio")
SIP_ACCOUNT_SID = os.getenv("SIP_ACCOUNT_SID", "")
SIP_AUTH_TOKEN = os.getenv("SIP_AUTH_TOKEN", "")
SIP_FROM_NUMBER = os.getenv("SIP_FROM_NUMBER", "")

GATEWAY_WEBHOOK_URL = os.getenv(
    "GATEWAY_WEBHOOK_URL",
    "https://your-domain.com/webhooks/inbound-call"
)


class NoAnswer(Exception):
    pass


class Busy(Exception):
    pass


class SIPClient:
    def __init__(self):
        self._provider = SIP_PROVIDER
        self._client = self._init_client()

    def _init_client(self):
        if self._provider == "twilio":
            from twilio.rest import Client
            return Client(SIP_ACCOUNT_SID, SIP_AUTH_TOKEN)
        elif self._provider == "plivo":
            import plivo
            return plivo.RestClient(SIP_ACCOUNT_SID, SIP_AUTH_TOKEN)
        else:
            raise ValueError(f"Unknown SIP provider: {self._provider}")

    def dial(self, to: str, script_vars: dict, timeout_seconds: int = 30) -> str:
        """
        Initiate an outbound call. Returns call SID.
        Raises NoAnswer or Busy on failure.
        """
        lang = script_vars.get("lang", "en")
        twiml_url = f"{GATEWAY_WEBHOOK_URL}?lang={lang}&name={script_vars.get('name', '')}"

        if self._provider == "twilio":
            call = self._client.calls.create(
                to=to,
                from_=SIP_FROM_NUMBER,
                url=twiml_url,
                timeout=timeout_seconds,
                machine_detection="DetectMessageEnd",
                async_amd=True,
                async_amd_status_callback=f"{GATEWAY_WEBHOOK_URL}/amd-status",
            )
            if call.status in ("no-answer", "failed"):
                raise NoAnswer(f"Call {call.sid} ended with status: {call.status}")
            if call.status == "busy":
                raise Busy(f"Call {call.sid} busy")
            return call.sid

        raise NotImplementedError(f"Provider {self._provider} dial not implemented")

    def send_sms(self, to: str, body: str) -> str:
        """Send SMS fallback."""
        if self._provider == "twilio":
            msg = self._client.messages.create(to=to, from_=SIP_FROM_NUMBER, body=body)
            return msg.sid
        raise NotImplementedError(f"Provider {self._provider} SMS not implemented")
