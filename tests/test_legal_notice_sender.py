import json

import pytest

from legal_signup.legal_notice_sender import InfraiEmailClient, LegalNotice, prepare_notice, send_legal_notice


def test_verification_command_sends_matter_link_and_exposes_transition():
    captured = {}

    def transport(request):
        captured["method"] = request.method
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data)
        return 200, {}, json.dumps({"ok": True, "data": {"message_id": "msg_1042"}, "error": None, "metadata": {}}).encode()

    notice = LegalNotice(
        request_id="matter-1042-verification-v1",
        kind="verify_email",
        recipient="jordan@example.com",
        client_name="Jordan Lee",
        matter_reference="MAT-1042",
        action_url="https://legal.example/verify/token-7",
    )
    result = send_legal_notice(notice, InfraiEmailClient("test-key", transport=transport))

    assert result.transition == "verification_sent"
    assert result.message_id == "msg_1042"
    assert captured["method"] == "POST"
    assert captured["body"]["to"] == "jordan@example.com"
    assert "MAT-1042" in captured["body"]["html"]
    assert "token-7" in captured["body"]["html"]
    assert captured["headers"]["Idempotency-key"] == "matter-1042-verification-v1"


def test_deadline_follow_up_requires_a_deadline():
    notice = LegalNotice(
        request_id="matter-1042-deadline-v1",
        kind="deadline_follow_up",
        recipient="jordan@example.com",
        client_name="Jordan Lee",
        matter_reference="MAT-1042",
        action_url="https://legal.example/matters/1042",
    )
    with pytest.raises(ValueError, match="deadline is required"):
        prepare_notice(notice)

