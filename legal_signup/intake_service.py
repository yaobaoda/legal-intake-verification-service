from fastapi import FastAPI, HTTPException

from .legal_notice_sender import InfraiEmailClient, InfraiError, LegalNotice, DeliveryResult, send_legal_notice


app = FastAPI(title="Legal intake email service")


@app.post("/legal-notices", response_model=DeliveryResult)
def deliver_notice(notice: LegalNotice) -> DeliveryResult:
    try:
        return send_legal_notice(notice, InfraiEmailClient.from_environment())
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail={"code": exc.code}) from exc
    except (ConnectionError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="email delivery unavailable") from exc

