# Why search and rescue first - and why A2A is a new frontier

## A first experiment people can feel

The quadcopter survey swarm was chosen as Flockinator's first
experiment because the stakes are easy to imagine. Picture a
search-and-rescue commander sending scouts out to find a lost
child, or a downed aircraft: limited battery, partial views,
hazardous country and long distances degrading every radio link,
decisions in seconds, and a wrong call - that shape is a survivor,
that one is a hazard; search here, hold there - that cannot be
taken back once the light or the battery is gone.

Our sixteen panels pretend to be that swarm so the decisions become
visible. When a false report wins, you do not read it in a log. You
watch the flock believe the wrong thing, together, in colour. That
immediacy is the point: agent-to-agent (A2A) failure should be
something a person can *see* before they are asked to trust it.

Search and rescue is the lead story because it carries the full
weight of the problem - a commander who must trust scouts she
cannot supervise, in conditions that fight their communication -
without reducing the work to weapons research. The same concept
holds wherever the stakes are real: the battlefield case that
inspired the scenario, and the civilian cases (clinics, shops,
roads, homes) that embedded agents will actually fill.

How would the scouts actually search? After an earthquake or a
flood, the swarm's nodes are exactly the kind of cheap, expendable
sensors you would send into places humans cannot yet go:

- **Thermal / infrared cameras** sweep rubble, floodwater, and
  collapsed buildings for heat signatures - a survivor under
  debris is, to an IR eye, a warm shape in a cold field.
- **CO2 sensing** sniffs the air in voids and sealed rooms:
  exhaled carbon dioxide accumulating where no vent explains it
  is a quiet, powerful sign of life.
- Ordinary cameras, microphones (a tapped pipe, a voice),
  temperature, humidity, motion, and gas sensors fill in the
  picture each node can afford.

No single node sees enough. One catches a heat smudge, another a
CO2 rise two metres away, a third hears nothing and doubts both.
The swarm's shared intelligence - who corroborates, who doubts,
what gets believed in time - is what turns scattered sensor
scraps into "dig here, now". That is also why a false report is
so costly, and why an attacker who can fabricate a heat signature
or suppress a real one is dangerous in a way a broken node is
not: the swarm will dig in the wrong place while the light lasts.

In the technical results you will see the labels *Friendly* and
*Enemy* - the scenario's original military shorthand. Read them
in the rescue story as *survivor* and *hazard*: the unforgivable
error, in either story, is the swarm confidently committing to
the dangerous misidentification.

## Where intelligence may actually live

Today's famous AI is monolithic: very large models, rented by
subscription, living in data centres. But intelligence is quietly
moving into devices - medical sensors, supermarket cash registers,
car navigation systems, and the flight controllers of quadcopters.
These are small, cheap, specialised agents, embedded everywhere,
talking to each other constantly. That is the **AIoT** world:
artificial intelligence in the Internet of Things.

The future is not either/or. It is hybrid: large models design,
audit, and occasionally arbitrate; tiny embedded agents act
continuously. Flockinator is itself that hybrid - frontier models
build the firmware and judge the evidence, a small local adversary
model attacks, and milliwatt-class nodes do the acting. The
research lives at the interface between those tiers.

Our hypothesis is that much of the intelligence in such a world
will not live inside any one device. It will live **between**
devices: in what they share, corroborate, doubt, and refuse to
believe (see [extra-node intelligence](extra-node-intelligence.md)).
If so, A2A communication is not plumbing. It is where the
intelligence is - and where it must be defended.

## The TCP/IP lesson - and what is different this time

When TCP/IP was new, it was trivial to spoof a packet and
impersonate an endpoint. Yet exploitation was slow, for a reason
easy to forget: very few humans then had the skills, knowledge,
and creativity to find the holes - or to propose the fixes. The
protocols had decades to grow protection layers (checksums and
sequence discipline, then TLS, authentication, attestation)
while the attacker population caught up.

In the AI age that grace period is gone. Holes will be found and
exploited by models, at machine speed, at a scale no human
attacker community could match. Our own adversary is a 30B-class
local model; in its first proposed scenario it already reached
for the highest-authority target available to it. The asymmetry
of attack - one cheap probe against a defence that must be right
every time - is likely *greater* now than in any previous network
era, and it favours whoever automates offence first.

That ends the oldest implicit defence: obscurity. An unpatched,
isolated node - in a medical device, a blood-bank fridge, a
critical industrial controller - used to be protected partly by
being obscure, uninteresting, and hard to reach. A model-driven
attacker does not get bored, does not skip the obscure device,
and can personalise an exploit for it at near-zero marginal
cost. Obscurity is no longer a security property; at best it is
a delay measured in machine time, which is to say barely at all.

## Three futures for A2A protection

A2A today is at the early, trusting stage: agents exchange
beliefs and confidence as if the other end were honest. The
experiment should help choose among three futures:

1. **Old protections still fit.** Signing, freshness, and
   recipient binding may be most of the answer. Our lab
   measurements support them for outsider forgery: forged and
   replayed messages are rejected.
2. **Necessary, but not enough.** Authentication proves *who*
   sent a claim, never whether it is *true*. Insider error,
   forwarded copies dressed as independent proof, and timing
   manipulation need A2A-native layers: corroboration that
   counts independence, abstention, dangerous-direction scoring.
   Those are what this project prototypes.
3. **They seed something new.** Agent networks may grow *belief
   layers* - standard ways to carry provenance, independence,
   and doubt with every claim - becoming the foundation of
   trustworthy machine cooperation instead of a retrofit after
   its first disasters.

Accountability sharpens the choice. A human platoon can refuse
an unlawful order and share responsibility for outcomes. A drone
swarm can do neither: responsibility stays, concentrated, with
the commander and the designers. That is not a reason to avoid
swarms; it is the reason their trust must be earned by testing -
friendly and hostile - before deployment, and why this project
publishes its rejected policies and successful attacks alongside
its wins.

## Why research it in a playground

Because the cost of learning these lessons late is deployment at
scale, against attackers who learn at machine speed. A
sixteen-panel flock that can be lied to safely, scored honestly,
and replayed seed by seed is how we find out - cheaply, visibly,
and before it matters - which protections the A2A age actually
needs. The quadcopters are the story. The frontier is every small
intelligent device that will ever need to decide whether to
believe another one.
