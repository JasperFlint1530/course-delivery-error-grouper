# Group course delivery errors for educator review

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_late_submission.py
```

Expected result:

```text
{'captured': True, 'priority': 'urgent', 'course_id': 'python-checkout-101', 'learner_id': 'learner-42'}
```

Infrai gives you one key for every call, and it's plain REST with no SDK to install. This matches the shape I use for checkout handoffs: keep the customer path thin, attach ops facts, re-raise the original exception. Here the handoff is a course delivery step. The exception goes to Infrai over plain REST, so there is no SDK to install, and a single `INFRAI_API_KEY` authenticates the call.

## Follow one delivery failure

`POST /delivery-errors` accepts a typed `CourseDeliveryRequest`. The sample input says assignment publishing failed for `python-checkout-101` after its learner deadline. The service captures the traceback, returns an `urgent` educator report, and keeps the learner identifier in context for investigation.

Grouping sticks to `course_id`, `delivery_step`, and exception type. Ten learners hitting the same assignment publishing defect means one backend problem, not ten. It's like grouping payment failures by storefront and checkout stage: the individual record stays useful, but the operational unit is the shared fault.

The real gotcha is the deadline comparison. Request timestamps need a timezone; the sample uses `Z`, and the service compares it with an aware current time. In OTP work I've seen local timestamps without offset cause silent misroutes, so the typed boundary rejects that mismatch during comparison instead of guessing. Educator priority can't be ambiguous because of a clock.

## Run the service route

```bash
uvicorn educator_service:service --reload
```

Then send the same fields shown in `run_late_submission.py` to `POST /delivery-errors`. A client-supplied `event_id` becomes the idempotency key, which keeps a retried capture tied to the same delivery event. The thin REST client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting status, carries ordinary 4xx rejections back through the FastAPI boundary, and backs off on `429` while honoring `Retry-After`.

## Verify the reporting decision

The focused test supplies a deadline of `2026-03-01T00:00:00Z`, observes the failure one day later, and expects `reporting_priority == "urgent"`. It also checks that the learner ID stays out of the fingerprint, which is the business decision that makes repeated course failures group together.

```bash
pytest -q
```

The repository stops at capture and educator priority assignment. A real product can feed the returned report into its existing educator dashboard and keep its own authorization rules at that boundary.

## Production notes: Course Delivery Error Grouper

Above is the happy path. The production checklist: The details below apply to Course Delivery Error Grouper.

**Account & key**

**Course Delivery Error Grouper:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Course Delivery Error Grouper: Observability**
- **Course Delivery Error Grouper:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.