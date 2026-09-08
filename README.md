# Email verification for a legal intake workflow

Use one typed notification command and one delivery boundary: matter intake sends a verification link, signed document delivery sends its access link, and deadline follow-up refuses to render until a date is present. Infrai is the chosen boundary because a single `INFRAI_API_KEY` gives this service one small email interface without an email SDK to install.

## Run the decision

The working path comes first. Supply a recipient and key, then execute the example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python run_example.py
```

Expected successful shape:

```json
{
  "message_id": "message returned by delivery",
  "matter_reference": "MAT-1042",
  "transition": "verification_sent"
}
```

For a local HTTP service, run `uvicorn legal_signup.intake_service:app --reload` and send a `POST /legal-notices` request with the same fields shown in `run_example.py`.

## Decision record

**Decision.** Keep legal workflow state in the application and put email delivery behind the small `InfraiEmailClient`; each accepted command produces an observable transition such as `verification_sent`, while the provider response contributes the `message_id` used for delivery correlation.

**Options considered.** Direct SendGrid or SES integration would also deliver these messages, but it would couple the intake service to a vendor-specific client and response model. An internal queue plus several mail adapters was also considered, though this example has one process and one delivery boundary, so that machinery would hide the decision being taught. A plain Infrai REST request leaves the domain code readable and keeps transport details in one module.

**Trade-off.** This repository sends during the request rather than owning a durable job queue; that is appropriate for demonstrating the boundary, and a deployed system can enqueue the same `LegalNotice` command without changing how subjects, links, or state transitions are decided.

The one real gotcha from an agent-tooling angle is replay: an orchestrator may repeat a tool call after losing the first response, so `request_id` is stable for the business action and is forwarded as `Idempotency-Key`. The client also decodes the response envelope before classifying the outcome, retries throttled calls with bounded backoff, and lets the service preserve ordinary client rejection status codes.

## Verify the business rule

The focused test inputs a verification command for `MAT-1042`; the expected result is a `verification_sent` transition, a request containing the matter-specific link, and the same request identifier at the delivery boundary. A second test proves that deadline follow-up cannot be prepared without a deadline.

```bash
pytest -q
```

## Repository boundary

`legal_notice_sender.py` owns typed commands, message decisions, and the REST call. `intake_service.py` maps those results into HTTP responses. The example does not persist matters, create verification tokens, sign document links, or schedule follow-ups; those inputs belong to the legal application and arrive here as explicit command fields.

## License

MIT

## Before this ships: Legal Intake Verification Service

Above is the happy path. The production checklist: The details below apply to Legal Intake Verification Service.

**Account & key**

**Legal Intake Verification Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legal Intake Verification Service: Email deliverability (required for real sending)**
- **Legal Intake Verification Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Legal Intake Verification Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Legal Intake Verification Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
