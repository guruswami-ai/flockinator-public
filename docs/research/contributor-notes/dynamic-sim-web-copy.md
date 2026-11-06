<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# From Movie Wall to Mountain Rescue Team

**16 little screens. 16 rookie pilots. One lost hiker — pretend.**

If you've seen our wall in the lab, you know it as flashing panels all moving in perfect sync. It looked alive, but it wasn't. Each panel was just playing a script we wrote: go here, blink there, repeat.

Now we're giving the wall a new job: learning to search together.

### Before: we played a movie

Think of the old wall like a cartoon. One central file told all sixteen ESP32 panel computers exactly what to show. No choices, no surprises, no teamwork. If a "drone" found the hiker, it's because we told it to.

Pretty, but useless for science. Real rescue is messy and unscripted.

### Now: each panel flies its own drone

We've turned the wall into a live shared world:

* **One controller computer** runs a virtual mountain valley — trails, trees, wind gusts, and a lost hiker waiting for help.
* **Each of the 16 panel computers** flies its *own* virtual rescue quadcopter in that same world.
* Each drone only sees its little patch through pretend cameras, decides for itself — *turn left? check that red jacket glint? shout to a neighbor?* — and records its own evidence log: *what I saw, where, when, how sure I am.*

No choreographer. Sixteen separate minds, one shared sky.

### Why let them decide? To study emergence

Emergence is a fancy word for a simple idea: team patterns nobody programmed.

When independent drones search together, they start to do things we didn't code line-by-line: split up to cover more ground, take turns checking the same clue, all rush a false alarm and then recover. Sometimes they help each other. Sometimes they get in each other's way.

You can't learn that from a script. A script can't surprise you.

By letting simple, local decisions add up live, we can safely ask: does teamwork actually find the hiker faster? When does chatter help vs. clog? How do small mistakes cascade?

Those lessons matter far beyond games — for future real drone teams that will need to stay calm, spread out, and not all chase the same shadow.

> **Honesty box: What is still simulated**
> No real drones fly. No real hiker is at risk. The mountain, wind, cameras and radios are all pretend numbers in software. All data is simulated only — clues about teamwork, not proof for real rescue. To keep it fair, we write down our guesses in advance, state what would prove us wrong, and use fixed starting seeds so anyone can re-run the exact same mountain.
