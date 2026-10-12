"""A gateway failure is not proof that an external write was rejected."""


def classify_receipt(status_code, body):
    failure = isinstance(body, dict) and (body.get("success") is False or bool(body.get("error")))
    outcome = body.get("outcome") if isinstance(body, dict) else None
    if isinstance(body, dict) and isinstance(body.get("output"), dict):
        outcome = outcome or body["output"].get("outcome")
    uncertain = (isinstance(outcome, str) and outcome in {"unknown", "committed_unrecorded"}) or (
        isinstance(body, dict) and body.get("state") in ("unknown", "committed_unrecorded"))
    # The origin can commit before a proxy synthesizes this response.
    # An explicit application failure receipt supports a definitive failure.
    if (status_code == 408 or 500 <= status_code < 600) and not failure:
        uncertain = True
    return failure, uncertain
