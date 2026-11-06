# Meta contribution bundle 001: contributor review that changed the twin

One inspectable sequence, as requested by the 2026-11-07 public
reassessment (priority 3): input -> model -> checked change ->
measured outcome. Public-safe; no credentials, no private data.

## The sequence

1. **Input:** `tools/kulira-core/kulira_core/twin.py` as merged
   in PR #121 (host simulation twin v1).
   Input SHA-256 (file as reviewed, reconstructed at bundle time
   from git history): see verifier note below.
2. **Model call:** `muse-spark-1.3-contributor` via the Meta
   Model API (`POST /v1/responses`), 2026-11-07. Task: review the
   module for determinism, spec compliance and parity bugs.
   Full prompt is preserved in the wave-5 fan-out script header
   (task `twin-code-review`); it supplied the module source and
   asked for severity-listed findings.
3. **Response:** preserved verbatim at
   `docs/research/contributor-notes/twin-code-review.md`
   (SHA-256 of that file at bundle time:
   `af6d07cc82d8c54c6d747f94752cbf0dfd2687da461ea9f519da57eb7e54ada5`).
   Headline verdict: "not parity-safe as-is" - Python RNG cannot
   bit-match a C++ port, banker's rounding in quantization,
   raw-float threshold compares, and `parity()` reporting 1.0 on
   truncated journals.
4. **Independent check:** supervisor verified each critical
   finding against the code before acting (RNG/rounding/parity
   points confirmed; the device receives broadcast inputs, so
   host RNG generates the *input stream*, it is not a device
   RNG - that scoping is recorded in `twin.py` comments).
5. **Change:** PR #122 - integer-quantized decisions
   (`signal_q >= 700`), half-up quantization, three independent
   RNG streams, joint-agreement parity with length-mismatch
   failure, analytic `expected_distribution()`. The 2026-11-07
   reassessment then found two residual parity issues (joint
   agreement overstated via max-of-mismatches; tick/seed not
   verified), fixed in the reassessment-response PR with
   regression tests.
6. **Measured outcome:** kulira-core suite 175 -> 177 -> 183
   passed across these changes; canary contract aligned in
   `docs/experiments/canary-contract-v1.md`.

## Verifier note

Check the response file hash:
`shasum -a 256 docs/research/contributor-notes/twin-code-review.md`
The reviewed twin source is recoverable from git:
`git show <PR-#121-merge>^:tools/kulira-core/kulira_core/twin.py`
(exact pre-review blob is in the PR #121 branch history).
Omissions, transparently: raw API request/response envelopes
(headers, request ids) were not archived at call time; the
prompt text survives in the fan-out script, the response text
survives verbatim. Future bundles should archive envelopes at
call time - recorded here as a process fix, not backfilled.
