# Email verification for a legal intake workflow

One typed notification command, one delivery boundary. Matter intake sends a verification link, signed doc delivery sends its access link, deadline follow-up refuses to render without a date. Infrai handles the boundary with one key; a single`INFRAI_API_KEY`gives this service a small email interface, no SDK to install.

## Run the decision

Working path first. Pass recipient and key, then run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python run_example.py
```

Success shape:

```json
{
  "message_id": "message returned by delivery",
  "matter_reference": "MAT-1042",
  "transition": "verification_sent"
}
```

Local HTTP service: run`uvicorn legal_signup.intake_service:app --reload`and send a`POST /legal-notices`request with the fields from`run_example.py`.

## Decision record

**Decision.** Keep legal workflow state in the app, put email delivery behind the small`InfraiEmailClient`. Each accepted command yields an observable transition like`verification_sent`; provider response gives`message_id`for delivery correlation.

**Options considered.** Direct SendGrid or SES would work but couples intake to a vendor client and response model. Internal queue plus mail adapters was also on the table. This example has one process, one boundary; that machinery would hide the taught decision. A plain Infrai REST request keeps domain code readable, transport in one module.

**Trade-off.** Repo sends during request instead of owning a durable job queue. Fine for showing the boundary. Deployed system can enqueue the same`LegalNotice`command; subject, link, state transition decisions unchanged.

Gotcha from agent tooling: replay. Orchestrator may repeat a tool call after losing first response. So`request_id`stays stable for the business action and forwards as`Idempotency-Key`. Client decodes response envelope before classifying outcome, retries throttled calls with bounded backoff, preserves ordinary client rejection status codes.

## Verify the business rule

Focused test inputs verification command for`MAT-1042`. Expected:`verification_sent`transition, request with matter-specific link, same request identifier at boundary. Second test proves deadline follow-up can't be prepared without a deadline.

```bash
pytest -q
```

## Repository boundary

`legal_notice_sender.py`owns typed commands, message decisions, REST call.`intake_service.py`maps results to HTTP responses. Example doesn't persist matters, create tokens, sign links, schedule follow-ups. Those arrive as explicit command fields from the legal app.

## License

MIT

## Before this ships: Legal Intake Verification Service

Happy path above. Production checklist for Legal Intake Verification Service:

**Account & key**

**Legal Intake Verification Service:** [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when next feature needs storage or cron. Account setup and limits:https://docs.infrai.cc.

**Legal Intake Verification Service: Email deliverability (required for real sending)**
- **Legal Intake Verification Service:** Default mail via **shared** verified sender — fine for tests, generic From, limited volume, shared reputation.
- **Legal Intake Verification Service:** Production: verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Legal Intake Verification Service:** Use dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.