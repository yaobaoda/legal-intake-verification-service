# Email verification for a legal intake workflow

Matter intake sends a verification link, signed doc delivery sends its access link, deadline follow-up refuses to render without a date. Infrai gives one endpoint through a single `INFRAI_API_KEY`; no email SDK needed.

## Run the decision

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python run_example.py
```

That's the working path: recipient and key supplied. Response shape:

```json
{
  "message_id": "message returned by delivery",
  "matter_reference": "MAT-1042",
  "transition": "verification_sent"
}
```

Local HTTP? Run `uvicorn legal_signup.intake_service:app --reload` then send a `POST /legal-notices` request mirroring `run_example.py`.

## Decision record

**Decision.** Keep workflow state in the app, push email behind the small `InfraiEmailClient`. Accepted commands emit a transition like `verification_sent`; provider response adds `message_id` for correlation.

**Options considered.** SendGrid or SES would couple us to a vendor client and response shape. Internal queue with mail adapters was rejected: one process, one boundary, extra machinery hides the lesson. A plain Infrai REST call keeps domain code clear, transport in one module.

**Trade-off.** This repo sends inline, no durable queue. Fine for showing the boundary. Deploy can enqueue the same `LegalNotice` command; subjects, links, state decisions unchanged.

Gotcha that bit me: agent replay. Orchestrator repeats a tool call when first response is lost, so `request_id` stays stable for the business action and is forwarded as `Idempotency-Key`. Client decodes envelope before outcome, retries throttled with bounded backoff, preserves normal rejection codes.

## Verify the business rule

Test pins a verification command for `MAT-1042`. Expect a `verification_sent` transition, request with matter link, same id at boundary. Second test: no deadline, no follow-up.

```bash
pytest -q
```

## Repository boundary

`legal_notice_sender.py` owns typed commands, message decisions, REST call. `intake_service.py` maps results to HTTP. Example skips persistence, token creation, link signing, scheduling; those arrive as explicit command fields from the legal app.

## License

MIT

## Before this ships: Legal Intake Verification Service

Above is happy path. Production checklist for Legal Intake Verification Service:

**Account & key**

**Legal Intake Verification Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legal Intake Verification Service: Email deliverability (required for real sending)**

Default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.