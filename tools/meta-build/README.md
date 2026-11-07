# Recorded Meta build assistance

`record_call.py` makes one bounded Meta Responses API call and records its exact
request, response, timing, usage, requested/reported model and available provider
request ID. It never executes model output or retries a failed request. It uses
the Python standard library and requires `MODEL_API_KEY` in its process
environment, supplied by your credential manager. Never put the key in a request
file, command argument or published evidence.

Prepare a public-safe JSON request with `model`, `input`, optional `instructions`
and `reasoning`, `max_output_tokens` (1–16384), and explicit `store: false`:

```sh
uv run --no-project python tools/meta-build/record_call.py \
  --request /path/to/request.json --out /path/to/new-call-directory
```

The output directory must not exist and its parent must already exist. Inspect
`receipt.json` and every response before acting. A completed call establishes
neither a correct plan nor a successful build. Review commands separately, run
them through a trusted executor and retain actual exit codes, logs and artifact
hashes. Failed calls remain evidence; start any intentional new attempt in a
different directory.

Credential checks inspect decoded JSON strings and object keys, including nested
fields. Safe response envelopes retain their exact bytes. A response reflecting
the credential is sanitized and recorded as a failure; its hash describes the
sanitized bytes. Malformed or duplicate-key responses are discarded with an
`invalid_response` receipt because they cannot be safely inspected.

This recorder is intended for small text tasks, with an 8 MiB request/response
bound and a 180-second socket timeout. It does not provide a total wall-clock
deadline, streaming, tool execution or persistent model sessions. Client hashes
check file consistency; they are not independent provider attestations. The
provider's retention/training policy remains applicable; `store: false` does not
override that policy. Use only public material with the contributor model.

Synthetic transport tests require no API credit:

```sh
uv run --no-project python -m unittest discover -s tools/meta-build -p 'test_*.py'
```
