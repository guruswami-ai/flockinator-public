#include "recon_render.h"
#include <unity.h>
#include <cstring>
using namespace recon;
void setUp() {}
void tearDown() {}
void run_wrap_retry_and_stop() {
  Runtime r;
  Config c{42, 1234, 64, 0, 0, true};
  uint32_t now = UINT32_MAX - 2000;
  TEST_ASSERT_TRUE(r.apply(c, true, 3000, now));
  TEST_ASSERT_TRUE(r.waiting(now + 2999));
  TEST_ASSERT_FALSE(r.waiting(now + 3000));
  TEST_ASSERT_EQUAL_UINT32(1000, r.elapsed(now + 4000));
  TEST_ASSERT_TRUE(r.apply(c, true, 3000, now + 4000));
  TEST_ASSERT_EQUAL_UINT32(1000, r.elapsed(now + 4000));
  Config changed = c;
  changed.seed++;
  TEST_ASSERT_FALSE(r.apply(changed, true, 0, now + 4000));
  TEST_ASSERT_TRUE(r.apply(c, false, 0, now + 4000));
  TEST_ASSERT_FALSE(r.active(now + 4000));
  TEST_ASSERT_FALSE(r.apply(c, true, 0, now + 4001));
}
void commands_are_bounded() {
  Config c{1, 2, 96, 2, 2, false}, got;
  bool start;
  uint32_t wait;
  uint8_t bytes[CommandSize];
  command_encode(bytes, c, true, 1000);
  TEST_ASSERT_TRUE(command_decode(bytes, sizeof(bytes), got, start, wait));
  TEST_ASSERT_TRUE(same(c, got));
  TEST_ASSERT_TRUE(start);
  TEST_ASSERT_EQUAL(1000, wait);
  TEST_ASSERT_FALSE(command_decode(bytes, 19, got, start, wait));
  bytes[4] = 2;
  TEST_ASSERT_FALSE(command_decode(bytes, 20, got, start, wait));
  bytes[4] = 0;
  put32(bytes + 16, 60001);
  TEST_ASSERT_FALSE(command_decode(bytes, 20, got, start, wait));
}
void launch_has_twenty_seconds_before_observations() {
  Config c{1, 1234, 64, 0, 0, true};
  int flying = 0;
  for (int i = 0; i < 16; i++) {
    auto s = scene(c, 6000, i);
    if (s.state == STANDBY)
      continue;
    flying++;
    TEST_ASSERT_EQUAL(TAKEOFF, s.state);
    float last = -1;
    for (unsigned t = 6000; t < 12000; t += 125) {
      s = scene(c, t, i);
      TEST_ASSERT_GREATER_OR_EQUAL(last, s.launch);
      last = s.launch;
      TEST_ASSERT_FALSE(s.observations);
    }
    for (unsigned t = 12000; t < 32000; t += 125) {
      s = scene(c, t, i);
      TEST_ASSERT_EQUAL(DEPLOY, s.state);
      TEST_ASSERT_FALSE(s.observations);
    }
    s = scene(c, 32000, i);
    TEST_ASSERT_TRUE(s.state == SCAN || s.state == LOITER);
    TEST_ASSERT_FALSE(s.observations);
    TEST_ASSERT_TRUE(scene(c, 36000, i).observations);
  }
  TEST_ASSERT_EQUAL(14, flying);
}
void variants_exhaust_the_bag() {
  for (int i = 0; i < 16; i++)
    for (int st = 0; st < Count; st++) {
      int last = -1;
      for (int block = 0; block < 4; block++) {
        unsigned mask = 0;
        for (int j = 0; j < 10; j++) {
          auto v = variant(1234, i, name(st), block * 10 + j);
          TEST_ASSERT_LESS_THAN(10, v);
          if (j == 0 && block)
            TEST_ASSERT_NOT_EQUAL(last, v);
          mask |= 1u << v;
          last = v;
        }
        TEST_ASSERT_EQUAL(1023, mask);
      }
    }
}
void stop_on_completion_and_fleet_gap() {
  Runtime r;
  Config c{1, 99, 64, 1, 2, false};
  TEST_ASSERT_TRUE(r.apply(c, true, 0, 0));
  for (int i = 0; i < 16; i++) {
    for (unsigned t = 122000; t < 127000; t += 125)
      TEST_ASSERT_EQUAL(BLANK, r.frame(t, i).state);
    TEST_ASSERT_EQUAL(READY, r.frame(127000, i).state);
  }
  TEST_ASSERT_FALSE(r.active(127000));
}
void reverse_only_loopable_states() {
  TEST_ASSERT_FLOAT_WITHIN(.001, visual(SCAN, 2), visual(SCAN, 6));
  TEST_ASSERT_FLOAT_WITHIN(.001, 6, visual(TAKEOFF, 6));
  TEST_ASSERT_FLOAT_WITHIN(.001, 6, visual(MARK, 6));
  TEST_ASSERT_FLOAT_WITHIN(.001, 6, visual(LAND, 6));
}
void countdown_and_message_borders() {
  node::Frame f, scratch;
  Scene s;
  s.state = MARK;
  s.launch = 1;
  s.phase = 1;
  render(f, scratch, s, 0);
  for (int i = 0; i < 64; i++) {
    TEST_ASSERT_EQUAL(warn, f.pixels[i]);
    TEST_ASSERT_EQUAL(warn, f.pixels[63 * 64 + i]);
  }
  // After the ETA countdown the panel holds the marked-site view
  // (TARGET CONFIRMED): no blank gap, no static feed-lost, no red.
  for (float ph : {10.5f, 12.0f, 15.0f}) {
    s.phase = ph;
    render(f, scratch, s, 0);
    bool any_lit = false, any_red = false;
    for (auto p : f.pixels) {
      if (p != 0)
        any_lit = true;
      if (p == red)
        any_red = true;
    }
    TEST_ASSERT_TRUE(any_lit);
    TEST_ASSERT_FALSE(any_red);
  }
  s.state = SCAN;
  s.direction = 1;
  s.commAge = .1;
  render(f, scratch, s, 0);
  TEST_ASSERT_EQUAL(rgb(0xff8a24), f.pixels[0]);
  s.direction = 2;
  render(f, scratch, s, 0);
  TEST_ASSERT_EQUAL(rgb(0x32ed70), f.pixels[0]);
  s.commAge = .3;
  render(f, scratch, s, 0);
  TEST_ASSERT_EQUAL(bg, f.pixels[0]);
}
void render_every_state_and_variant() {
  node::Frame f, scratch;
  for (int st = 0; st < Count; st++)
    for (int v = 0; v < 10; v++)
      for (int mode = 0; mode < 4; mode++) {
        Scene s;
        s.state = State(st);
        s.phase = 2.5;
        s.motion = 40;
        s.launch = 1;
        s.variation = v;
        s.camera = v;
        s.sensor = mode;
        s.observations = true;
        render(f, scratch, s, 15);
        TEST_ASSERT_FALSE(f.clipped);
      }
}
void summary_tracks_aircraft_and_survives_blank_gap() {
  unsigned outcomes = 0;
  for (unsigned scenario = 0; scenario < 3; ++scenario) {
    Config c{1, 3456, 64, uint8_t(scenario), 0, true};
    for (int i = 0; i < 16; ++i) {
      Overview previous = Overview::Ready;
      for (unsigned t = 0; t < 127000; t += 100) {
        const auto frame = scene(c, t, i);
        const auto status = overview(c, t, i);
        if (frame.state == STANDBY || frame.state == APPROVED || frame.state == ORDERS)
          TEST_ASSERT_EQUAL(Overview::Ready, status);
        else if (frame.state == CHARGE) TEST_ASSERT_EQUAL(Overview::Charging, status);
        else if (frame.state == MARK)
          TEST_ASSERT_EQUAL(frame.phase < 10 ? Overview::OnMission : Overview::DOWN, status);
        else if (frame.state == CRASH)
          TEST_ASSERT_EQUAL(frame.phase < 3 ? Overview::OnMission : Overview::DOWN, status);
        else if (frame.state == EMPTY)
          TEST_ASSERT_EQUAL(frame.phase < 3 ? Overview::OnMission : Overview::MIA, status);
        else if (frame.state == NOLINK) TEST_ASSERT_EQUAL(Overview::MIA, status);
        else if (frame.state == BLANK) TEST_ASSERT_EQUAL(previous, status);
        else TEST_ASSERT_EQUAL(Overview::OnMission, status);
        previous = status;
        outcomes |= 1u << uint8_t(status);
      }
      TEST_ASSERT_EQUAL(Overview::Ready, overview(c, 127000, i));
    }
  }
  TEST_ASSERT_EQUAL(31, outcomes);
}
void ending_never_shows_kill_or_engage_names() {
  // Rescue retheme: the default scenario's endings must never produce
  // a state whose display name is KILL or ENGAGE.
  Config c{1, 3456, 64, 0, 0, true};
  for (uint32_t cycle = 0; cycle < 8; ++cycle)
    for (int i = 0; i < 16; ++i) {
      const char *n = name(ending_for(c, cycle, i));
      TEST_ASSERT_NOT_EQUAL(0, std::strcmp(n, "KILL"));
      TEST_ASSERT_NOT_EQUAL(0, std::strcmp(n, "ENGAGE"));
    }
}
void summary_resets_on_stop_wait_and_restart() {
  Runtime r; Config c{1, 3456, 64, 0, 0, true};
  TEST_ASSERT_EQUAL(Overview::Ready, r.summary(90000, 0));
  TEST_ASSERT_TRUE(r.apply(c, true, 12000, 100));
  TEST_ASSERT_EQUAL(Overview::Ready, r.summary(12099, 0));
  TEST_ASSERT_TRUE(r.apply(c, false, 0, 120000));
  TEST_ASSERT_EQUAL(Overview::Ready, r.summary(120001, 0));
  ++c.run; TEST_ASSERT_TRUE(r.apply(c, true, 0, 120002));
  TEST_ASSERT_EQUAL(Overview::Ready, r.summary(120002, 0));
  TEST_ASSERT_EQUAL(Overview::Ready, r.summary(120002+86400000u, 0));
}
int main() {
  UNITY_BEGIN();
  RUN_TEST(summary_tracks_aircraft_and_survives_blank_gap);
  RUN_TEST(summary_resets_on_stop_wait_and_restart);
  RUN_TEST(run_wrap_retry_and_stop);
  RUN_TEST(commands_are_bounded);
  RUN_TEST(launch_has_twenty_seconds_before_observations);
  RUN_TEST(variants_exhaust_the_bag);
  RUN_TEST(stop_on_completion_and_fleet_gap);
  RUN_TEST(reverse_only_loopable_states);
  RUN_TEST(countdown_and_message_borders);
  RUN_TEST(ending_never_shows_kill_or_engage_names);
  RUN_TEST(render_every_state_and_variant);
  return UNITY_END();
}
