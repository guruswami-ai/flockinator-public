# Talking in harmonics: pheromones, music, and dance

Not every swarm talks in data packets. Ants talk in pheromones -
chemicals left in the world for whoever passes next. Bees talk in
dance. Flockinator's nodes have a third option their radio does
not give them: **sound**.

Each node has microphones and a speaker, and a screen that already
knows how to draw music - spectrum bars, pulses, patterns that
move with what the node hears and sings. So a new experiment
asks: put sixteen nodes in a room, let them make short harmonic
phrases, listen to each other, and see what happens.

Three things might emerge, and each is measurable:

- **A shared vocabulary.** No pitch is assigned a meaning. But if
  one node's phrase gets answered, copied, and spread - the way
  a pheromone trail strengthens with use - a shared set of
  pitches may grow that the group treats as signals. We count
  distinct pitches, and how many nodes share each one.
- **Synchrony.** Oscillators that hear each other tend to align.
  Fireflies do this; metronomes on a shared shelf do this. We
  measure phase alignment directly (a number from 0, chaos, to
  1, perfect unison) and watch whether nodes fall into coordinated
  music - or coordinated *movement* patterns on their panels,
  a visible dance driven by what they hear.
- **A channel attackers must respect physics to abuse.** Sound
  fades with distance and a node is briefly deaf after singing.
  A liar across the room is quieter than a friend beside you.
  That does not make acoustic trust automatic - a loudspeaker
  lies at any volume - but it changes the attack geometry in
  ways radio does not, and Kulira will test exactly that.

Why it matters beyond pretty lights: if small devices are going
to hold intelligence *between* themselves, they will use every
channel they have - radio, light, sound, shared surfaces. A
swarm that can invent even a primitive acoustic language in a
room is a visible, audible model of the same emergence we claim
for rescue sensing and for A2A protocols. And an audience can
*hear* consensus form - or be deceived - which no log file will
ever give them.

Status: the host-side acoustic model (distance attenuation,
self-deaf settling, synchrony and vocabulary metrics) is
implemented and tested in `tools/kulira-core`; firmware that
sings and listens on the nodes themselves is a separate,
owner-gated experiment. Nothing here is claimed as run on the
fleet yet.
