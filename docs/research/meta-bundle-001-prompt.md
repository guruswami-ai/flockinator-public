# Meta bundle 001: exact contributor prompt (instruction part)

Provenance repair for `docs/research/meta-contribution-bundle-001.md`.
The call was assembled by the wave-5 fan-out script as:
project context + the instruction below + the reviewed module
source (`twin.py` at blob SHA-256
`3589ab33cba2248f67f71ea8128de5d85f8c62c912c4be089a34fd2de35abfcf`,
recoverable via `git show af7c3ec:tools/kulira-core/kulira_core/twin.py`).
The script itself was a session scratch file and is not archived;
this file preserves the exact instruction text it sent, extracted
2026-11-07. Model: `muse-spark-1.3-contributor`, Meta Model API
`POST /v1/responses`. Raw API envelopes were not archived (see
bundle omissions); this prompt plus the hashed source and the
verbatim response are the replayable input record.

## Instruction sent (verbatim)

Review this Python module for a host simulation twin (parity
comparator for an embedded device journal). Check: determinism
(RNG stream separation, float hashing), spec compliance (rule
priority LOSS > OBSTACLE > SIGNAL, thresholds 0.70/0.10/0.05,
FNV-1a hash over 'tick:seed:signal_q:obstacle:loss'), parity()
correctness when row counts differ, and any bug where host and
a correct C++ device port would diverge. List findings by
severity.

(Followed by the full module source identified by the hash above,
under the project context preamble used for all wave-5 tasks:
simulation study framing, pre-registration discipline,
simulation-only claims.)
