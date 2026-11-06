# SAM 3.1 for the 16-panel LED wall — evaluation

Date: 2026-11-06. Sources: primary Meta sources only (Meta AI blog, dev.meta.ai docs, `facebookresearch/sam3`, `facebook/sam3`/`sam3.1` HF cards). Verdicts are this evaluation's assessment.

## What SAM 3.1 is

- SAM 3 is "a unified foundation model for promptable segmentation in
  images and videos. It can detect, segment, and track objects using
  text or visual prompts such as points, boxes, and masks"
  ([github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3/blob/main/README.md)).
- SAM 3.1 (2026-03-27) adds Object Multiplex: it "track[s] up to 16
  objects in a single forward pass", doubling throughput "from 16 to
  32 frames per second on a single H100 GPU"
  ([ai.meta.com/blog/segment-anything-model-3](https://ai.meta.com/blog/segment-anything-model-3/)).
- Architecture: detector + tracker sharing a vision encoder, 848M
  parameters; the detector is "conditioned on text, geometry, and
  image exemplars"
  ([github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3/blob/main/README.md)).

## Access routes

### Meta Model API (hosted)

- Model name `sam-3.1`, over `POST /v1/responses` on
  `https://api.meta.ai/v1` with Bearer auth; one model serves stills
  and clips ([dev.meta.ai/docs/sam/overview](https://dev.meta.ai/docs/sam/overview)).
- Pricing (pay-as-you-go, billed per image/frame, not per token):
  image segmentation "$2.50 per 1,000 images"; video segmentation
  "$0.20 per 1,000 frames"; every video request is billed for at
  least 50 frames ([dev.meta.ai/docs/pricing-rate-limits](https://dev.meta.ai/docs/pricing-rate-limits)).
- Rate limit for `sam-3.1`: 3,000 RPM per team, no TPM limit
  ([dev.meta.ai/docs/pricing-rate-limits](https://dev.meta.ai/docs/pricing-rate-limits)).
- Limits: MP4/MOV with H.264/H.265/MPEG-4 only; up to 15,000 frames
  (~10 min) per request; video tracks up to 16 objects per frame;
  object prompts name at most 16 objects
  ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).

### Open weights (self-hosted)

- Checkpoints: `facebook/sam3.1` (`sam3.1_multiplex.pt`, 3.5 GB) and
  `facebook/sam3`, both gated — you must request access and
  authenticate (`hf auth login`) before download
  ([huggingface.co/facebook/sam3.1](https://huggingface.co/facebook/sam3.1),
  [github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3/blob/main/README.md)).
- Licence: Meta's SAM License (custom, not Apache/MIT) — royalty-free
  use/redistribution under its terms, with trade-control restrictions
  (no military/nuclear/espionage/weapons use)
  ([github.com/facebookresearch/sam3 LICENSE](https://github.com/facebookresearch/sam3/blob/main/LICENSE)).
- Hardware/software floor: Python 3.12+, PyTorch 2.7+, a
  CUDA-compatible GPU with CUDA 12.6+
  ([github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3/blob/main/README.md)).
  No CPU/edge path is documented. The 3.1 repo "hosts only the SAM 3.1
  model checkpoints — there is no Hugging Face Transformers
  integration"; use the GitHub code
  ([huggingface.co/facebook/sam3.1](https://huggingface.co/facebook/sam3.1)).

## Prompts, video, outputs, latency

- Prompt types (API): (1) text concept — one short noun phrase per
  request ("yellow school bus"); lists, negation, OR and spatial
  phrasing ("person on the left") are unreliable or return zero
  matches; (2) object prompts — a box, positive/negative points, or a
  mask per object under a caller-chosen id; a phrase and object
  prompts cannot be combined in one request
  ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- Exemplar (image-example) prompts exist in the open-weights model —
  the detector is conditioned on "image exemplars" and Promptable
  Concept Segmentation takes "text and/or image exemplars"
  ([huggingface.co/facebook/sam3](https://huggingface.co/facebook/sam3)) —
  but no exemplar prompt type is documented for the Model API
  ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- Video tracking (API): object prompts on any frames, propagated
  `forward`, `backward` or `both` (`metadata.propagation_direction`,
  default `both`); repeat an id on a later frame to re-prompt the
  same object ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- Output format (API): special-token text, one line per frame —
  `<Nf>id<|box;x1..;y2..;w..;h..|><|mask;x=0;y=0;data=H,W,~...|>` —
  i.e. per object a box in source pixels plus a mask raster
  (`lossless` `~` default, compact `one_bit` `!` on request). Zero
  matches is a valid empty `output_text`
  ([dev.meta.ai/docs/sam/reading-segmentation](https://dev.meta.ai/docs/sam/reading-segmentation),
  [dev.meta.ai/docs/sam/overview](https://dev.meta.ai/docs/sam/overview)).
- Confidence is opt-in: `metadata.include_confidence="true"` adds a
  `c` field (0-1) to every box and mask, same value on both, varying
  per frame ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
  Open-weights code likewise returns `masks, boxes, scores`
  ([github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3/blob/main/README.md)).
- Identity: the leading integer is a stable object id across frames
  within a response, but "don't rely on the id across an object's
  entry, exit, or full occlusion, or over very long clips"; frames
  with no visible objects produce no line
  ([dev.meta.ai/docs/sam/reading-segmentation](https://dev.meta.ai/docs/sam/reading-segmentation)).
  Results "can vary slightly between runs of the same request"
  ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- Scope limit: "SAM 3.1 locates the objects you name; it doesn't
  answer questions or reason about a scene"
  ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- Latency claims: SAM 3 runs "in 30 milliseconds for a single image
  with more than 100 detected objects on an H200 GPU", with video
  "near real-time performance for approximately five concurrent
  objects"; SAM 3.1 reaches 32 fps on one H100 at medium object
  counts, and the open-weights release claims "~7x speedup at 128
  objects on a single H100" vs the SAM 3 release
  ([ai.meta.com/blog/segment-anything-model-3](https://ai.meta.com/blog/segment-anything-model-3/),
  [RELEASE_SAM3p1.md](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)).
  No latency figure is published for the hosted API.

## Verdicts vs a classical fixed-grid colour/template classifier

The wall is fixed: 16 panels in a 4x4 grid, fixed camera. One homography + 16 fixed ROIs, then per-cell colour/template/OCR on rectified crops, is deterministic, CPU-millisecond, and needs no GPU, licence gate, or per-call fee.

### (a) Segmenting the 16 panels — SAM: usable bootstrap, not the runtime answer

- Measured (2026-11-06, see Decisive comparison below): concept
  prompts do **not** discover the panels — "LED panel", "monitor"
  and "television" return zero objects; "screen", "display" and
  "LED screen" return one object, the whole wall as a single screen
  (confidence 0.85-0.95, best single-cell box IoU 0.067).
- But given the grid's 16 boxes as object prompts, SAM returns all
  16, mean box IoU 0.921 (min 0.868) against the calibrated cells.
  That confirms the one-off role: an excellent ROI bootstrap /
  calibration verifier if the grid is ever lost — not a per-frame
  replacement for it, and not a panel finder.

### (b) Tagging state changes on the displays — SAM: not suited

- SAM returns geometry (box+mask+optional confidence), not content:
  it does not read text, name colours as states, or reason about the
  scene ([dev.meta.ai/docs/sam/segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- A dot-matrix text change inside an already-lit panel leaves the
  panel mask almost unchanged, so mask-diff is blind to exactly the
  changes that matter. Per-cell colour/template/OCR comparison on
  the fixed crops detects them directly and names the new state.

### (c) Tracking panels across video — SAM: capable, but unnecessary here

- This is SAM 3.1's headline strength: identity-preserving tracks,
  16 objects in one multiplexed pass, 32 fps on an H100
  ([ai.meta.com/blog/segment-anything-model-3](https://ai.meta.com/blog/segment-anything-model-3/)).
- But fixed panels do not move, occlude, or re-enter; identity-by-
  grid-position is exact and free, and survives the entry/exit/
  occlusion cases where SAM ids are explicitly not guaranteed
  ([dev.meta.ai/docs/sam/reading-segmentation](https://dev.meta.ai/docs/sam/reading-segmentation)).
  SAM tracking earns its cost only if the camera or wall moves.

## Failure modes specific to LED dot-matrix panels

- Small text glyphs: SAM segments the panel as one object, not its
  glyphs. Meta notes SAM 3 "struggles to generalize to fine-grained
  out-of-domain concepts in a zero-shot manner" and adapts only with
  fine-tuning on annotated data
  ([ai.meta.com/blog/segment-anything-model-3](https://ai.meta.com/blog/segment-anything-model-3/)).
  Do not expect per-character or per-dot masks zero-shot.
- Moire / flicker: refresh-vs-shutter aliasing makes panels shimmer
  frame to frame; expect mask-edge jitter, confidence fluctuation,
  and occasional dropped panels (empty frames emit no line)
  ([dev.meta.ai/docs/sam/reading-segmentation](https://dev.meta.ai/docs/sam/reading-segmentation)).
  A fixed ROI integrates the same pixels every frame and can average
  over flicker instead of chasing it.
- Dark/off panels: a panel showing nothing may not match "screen/
  panel" at all — zero matches is a normal API outcome
  ([dev.meta.ai/docs/sam/overview](https://dev.meta.ai/docs/sam/overview)) —
  so "off" and "not found" are confounded. The grid knows the cell
  exists and can measure its darkness directly.
- Mirrored rear view: panel rectangles still segment, but glyphs are
  mirror-reversed; SAM gives no reading either way, and downstream
  OCR on SAM crops fails unless the crop is flipped. Fixed ROIs make
  the flip a one-line, always-on correction.
- Perspective: masks follow the warped quad, but boxes are
  axis-aligned, so neighbouring panels intrude into each box at an
  angle. Rectify each fixed cell with the homography before any
  colour/template comparison; SAM output still needs that step.
- Identical neighbours: 16 visually identical adjacent rectangles are
  the crowded-similar-objects case; id swaps would silently mislabel
  state changes. Grid position cannot swap.

## Bottom line

Keep the classical fixed-grid classifier as the wall pipeline. SAM 3.1 is a reasonable one-off ROI-derivation tool and a strong general tracker, but it adds GPU/API cost, nondeterminism, and a 16-object ceiling to problems (a)-(c) that fixed geometry already solves exactly — and it cannot do (b) at all.

## Decisive comparison, executed (2026-11-06)

Correction first: an earlier version of this page reported
`401 invalid_api_key` for the project keys. That was a defect in
our own probe script (its authorisation header was mangled before
sending), not a Meta response. Re-tested correctly, both project
keys authenticate, `sam-3.1` is listed, and the comparison below
actually ran. Evidence: `validation/wall-observer/sam31-comparison-001.json`.

Setup: SAM 3.1 via `POST https://api.meta.ai/v1/responses`,
`include_confidence=true`, on stored wall captures. Grid side: the
calibrated fixed grid (`wall_report.DEFAULT_CORNERS`) on
`validation/wall-observer/demo-001/sample-beginning.jpg` (1000x750,
all 16 panels READY), whose same-state noise floor is mean
per-cell RGB delta 1.45, max 4.03.

| Test | Result |
|---|---|
| Concept "LED panel" / "monitor" / "television" | 0 objects |
| Concept "screen" / "display" / "LED screen" | 1 object: the whole wall (conf 0.85-0.95; best single-cell box IoU 0.067) |
| Object prompts: the grid's 16 boxes | 16/16 returned, mean box IoU **0.921**, min 0.868, conf 0.73-0.91 |
| Concept "screen", second identical run | Identical box and confidence |
| Panel state (text/colour) in any output | None — box + mask + confidence only |

Verdict, now measured rather than inferred: SAM cannot discover
the 16 panels and cannot read their state, so it is not the wall
pipeline. Given known boxes it refines them superbly (IoU 0.921),
which makes it a genuine one-off calibration bootstrap/verifier —
the role section (a) predicted. The fixed grid remains the
runtime answer: exact cell identity, deterministic, CPU-only.

Audio note: the same API lists `muse-voice-transcribe-1.0`
(speech-to-text) but no speech-generation model, so generated
mission-alert audio is not available on this API today.
