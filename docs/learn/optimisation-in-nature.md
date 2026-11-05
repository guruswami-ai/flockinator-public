# Optimisation in nature: survival, not smartest

It is tempting to imagine the swarm *learning its way downhill*
to the best possible behaviour, the way a training program
improves a model step by step. Nature does something related -
but cruder, and in some ways wiser.

Think of it as **gradient descent without a gradient**. In
ordinary machine learning, one optimiser sees the whole problem,
works out which direction is better, and adjusts everything at
once. In a flock, nobody sees the whole problem. Each node makes
a small local adjustment - trust this neighbour a little more,
doubt that sensor a little sooner, wait a little longer before
committing - and the *environment* supplies the feedback: the
policies that lead to dangerous mistakes do not get promoted;
the ones that survive do. Many noisy little steps, taken in
parallel by sixteen nodes at slightly different settings, are
how the group finds its way without a map. Nature never tells
anyone the landscape. It delivers one late, unexplained verdict:
reproduce, or don't.

And here is the part that changes how you should judge the
results: **the filter selects survivors, not the smartest.**
A parasite that throws away most of its own genome and lets its
host do the work is, by survival, winning. A hardy generalist
that is merely good enough in drought, flood, and disease
outlives the brilliant specialist the first year the weather
changes. Showy capability can even be a handicap that only
looks like fitness because the real landscape includes things
nobody put on the scoreboard.

So Flockinator does not ask "what is the optimal swarm?" It
asks "what swarm is *survivable*?" Our promotion gates are,
deliberately, viability gates: a new policy is promoted not for
the highest score but for clearing zero tolerance on the most
dangerous error - in rescue terms, never confidently sending
crews to a hazard as if it were a survivor - while staying
useful enough to be worth deploying. In a landscape that can
change under you - new terrain, a lying sensor, an adversary
who learns - reliably good enough and never catastrophically
wrong beats occasionally brilliant.

Two warnings come with the metaphor, and the experiments are
built around both:

- **We chose the landscape.** The gates define what "survives"
  here. Change the tolerance and a different policy evolves
  and wins. That is why the gates are written down *before*
  the runs (pre-registered): we are declaring the environment
  honestly, not discovering a law of nature.
- **The most capable-looking policy may be the most fragile.**
  One that memorises the test conditions tops the table and
  fails in the real world. Fresh unseen tests, frozen scoring,
  and eventually the same test on real hardware are how we
  avoid evolving a very fit idiot.

The swarm is not descending toward the smartest state. It is
being filtered toward a survivable one - and in any landscape
that can move, survivable is the smarter bet.
