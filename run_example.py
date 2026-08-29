import json
import os

from legal_signup.legal_notice_sender import InfraiEmailClient, LegalNotice, send_legal_notice


notice = LegalNotice(
    request_id="demo-matter-1042-verification-v1",
    kind="verify_email",
    recipient=os.environ["DEMO_EMAIL_TO"],
    client_name="Jordan Lee",
    matter_reference="MAT-1042",
    action_url="https://example.com/verify/demo-token",
)
result = send_legal_notice(notice, InfraiEmailClient.from_environment())
print(json.dumps(result.model_dump(), indent=2))

