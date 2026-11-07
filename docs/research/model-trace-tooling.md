# Single-attempt model trace tooling

Supports [#135](https://github.com/guruswami-ai/flockinator-public/issues/135).
This is software for collecting a future trace, **not a Meta invocation or a
measured contribution**. No network client, credential lookup, provider endpoint
or retry policy is supplied.

The bounded task is display-difference detection from the same reference and
observed 16-cell RGB grids available to a simple baseline. It is not an image
vision adapter or a test of mission truth. A task-specific fixed instruction,
neutral trial/case IDs, requested model and numeric parameters form the request.
This narrow input format avoids arbitrary prompt text, headers and private
annotations in the recorder. An actual image task needs a separately reviewed
media/input contract; do not claim that this RGB comparison evaluates vision.

## Callable contract

The implementation is [model_trace.py](../../tools/kulira-core/kulira_core/model_trace.py).
Use its Python interface around an existing provider adapter:

```python
from kulira_core.model_trace import fault_request, run_attempt

request = fault_request(
    trial_id="trial-001",
    requested_model="provider-model-name",
    parameters={"temperature": 0, "max_output_tokens": 128},
    case=public_case,  # case_id, reference_rgb, observed_rgb only
)
summary = run_attempt(
    fresh_attempt_directory, request, provider_adapter,
    evidence_kind="observed",
)
```

`provider_adapter(request_json_text)` receives an **immutable canonical JSON
string identical to the archived request bytes**. It may parse that string to
construct the provider's native request, keeping the instruction, case,
parameters and model selection unchanged. Credentials remain inside the
adapter's transport layer and must never be placed in this request. Unknown
fields reject before invocation. Supported parameters are `temperature` (0–2),
`top_p` (0–1), positive integer `max_output_tokens` and nonnegative integer `seed`;
omitted provider defaults remain unspecified. Provider-specific restrictions
are the adapter's responsibility.

Return exactly this structured shape, extracted from the actual response:

```json
{
  "status": "completed",
  "detected_nodes": ["A1"],
  "reported_model": null,
  "usage": null,
  "cost_usd": null,
  "cost_source": null,
  "error_code": null
}
```

`reported_model` is the provider-reported identifier, **not copied from the
requested model when absent**. Usage is null or an object with `input_tokens`
and `output_tokens`, each a nonnegative integer or null. Cost is null unless
known; when numeric, `cost_source` must be `provider_reported` or
`adapter_estimated`. An estimate must have its rate/method documented separately;
this tool invents no prices and does not turn unknown cost into zero.

For a failed call, return `status="error"`, empty `detected_nodes`, and one of
`provider_error`, `transport_error`, `timeout`, `invalid_response` or
`invoke_exception`. Preserve available usage/cost on failures too. Unknown fields,
invalid labels and contradictory metadata turn the attempt into
`invalid_response`; unsafe returned content is not archived. An exception from
the callable becomes `invoke_exception` with unknown metadata. Exception text,
raw HTTP headers, response envelopes and arbitrary model prose are never saved.
IDs/model labels must themselves be public identifiers: shape validation is
not a general secret detector or evidence that an input was reviewed.

## Recording and verification

The wrapper creates a new directory exclusively, then writes `request.json`
and `start.json` with exclusive creation and flushes them before invoking the
callable. `start.json` contains UTC time, input hash and declared `evidence_kind`
(`observed` or `synthetic_test`). `outcome.json` binds request/start hashes and
contains UTC finish time, monotonic elapsed seconds and the structured response.
Elapsed time covers the callable and response validation, not a provider's
reported server latency; wall-clock adjustments do not make it negative.

Existing attempt directories and concurrently created files are never
replaced. The wrapper performs no retries: one attempt means one callable
invocation, not proof of one provider request. Disable SDK/network automatic
retries inside the provider adapter, or expose each provider request as a
separate recorded attempt. Hidden retries can consume unreported time/tokens
and make a final-response cost underestimate the total; this wrapper cannot
observe or prevent them. A process interruption after the start
record leaves an `INCOMPLETE` attempt, not a successful or zero-cost call.
A torn/malformed record is a verification error. Keep these attempts in the
ledger; investigate before any retry, whose distinct attempt must remain visible.

```sh
uv run --project tools/kulira-core python -m kulira_core.model_trace /tmp/attempt-001
uv run --locked --project tools/kulira-core pytest -q tools/kulira-core/test_model_trace.py
```

The verifier checks field contracts, duplicate JSON keys, file types and hash
binding. It refuses extra files such as raw headers. Exit 0 means a structurally
valid completed attempt, 2 means a recorded error or incomplete attempt, and 3
means invalid/unreadable evidence. It prints the outcome hash for an external
manifest to pin before review. The hash identifies bytes; someone able to
rewrite all records can recompute hashes. This wrapper cannot independently
attest the provider, enforce that an adapter sent the supplied request, establish
protocol freeze time or prove benefit.

## Bind to the evaluation before claiming a result

Use the preassigned `trial_id` and map completed `detected_nodes` plus elapsed
time to the fault-evaluation response contract. Preserve error/timeout trials;
never choose the best retry after seeing labels. The trace directory is per
attempt, while the quality scorer expects one protocol-selected response per
trial. Predeclare that mapping and the retry budget, count cost across **all**
attempts, and keep unavailable costs visibly unknown. Do not drop incomplete
attempts from the collection ledger.

The adapter must parse provider output without leaking evaluator answers, use
identical allowed inputs for the comparator, and establish actual model/version
metadata. Tests use explicitly synthetic callables only. Real calls, protocol
review, held-out labels, a measured baseline comparison and independently checked
intervention consequences remain necessary to close #135.
