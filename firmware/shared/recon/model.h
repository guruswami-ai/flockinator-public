#pragma once
// Scripted display theatre only. No navigation, inference or actuator outputs.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
namespace recon {
constexpr float Pi = 3.14159265358979323846f;
enum State : uint8_t {
  HOLD,
  SCAN,
  SEEN,
  SHARE,
  CHECK,
  DOUBT,
  EVENT,
  LOST,
  MARK,
  CRASH,
  EMPTY,
  NOLINK,
  ALERT,
  PRIORITY,
  CLAIM,
  ASSIGN,
  YIELD,
  LOITER,
  R2B,
  LAND,
  CHARGE,
  STANDBY,
  FRIEND,
  TARGET,
  DEPLOY,
  APPROVED,
  ORDERS,
  TAKEOFF,
  BLANK,
  READY,
  Count
};
inline const char *name(uint8_t state) {
  static const char *names[] = {
      "HOLD",   "SCAN",     "SEEN",   "SHARE",   "CHECK",  "DOUBT",
      "EVENT", "LOST",     "MARK",   "CRASH",   "EMPTY",  "NOLINK",
      "ALERT",  "PRIORITY", "CLAIM",  "ASSIGN",  "YIELD",  "LOITER",
      "R2B",    "LAND",     "CHARGE", "STANDBY", "FRIEND", "TARGET",
      "DEPLOY", "APPROVED", "ORDERS", "TAKEOFF", "BLANK",  "READY"};
  return state < Count ? names[state] : "UNKNOWN";
}
enum class Overview : uint8_t { Ready, OnMission, DOWN, MIA, Charging, Unknown };
inline const char *overview_name(Overview value) {
  const char *names[] = {"READY", "OM", "DOWN", "LOST", "CHARGING"};
  return uint8_t(value) < 5 ? names[uint8_t(value)] : "--";
}
inline Overview decode_overview(uint8_t version, uint8_t value) {
  return version == 1 && value < 5 ? Overview(value) : Overview::Unknown;
}
enum Sensor : uint8_t { CAM, WH, BH, NV, IR };
inline const char *sensor_name(uint8_t s) {
  static const char *names[] = {"CAM", "WH", "BH", "NV", "IR"};
  return s < 5 ? names[s] : "?";
}
inline const char *scenario_name(uint8_t s) {
  static const char *names[] = {"Mixed outcomes", "Survey & return",
                                "Link disruption"};
  return s < 3 ? names[s] : "Unknown";
}
inline const char *goal_name(uint8_t g) {
  static const char *names[] = {"Observe", "Compare reports", "Recovery"};
  return g < 3 ? names[g] : "Unknown";
}
struct Config {
  uint32_t run = 0, seed = 1;
  uint16_t seconds = 64;
  uint8_t scenario = 0, goal = 0;
  bool repeat = true;
};
inline bool valid(const Config &c) {
  return c.run && c.seed && (c.seconds == 64 || c.seconds == 96) &&
         c.scenario < 3 && c.goal < 3;
}
inline bool same(const Config &a, const Config &b) {
  return a.run == b.run && a.seed == b.seed && a.seconds == b.seconds &&
         a.scenario == b.scenario && a.goal == b.goal && a.repeat == b.repeat;
}
constexpr unsigned CommandSize = 20, HealthSize = 128;
inline uint32_t get32(const uint8_t *p) {
  return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 |
         uint32_t(p[3]) << 24;
}
inline void put32(uint8_t *p, uint32_t x) {
  for (int i = 0; i < 4; i++)
    p[i] = x >> (i * 8);
}
inline bool command_decode(const uint8_t *p, unsigned n, Config &c, bool &start,
                           uint32_t &delay) {
  if (n != CommandSize || p[0] != 1 || p[1] > 1 || p[4] > 1 || p[5] || p[7])
    return false;
  c = {get32(p + 8), get32(p + 12), p[6], p[2], p[3], bool(p[4])};
  start = p[1];
  delay = get32(p + 16);
  return valid(c) && delay <= 60000;
}
inline void command_encode(uint8_t *p, const Config &c, bool start,
                           uint32_t delay) {
  memset(p, 0, CommandSize);
  p[0] = 1;
  p[1] = start;
  p[2] = c.scenario;
  p[3] = c.goal;
  p[4] = c.repeat;
  p[6] = c.seconds;
  put32(p + 8, c.run);
  put32(p + 12, c.seed);
  put32(p + 16, delay);
}
inline float mod(float a, float b) { return a - b * std::floor(a / b); }
inline float smooth(float x) {
  x = std::max(0.f, std::min(1.f, x));
  return x * x * (3 - 2 * x);
}
inline bool reversible(State s) {
  return s <= LOST || (s >= ALERT && s <= YIELD);
}
inline float visual(State s, float t) {
  if (!reversible(s))
    return t;
  float c = mod(t, 8), p = c <= 4 ? c : 8 - c;
  return 2 * (1 - std::cos(Pi * p / 4));
}
inline uint32_t hash(uint32_t seed, uint32_t a, uint32_t b = 0) {
  uint32_t n = seed ^ ((a + 1) * 0x45d9f3bu) ^ ((b + 1) * 0x27d4eb2du);
  n = (n ^ (n >> 16)) * 0x45d9f3bu;
  return n ^ (n >> 16);
}
inline uint32_t mix(uint32_t n) {
  n = (n ^ (n >> 16)) * 0x45d9f3bu;
  n = (n ^ (n >> 16)) * 0x45d9f3bu;
  return n ^ (n >> 16);
}
inline void bag(uint32_t key, uint32_t block, uint8_t *out) {
  for (int i = 0; i < 10; i++)
    out[i] = i;
  uint32_t v = mix(key ^ ((block + 1) * 0x85ebca6bu));
  for (int i = 9; i > 0; i--) {
    v = mix(v + 0x9e3779b9u);
    std::swap(out[i], out[v % (i + 1)]);
  }
}
inline uint8_t variant(uint32_t seed, int index, const char *state,
                       uint32_t visit) {
  uint32_t key = mix(seed ^ ((index + 1) * 0x27d4eb2du));
  for (auto p = state; *p; p++)
    key = mix(key ^ uint8_t(*p));
  uint8_t a[10], b[10];
  bag(key, visit / 10, a);
  if (visit >= 10) {
    bag(key, visit / 10 - 1, b);
    if (a[0] == b[9])
      std::swap(a[0], a[1]);
  }
  return a[visit % 10];
}
struct Motion {
  float bank, sway, pitch, heave, rate, speed, offset, tx, ty, exit, roll,
      rollTime, zoomPower, zoomMax;
};
constexpr Motion motions[] = {
    {0, .12, -2, 2, .8, .8, 0, 6, 3, 0, 1, 1.5, 2, 4},
    {-.3, .14, 0, 3, .7, 1, .8, 10, 4, Pi, -1, 1.2, 1.4, 3.5},
    {.3, .16, -3, 2.5, .9, 1.1, 1.6, 8, 6, .4, 1, 1.8, 2.6, 4.5},
    {-.08, .18, 5, 3, .6, .7, 2.4, 5, 7, -1.2, -1, 1.9, 1.7, 4.2},
    {.06, .16, -7, 2, .8, 1.3, 3.2, 9, 3, 1.2, 1, 1.1, 2.8, 3.8},
    {0, .43, -1, 4, 1.6, 1, 4, 11, 5, -2.1, -1, 1.6, 2.2, 4.7},
    {.12, .3, 1, 5, 2.2, .9, 4.8, 6, 8, 2.1, 1, 1.35, 1.2, 3.7},
    {-.4, .12, -4, 2, .45, .6, 5.6, 12, 4, Pi + .3, -1, 2.1, 3, 4.3},
    {.1, .1, -9, 1.5, 1.1, 1.6, 6.4, 4, 6, -.5, 1, 1.65, 1.8, 4.8},
    {.25, .3, 3, 3.5, 1.25, 1.2, 7.2, 10, 7, 2.7, -1, 1.4, 2.4, 3.6}};
struct Scene {
  State state = READY;
  float phase = 0, motion = 0, launch = 0, commAge = 99;
  uint32_t cycle = 0;
  uint8_t variation = 0, camera = 0, sensor = NV, owner = 0, source = 0,
          peer = 0, direction = 0, goal = 0;
  bool observations = false, friendly = false;
};
inline State flight_state(const Config &c, uint32_t cycle, int i, int round,
                          float offset, int owner, int challenger) {
  if (offset < 20) {
    if (c.scenario == 2 && round > 0) {
      const State disrupted[] = {NOLINK, DOUBT, LOST, CHECK};
      return disrupted[(i + round) % 4];
    }
    if (c.goal == 1 && round > 0)
      return (i + round) % 2 ? DOUBT : CHECK;
    if (round == 0)
      return i % 2 ? LOITER : SCAN;
    const State states[] = {SCAN,  LOITER, SEEN, CHECK,
                            SHARE, LOITER, HOLD, DOUBT};
    return states[hash(c.seed, cycle * 97 + round * 3, i) % 8];
  }
  if (c.goal == 2)
    return LOITER;
  if (offset < 22)
    return ALERT;
  if (offset < 24)
    return PRIORITY;
  if (offset < 26)
    return i == owner || i == challenger ? CLAIM : CHECK;
  if (offset < 30)
    return i == owner ? ASSIGN : YIELD;
  return i == owner ? SEEN : SCAN;
}
inline State ending_for(const Config &c, uint32_t cycle, int i) {
  uint32_t draw = hash(c.seed, cycle * 17 + i, 271) % 10;
  return c.scenario == 1 || c.goal == 2 ? R2B
         : c.scenario == 2 ? (draw < 5 ? NOLINK : R2B)
         : draw < 3 ? MARK : draw < 5 ? CRASH : draw < 6 ? EMPTY : R2B;
}
// Authoritative simulated aircraft condition, independent of UI polling history.
inline Overview overview(const Config &c, uint32_t elapsed, int i) {
  uint32_t duration = (32 + c.seconds + 31) * 1000u;
  uint32_t cycle = elapsed / duration, t = elapsed % duration;
  if ((!c.repeat && cycle) || t < 6000) return Overview::Ready;
  int reserve = hash(c.seed, cycle, 77) % 16;
  if (i == reserve || i == (reserve + 8) % 16) return Overview::Ready;
  int32_t age = int32_t(t) - int32_t((32 + c.seconds + hash(c.seed, cycle, i) % 5) * 1000u);
  if (age < 0) {
    // Mid-flight scripted link disruption is recoverable, not a permanent loss.
    if (c.scenario == 2 && t >= 64000 && t < (32u+c.seconds)*1000u && (t - 32000) % 32000 < 20000 &&
        (i + (t - 32000) / 32000) % 4 == 0) return Overview::MIA;
    return Overview::OnMission;
  }
  switch (ending_for(c, cycle, i)) {
  case MARK: return age < 10000 ? Overview::OnMission : Overview::DOWN;
  case CRASH: return age < 3000 ? Overview::OnMission : Overview::DOWN;
  case EMPTY: return age < 3000 ? Overview::OnMission : Overview::MIA;
  case NOLINK: return Overview::MIA;
  default: return age < 14000 ? Overview::OnMission : Overview::Charging;
  }
}
inline Scene scene(const Config &c, uint32_t elapsed, int i) {
  Scene s;
  const float duration = 32 + c.seconds + 26 + 5;
  float seconds = elapsed / 1000.f;
  uint32_t cycle = uint32_t(seconds / duration);
  if (!c.repeat && cycle)
    return s;
  s.cycle = cycle + 1;
  s.goal = c.goal;
  float t = mod(seconds, duration), flight = t - 32;
  int reserve = hash(c.seed, cycle, 77) % 16;
  bool parked = i == reserve || i == (reserve + 8) % 16;
  int participants[14], count = 0;
  for (int n = 0; n < 16; n++)
    if (n != reserve && n != (reserve + 8) % 16)
      participants[count++] = n;
  s.camera = variant(c.seed, i, "FLIGHT", cycle);
  s.variation = s.camera;
  s.motion = t - 6;
  s.launch = smooth((t - 6) / 6);
  if (t < 2) {
    s.state = APPROVED;
    s.phase = t;
  } else if (t < 6) {
    s.state = ORDERS;
    s.phase = t - 2;
  } else if (t < 12) {
    s.state = TAKEOFF;
    s.phase = t - 6;
    s.sensor = CAM;
  } else if (t < 32) {
    s.state = DEPLOY;
    s.phase = t - 12;
    s.sensor = CAM;
  } else if (flight < c.seconds) {
    int round = int(flight / 32);
    float offset = mod(flight, 32);
    int slot = round * 3 % 14;
    s.source = participants[slot];
    s.owner = participants[(slot + 5) % 14];
    int challenger = participants[(slot + 9) % 14];
    s.state = flight_state(c, cycle, i, round, offset, s.owner, challenger);
    s.phase = offset < 20   ? offset
              : offset < 22 ? offset - 20
              : offset < 24 ? offset - 22
              : offset < 26 ? offset - 24
              : offset < 30 ? offset - 26
                            : offset - 30;
    if (c.goal == 2 && offset >= 20)
      s.phase = offset - 20;
    s.variation = variant(c.seed, i, name(s.state), cycle + round * 10);
    s.motion = 26;
    for (int r = 0; r <= round; r++) {
      int own = participants[(r * 3 + 5) % 14],
          ch = participants[(r * 3 + 9) % 14];
      const int starts[] = {0, 20, 22, 24, 26, 30, 32};
      for (int k = 0; k < 6; k++) {
        if (r == round && offset < starts[k])
          break;
        auto st = flight_state(c, cycle, i, r, starts[k], own, ch);
        float len = r == round ? std::min(offset - float(starts[k]),
                                          float(starts[k + 1] - starts[k]))
                               : float(starts[k + 1] - starts[k]);
        s.motion += visual(st, len);
        if (r == round && offset < starts[k + 1])
          break;
      }
    }
    s.sensor = (i + cycle + int(flight / 5)) % 4;
    s.observations = flight >= 4 && !parked;
    auto broadcast = [&](float age) {
      s.direction = i == s.source ? 1 : 2;
      s.peer = i == s.source ? 255 : s.source;
      s.commAge = age;
    };
    if (offset >= 12 && offset < 16) {
      s.friendly = true;
      broadcast(offset - 12);
    } else if (c.goal != 2 && offset >= 20 && offset < 22)
      broadcast(offset - 20);
    else if (c.goal != 2 && offset >= 26 && offset < 30)
      broadcast(offset - 26);
    else if (c.goal != 2 && offset >= 24 && offset < 26) {
      int sender = offset < 24.875 ? s.owner : challenger;
      s.commAge = offset - (offset < 24.875 ? 24 : 24.875);
      if (i == sender) {
        s.direction = 1;
        s.peer = s.source;
      } else if (i == s.source) {
        s.direction = 2;
        s.peer = sender;
      }
    } else if (offset < 20) {
      // Every display derives the same scripted pair, including the receiver.
      int sender = -1, receiver = -1;
      for (int n = 0; n < 16; n++) {
        int candidate = (int(flight / 2) + n) % 16;
        if (candidate == reserve || candidate == (reserve + 8) % 16)
          continue;
        if (flight_state(c, cycle, candidate, round, offset, s.owner,
                         challenger) == SHARE) {
          sender = candidate;
          break;
        }
      }
      for (int n = 0; n < 14; n++)
        if (participants[n] == sender)
          receiver = participants[(n + 5) % 14];
      if (i == sender) {
        s.direction = 1;
        s.peer = receiver;
      } else if (i == receiver) {
        s.direction = 2;
        s.peer = sender;
      }
      s.commAge = mod(flight, 2);
    }
  } else if (flight < c.seconds + 26) {
    float age = flight - c.seconds - int(hash(c.seed, cycle, i) % 5);
    State ending = ending_for(c, cycle, i);
    if (age < 0) {
      s.state = SCAN;
      s.phase = flight - c.seconds;
    } else if (ending == R2B) {
      s.state = age < 8 ? R2B : age < 14 ? LAND : age < 22 ? CHARGE : BLANK;
      s.phase = age - (age < 8 ? 0 : age < 14 ? 8 : age < 22 ? 14 : 22);
    } else {
      float length = ending == MARK ? 16.5 : 8;
      s.state = age < length ? ending : BLANK;
      s.phase = age < length ? age : age - length;
    }
    s.variation = variant(c.seed, i, name(ending), cycle);
    s.motion = 26;
    for (int r = 0; r < c.seconds / 32; r++) {
      int own = participants[(r * 3 + 5) % 14],
          ch = participants[(r * 3 + 9) % 14];
      const int starts[] = {0, 20, 22, 24, 26, 30, 32};
      for (int k = 0; k < 6; k++)
        s.motion += visual(flight_state(c, cycle, i, r, starts[k], own, ch),
                           starts[k + 1] - starts[k]);
    }
    s.motion +=
        visual(SCAN, float(hash(c.seed, cycle, i) % 5)) + std::max(age, 0.f);
  } else {
    s.state = BLANK;
    s.phase = flight - c.seconds - 26;
  }
  if (parked && t < duration - 5) {
    s.state = STANDBY;
    s.phase = t;
    s.launch = 0;
    s.observations = false;
  }
  return s;
}
struct Runtime {
  Config config;
  uint32_t accepted = 0, delay = 0;
  bool running = false, ever = false;
  bool apply(const Config &c, bool start, uint32_t wait, uint32_t now) {
    if (!valid(c) || wait > 60000)
      return false;
    if (start) {
      if (ever && config.run == c.run)
        return running && same(config, c);
      config = c;
      accepted = now;
      delay = wait;
      running = true;
      ever = true;
    } else {
      if (ever && config.run != c.run)
        return false;
      config = c;
      running = false;
      ever = true;
    }
    return true;
  }
  bool waiting(uint32_t now) const {
    return running && uint32_t(now - accepted) < delay;
  }
  uint32_t elapsed(uint32_t now) const {
    return !running || waiting(now) ? 0 : uint32_t(now - accepted) - delay;
  }
  bool active(uint32_t now) const {
    return running && uint32_t(now - accepted) < 86400000u &&
           (config.repeat ||
            elapsed(now) < uint32_t(32 + config.seconds + 31) * 1000);
  }
  Overview summary(uint32_t now, int i) const {
    return active(now) && !waiting(now) ? overview(config, elapsed(now), i)
                                        : Overview::Ready;
  }
  Scene frame(uint32_t now, int i) const {
    return active(now) && !waiting(now) ? scene(config, elapsed(now), i)
                                        : Scene{};
  }
};
} // namespace recon
