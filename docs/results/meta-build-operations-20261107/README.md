# Recorded Meta build operations — 2026-11-07

Four real calls to `muse-spark-1.3-contributor` assisted build planning and log
interpretation. A frontier coordinator checked the plans and executed fixed
commands against isolated public-source exports. All four calls returned HTTP
200 and provider status `completed`; their exact request/response envelopes,
available request IDs, timestamps and usage are retained. They used `xhigh`
reasoning with no automatic retries. The two planning calls ran in parallel.

This demonstrates an operational API workflow. It is **not** a controlled
comparison, evidence of improved model quality, hardware acceptance, on-node
inference or a scientific result. Frontier models performed the source reviews
and fixes. Meta did not author the authentication or build repairs in this run.
These artifacts were created on 2026-11-07; they do not establish what was in an
earlier competition submission or whether later changes are eligible.

## Inspect the sequence

| Call | Input and actual model output | Coordinator disposition |
|---|---|---|
| Panel build plan | [Request](panel-plan/request.json), [response](panel-plan/response.json), [receipt](panel-plan/receipt.json) | Accepted the sequential native/panel/journal build commands with isolated output paths. Rejected its claim that ordinary PlatformIO native tests include the separate response-authentication suite. |
| Controller build plan | [Request](controller-plan/request.json), [response](controller-plan/response.json), [receipt](controller-plan/receipt.json) | Ran the reviewed compile-only plan. Preserved the failure: a fresh checkout had no board defaults and selected ESP32 rather than S31. The plan also did not identify the omitted speech assets. Frontier fixes followed. |
| Panel log interpretation | [Request](panel-result/request.json), [response](panel-result/response.json), [receipt](panel-result/receipt.json) | Correctly acknowledged the test-suite mistake and withheld a Waveshare success claim absent from its excerpt. The full retained log establishes both builds succeeded. Its phrase “11 envs” means 11 suites within the single native environment. |
| Controller log interpretation | [Request](controller-result/request.json), [response](controller-result/response.json), [receipt](controller-result/receipt.json) | Correctly separated the initial failure from the corrected S31 compile and did not attribute frontier repairs to Meta. Independently checked against exits, logs and hashes. |

No model output was executed automatically. The output is advisory; the
coordinator's verified disposition is the result. Nothing was flashed, and no
live node credentials were used or initialized by these build operations.

## What actually passed

- At public source `aabd15feb8b03c6218d3b719ac88d8f02e4593e7`, ordinary
  PlatformIO native tests passed **44 checks across 11 suites**. Both
  `waveshare-s3` and `journal-trial` compiled successfully. See the
  [full panel log](logs/panel-build.log), [execution receipt](logs/panel-build-receipt.json)
  and [artifact hashes](logs/panel-artifacts.json).
- The separate real-Mbed-TLS response protocol and compiled production HTTP
  suites passed under ASan/UBSan on macOS: [log](logs/response-native-build.log).
  They comprise 1007 protocol checks and 83 production-path checks. These are
  synthetic transport tests, not full ESP HTTP-server or hardware emulation.
- The initial controller build failed before compilation:
  [log](logs/controller-build.log), [receipt](logs/controller-build-receipt.json).
  This failure remains in the record.
- At public source `dac313fe06d53c3a3c43e369d6d5b9c33d1a4bc9`, the corrected
  default S31 build completed **2269 build steps**, including link and partition
  checks: [full log](logs/controller-corrected-build.log),
  [exit](logs/controller-corrected-build.exit),
  [selected configuration](logs/controller-corrected-selected-config.txt),
  [toolchain](logs/controller-corrected-toolchain.txt),
  [artifact hashes](logs/controller-corrected-artifacts.sha256).
  It uses public board defaults and leaves optional embedded speech disabled.
  Follow-up `ffbb576` changes only the README copy recipe. The
  [frontier report](logs/controller-frontier-report.txt) details the exact scope.

Controller pins: ESP-IDF `9a97f6c54ec638111ce55cd36581b3c192f15207` and BSP
`bd4d4ac18657e73583af3d7c0b0a23c3cddf3735`. Ninja was installed in an isolated
uv environment; the existing toolchains and private checkout were preserved.
The no-speech public build was compiled; optional actual voice-asset compilation
and playback were not tested. Build artifacts are identified, not distributed
here as hardware-approved installation packages.

## Provenance and limits

The [recorder](../../../tools/meta-build/README.md) retains one request per call.
`usage.json` totals **18,925 input tokens and 15,167 output tokens**, with zero
reported cached input tokens. Output includes provider-counted reasoning tokens.
This is reported usage, not an invoice or a time/cost benefit estimate.

Request/response JSON is retained byte-for-byte from the recorder, including
model mistakes. No credential reflection was detected. Build logs normalize
local source/operator paths and remove ANSI colour sequences. Execution receipts
retain hashes of the original logs and separately identify the published log
hashes; `SHA256SUMS` covers the actual published files. Other hashes in reports
may identify original source/configuration/build artifacts held outside this
bundle. No original private checkout, credentials, firmware binaries or licensed
voice/font assets are included.

From this directory, check published file integrity with:

```sh
sha256sum -c SHA256SUMS
# macOS: shasum -a 256 -c SHA256SUMS
```

Hashes establish consistency of these bytes, not independent provider or device
attestation. Request IDs and model fields are client-observed provider responses.
No held-out workflow baseline, blinded evaluator, latency comparison or physical
intervention consequence was measured. The prospective Meta-benefit work in the
[backlog](../../BACKLOG.md#measured-meta-contribution--135) remains outstanding.
