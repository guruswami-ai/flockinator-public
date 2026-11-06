# How Flockinator tests all this

Flockinator is a playground where the ideas on these pages become measurements:

1. **Train small, alone.** Each node — each single member of the group — has its own small AI program, called a model. That model learns by itself first, so we know what it can do without help.
2. **Give it a flock.** A flock means a group working together. The nodes share what they see in a simulated search-and-rescue mission. Did sharing actually help, compared with each node keeping its thoughts private? We measure the difference, at the same cost.
3. **Send in the adversary.** An adversary means an attacker sent in to test the group. Kulira — a separate computer with its own small AI model — disrupts, impersonates, and lies to the swarm, politely at first, then harder. Nothing real is at risk; the mission is fictional and the lab is closed.
4. **Keep the truth hidden.** A scorekeeper — a separate program that keeps score — knows where every simulated object really was, and only reveals it after the run. Nodes cannot cheat, and neither can we.
5. **Promote nothing without proof.** New swarm policies — new shared rules for how the group acts — must beat the old ones on fresh missions, with zero tolerance for the most dangerous mistake: calling an enemy a friend. Failures are published, not deleted.

Because every run is seeded — it starts from a recorded starting point, like replaying the same shuffled deck — a surprising result can be replayed, argued with, and re-tested. That is the difference between a demo and an experiment.

Start with the story: [survey guide](../scenarios/quadcopter-survey/README.md).
Then the method in full: [experiments](../experiments.md).
Then the scoreboard: [results](../results/README.md).
