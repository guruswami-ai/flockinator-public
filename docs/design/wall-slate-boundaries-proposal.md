# Proposed wall slates: opening intent and closing evidence

**Proposal for [#89](https://github.com/guruswami-ai/flockinator-public/issues/89),
2026-11-07. Not an accepted protocol, firmware implementation or device result.**
The existing host slate and tile helpers are useful, but displaying their final
checksum at live mission start is not possible when the data do not yet exist.

## Existing pieces and the missing contract

- [`slate.py`](../../tools/kulira-core/kulira_core/slate.py) derives the v1
  `FLOCK-<16 hex>` checksum from mission ID, start UTC, telemetry hash and sorted
  frame hashes. Its `qr_payload` and `validate_qr_payload` define the existing
  final-evidence payload. Keep those meanings unchanged.
- [`dataset.py`](../../tools/kulira-core/kulira_core/dataset.py) computes that
  checksum after collecting the selected files, then creates optional opening
  and closing **video derivatives**. Those are retrospective editing assets;
  their presence does not prove the physical wall showed a live slate.
- [`tiles.py`](../../tools/kulira-core/kulira_core/tiles.py) already splits an
  exact 256×256 source into sixteen addressed 64×64 PPM tiles and records file
  hashes and horizontal flipping. Reuse it. Its wall convention is top-to-bottom
  D,C,B,A and left-to-right 1–4; this differs from treating the firmware's
  column-first index as a screen row. Confirm orientation against a labelled
  fixture before deployment, including the explicit flip setting.
- [`mission.cpp`](../../firmware/node-platform/src/mission.cpp) accepts a bounded
  mission command with run/seed/scenario/timing fields, but no slate image,
  UTC or checksum. [`display.cpp`](../../firmware/node-platform/src/display.cpp)
  exposes selected display modes, not a general wall-slate transaction.
  [`recon::Runtime`](../../firmware/shared/recon/model.h) uses elapsed monotonic
  time. A run number alone is neither wall-clock UTC nor a bundle checksum.

Existing slate/tile tests check derivation, payload shape, placement, dimensions
and file hashes. The image test uses an injected checkerboard, not a real QR
round trip. Those tests alone do not establish camera readability, complete-wall
presentation or correct orientation on a new installation.

## Two identities, with different meanings

**Opening: precommitted intent.** Add a separately named format,
`flockinator-slate-open/1`; do not pass it to the current v1 final-slate validator
or manufacture a `FLOCK-` checksum for future frames. Proposed fields are:

| Field | Meaning and proposed validation |
|---|---|
| `format` | Exact `flockinator-slate-open/1` discriminator |
| `mission` | Nonempty bounded public identifier; same ID throughout the evidence chain |
| `planned_start_utc` | Explicit scheduled UTC in ISO 8601 with `Z`; not an observed start time |
| `plan_sha256` | Full lowercase SHA-256 of the retained immutable plan file |

The plan records intended scenario, source/image revisions, expected A1–D4
labels, orientation, display duration, clock/skew tolerance and capture phase
boundaries. Hash the exact saved bytes; do not parse and reserialize them when
verifying. The plan must exclude its own digest, the derived opening image and
its tile hashes. A later delivery manifest references both the plan digest and
the generated image/tile hashes. Label the wall text `OPEN / PLAN`, mission ID,
`UTC PLAN` and a shortened plan digest; retain the full digest in the QR/file.
No actual run, timing accuracy or successful presentation is implied.

**Closing: completed mission data.** After capture is closed and the mission
bundle is immutable, reuse `flockinator-slate/1`, the existing checksum function
and its unchanged `mission`, `utc`, `ck` and optional telemetry-hash fields.
Here `utc` remains the bundle's recorded mission start UTC, not the time the
closing image was generated. Label the image `CLOSE / DATA`. Record the full
bundle manifest hash beside its short checksum in the evidence index; short
checksums help identification and do not authenticate a publisher.

A clock that cannot establish UTC must report that limitation. Do not substitute
an elapsed timer or planned UTC for an observed start. The proposed live
acceptance requires a usable UTC association, even though the current v1 helper
accepts arbitrary nonempty UTC strings; stricter new validation must not silently
reclassify old archives.

## Break the self-hash cycle with an explicit capture boundary

1. Save the opening plan. Generate its opening graphic and tiles, then retain
   the delivery manifest separately. Capture opening presentation as evidence.
2. Run the mission and stop the **mission-data capture session** at the
   predeclared boundary, before creating the closing slate. Freeze its telemetry
   and media list, including opening evidence if that was declared in the plan.
   Package that fixed session with the existing dataset path and derive v1 `ck`.
3. Display the closing slate for that already frozen bundle. Record its camera
   footage and acknowledgements in a **separate closing-evidence session**.
   These files reference the frozen bundle manifest hash and its `ck`; they are
   not appended to the bundle whose checksum the image displays.
4. A final evidence index lists the immutable mission bundle, opening plan and
   closing-evidence files with their hashes. It excludes its own hash and is not
   another object the closing QR claims to cover. A later release may hash this
   index externally without creating a reference back into its own contents.

This is an acyclic chain: plan → opening presentation → mission bundle → closing
presentation → final index. No image contains a digest that depends on that same
image's captured bytes. Keep every phase and exclusion inspectable; do not drop
unfavourable mission frames after seeing them. A closing camera clip belongs to
closing evidence because of the predeclared boundary, not because it is unwanted.
A single continuous video spanning both phases needs an explicit, recorded split
and source-byte lineage; the first implementation should use separate sessions.

## Presentation and acknowledgements

Propose a prepare/commit/observe transaction, implemented separately from the
existing mission command. Preparation must bind the phase, mission and plan or
bundle identity, node label, tile digest and expected image digest. Each panel
validates its addressed tile before acknowledging readiness. Do not present a
mixed wall assembled from different missions or phases.

The coordinator commits only after all sixteen intended panels are ready for
the same transaction. Duplicate messages are idempotent; conflicting digests,
wrong labels, expired preparation or changed boot IDs reject. A fresh status
read must distinguish **received**, **scheduled** and **displayed**. Delivery
success is not proof of pixels on the wall.

Hold the complete slate for at least three seconds of common visible overlap.
Record per-panel monotonic display-start/end and boot IDs, coordinator UTC
association and measured clock uncertainty. Declare the allowed skew before the
run; if it cannot be bounded, the three-second wall-wide interval is unverified.
The authenticated local transport supplies command authority; hashes alone do
not. Cancellation/expiry must restore the prior safe display state without
silently starting or stopping a mission. The closing slate must never be
interpreted as a mission-start command.

Missing panels, stale acknowledgements, reboot, mismatched hashes or an
unreadable QR produce **incomplete/unverified presentation**, with the failure
retained. A text-only slate is an allowed fallback when declared in the plan,
but cannot be reported as a successful QR decode. A successful software join of
sixteen tile files is only an offline check. Actual wall acceptance needs safe,
silent camera footage showing the identity text and a successful independent QR
decode, or explicit text-only acceptance, throughout the required interval.

## Bounded implementation tasks after review

1. Add an opening-plan schema and separate validator; fixtures reject cross-use
   with final v1 payloads, malformed digests/UTC and self-referential plans.
   Add an evidence-index builder that enforces the phase/file partition.
2. Produce a deliberate 256×256 layout and reuse `split_graphic`. Preserve
   integer QR modules and a complete quiet zone; validate the actual encoded
   size instead of assuming any payload fits a given QR version. Do not simply
   downscale the existing 960-pixel report image. Test tile reconstruction,
   flips, clipping, truncation and decode of a real QR using an independent
   decoder. Include panel-gap/rotation fixtures; they approximate camera risk.
3. Add a versioned authenticated host/firmware transaction with bounded storage,
   replay/expiry rules, start/end status and timeout/cancellation tests. Reuse
   existing identity verification and coordinate with mission timing; do not
   expand the current mission allowlist ad hoc or weaken its validation.
4. After review/build/native tests, perform the separately authorized physical
   canary and wall capture. Record timing, missing/stale panels, decode outcome
   and firmware/image identity. Keep #89 open until this physical acceptance.

These tasks reuse current components and preserve historical artifacts. This
proposal does not change the slate checksum, tile orientation, mission protocol,
firmware or hardware state. Its immediate purpose is to make the missing work
reviewable rather than treating #89 as an unqualified image-painting task.
