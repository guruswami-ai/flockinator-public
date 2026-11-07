# Meta contribution bundle 001: contributor review that changed the twin

One inspectable sequence, as requested by the 2026-11-07 public
reassessment (priority 3): input -> model -> checked change ->
measured outcome. Public-safe; no credentials, no private data.
Revised 2026-11-07 for
[issue #132](https://github.com/guruswami-ai/flockinator-public/issues/132)
(verifier path, commit labels, evidence boundaries); the
described sequence is unchanged.

## The sequence

1. **Input:** `tools/kulira-core/kulira_core/twin.py` as merged
   in PR #121 (host simulation twin v1), merge commit `af7c3ec`.
   Git blob `7baff126`, SHA-256
   `3589ab33cba2248f67f71ea8128de5d85f8c62c912c4be089a34fd2de35abfcf`.
   The same blob is on the PR #121 branch tip `714e87f` and at
   the merge. This identifies the file in Git history; it is not
   an independent record of the bytes the API request carried
   (see evidence boundaries).
2. **Model call:** `muse-spark-1.3-contributor` via the Meta
   Model API (`POST /v1/responses`), 2026-11-07, as recorded by
   the supervisor who made the call. The exact prompt and the
   fan-out script that issued the call are private and are not
   in this repository. Task paraphrase, not prompt text: the
   call supplied the module source and asked for severity-listed
   findings on determinism, spec compliance and parity.
3. **Response:** preserved verbatim at
   `docs/research/contributor-notes/twin-code-review.md`, added
   in commit `aba0f9a` (PR #122) and unchanged since (blob
   `ea50bb15`). SHA-256
   `af6d07cc82d8c54c6d747f94752cbf0dfd2687da461ea9f519da57eb7e54ada5`.
   Headline verdict: "not parity-safe as-is" - Python RNG cannot
   bit-match a C++ port, banker's rounding in quantization,
   raw-float threshold compares, and `parity()` reporting 1.0 on
   truncated journals.
4. **Independent check:** supervisor verified each critical
   finding against the code before acting (RNG/rounding/parity
   points confirmed; the device receives broadcast inputs, so
   host RNG generates the *input stream*, it is not a device
   RNG - that scoping is recorded in `twin.py` comments).
5. **Change:** PR #122 (merge `092a005`) - integer-quantized
   decisions (`signal_q >= 700`), half-up quantization, three
   independent RNG streams, length-mismatch parity failure,
   analytic `expected_distribution()`. Its `parity()` still
   scored agreement as `n - max(hash_mismatches,
   decision_mismatches)`, which overstates joint agreement when
   hash and decision errors fall on different rows, and it did
   not check tick/seed identity. The 2026-11-07 reassessment
   found both. PR #126 (merge `7ba834e`, commit `142b147`)
   replaced it with per-row joint agreement over identity, hash
   and decision, with a regression test
   (`test_parity_joint_agreement_and_identity`). That test
   exercises the identity check and the new result keys. A
   fixture with hash-only and decision-only errors on disjoint
   rows, which separates the two formulas (4 + 4 errors in 500
   rows: 0.992 under the old formula, 0.984 correct), is not in
   `test_twin.py` at the commits listed here; it was requested
   as follow-up in
   [issue #131](https://github.com/guruswami-ai/flockinator-public/issues/131).
6. **Measured outcome:** kulira-core suite (`pytest
   tools/kulira-core`) at each merge commit: PR #121 `af7c3ec`
   175 passed; PR #122 `092a005` 177; PR #123 `160a962` 183
   (adds the twin distribution sweep); PR #126 `7ba834e` 196;
   unchanged at `290c054`, the commit this revision was checked
   against. Each run also reports 1 skipped, an
   optional-dependency skip in `test_slate.py`. These are
   whole-suite counts pinned to those commits, not a measure of
   twin coverage and not a score; later merges change the twin
   and its tests, so counts on current main differ. Canary
   contract aligned in `docs/experiments/canary-contract-v1.md`
   (PR #126).

## Verifier commands

From a full (non-shallow) clone at main `290c054` or later:

```sh
sha256sum docs/research/contributor-notes/twin-code-review.md
# af6d07cc82d8c54c6d747f94752cbf0dfd2687da461ea9f519da57eb7e54ada5
git show af7c3ec:tools/kulira-core/kulira_core/twin.py | sha256sum
# 3589ab33cba2248f67f71ea8128de5d85f8c62c912c4be089a34fd2de35abfcf
git show af7c3ec^2:tools/kulira-core/kulira_core/twin.py | sha256sum
# same hash: af7c3ec^2 is the PR #121 branch tip 714e87f
git rev-parse af7c3ec:tools/kulira-core/kulira_core/twin.py
# 7baff126e6eafb502431d8a0915367ce1ba5b818
```

`shasum -a 256` gives the same digests where `sha256sum` is
absent. An earlier version of this note used `af7c3ec^` (the
first parent, pre-merge main `09d1cf5`), where the module does
not yet exist, so that command fails; use the merge commit or
the second parent as above. Suite counts: check out (or
`git archive`) each merge commit in step 6 and run from its root:

```sh
uv run --locked --project tools/kulira-core pytest tools/kulira-core
```

## Evidence boundaries

- Git establishes which file existed at the PR #121 merge. It is
  not an attestation of the bytes the API request carried; the
  two are linked only by the supervisor's record of the call.
- The model identifier and endpoint are as recorded by the
  supervisor at call time; nothing in the public tree
  independently attests them.
- The exact prompt and the fan-out script are not public. The
  step 2 task description is a paraphrase, not the prompt. No
  sanitized copy has been published.
- Raw API request/response envelopes (headers, request ids) were
  not archived at call time and have not been reconstructed; the
  response text survives verbatim, with the hash above.
- Process fix going forward: archive sanitized request/response
  metadata (model id, endpoint, timestamp, request id, input
  hash, prompt hash) at call time. Recorded here as a process
  fix, not backfilled.
