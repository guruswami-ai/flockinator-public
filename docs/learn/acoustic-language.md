# Exploring communication through sound and dance

Flockinator's nodes have microphones, speaker output and animated panels. These
provide a way to explore how a group could exchange acoustic signals and develop
shared rhythms while responding to noise or misleading cues.

A host-side acoustic model is implemented and tested. It represents distance
attenuation and exclusion of a source's own phrase within a settling interval,
and calculates phase alignment and shared-pitch counts. Physical sound-driven
Patternflow animation and a swarm that learns acoustic signals remain proposed
experiments. The [model](../../tools/kulira-core/kulira_core/acoustic.py) and
[tests](../../tools/kulira-core/test_acoustic.py) define the implemented behaviour.

Three questions guide the experiment.

- **Can sounds carry learned information?** Track whether a receiver uses a phrase
  to make a better task decision on unseen examples. The current pitch-counting
  helper records which pitches occur across listeners. Shared meaning requires
  decoding and task-success measurements as well.
- **Can a group coordinate a performance?** Measure phase alignment, participation
  and recovery after a disturbance. The current synchrony metric ranges from zero
  for cancelling phase vectors to one for full alignment. Low values can describe
  structured patterns with opposing phases. Panel dance would show each node's
  recorded state and response to sound.
- **Can cooperation survive misleading cues?** Compare clean and disturbed runs
  with matched budgets and frozen stimuli. Distance, room reflections, source
  volume and microphone placement all need calibration in a physical experiment.

Camera and room-audio recordings can help an audience follow these interactions.
Time-aligned telemetry and controlled comparisons establish whether information
changed a decision, whether learning improved performance and whether a firmware
revision retained the gain. The [experimental methodology](../experiments.md)
defines those comparisons, and the [results record](../results/README.md) identifies
completed measurements and their limits.
