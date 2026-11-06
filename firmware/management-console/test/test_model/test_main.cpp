#include <unity.h>
#include "console_model.h"
#include "console_ui.h"
#include "live_policy.h"
#include "refresh_policy.h"
#include <string>
#include <vector>

using namespace flockinator;

void all_cards_and_gaps() {
    for (int i = 0; i < 16; ++i) {
        const Rect box = card_rect(i);
        TEST_ASSERT_EQUAL(i, node_at({box.x + box.w / 2, box.y + box.h / 2}));
        TEST_ASSERT_EQUAL(i, node_at({box.x, box.y}));
        TEST_ASSERT_EQUAL(i, node_at({box.x + box.w - 1, box.y + box.h - 1}));
        TEST_ASSERT_EQUAL(-1, node_at({box.x + box.w, box.y}));
        TEST_ASSERT_EQUAL(-1, node_at({box.x, box.y + box.h}));
    }
    TEST_ASSERT_EQUAL(-1, node_at({-1, 100}));
    TEST_ASSERT_EQUAL(-1, node_at({960, 100}));
    TEST_ASSERT_EQUAL(-1, node_at({100, 540}));
    TEST_ASSERT_EQUAL(-1, node_at({0, 0}));
}

void raw_touch_orientation() {
    Point p = landscape_touch(0, 0);
    TEST_ASSERT_EQUAL(0, p.x);
    TEST_ASSERT_EQUAL(539, p.y);
    p = landscape_touch(539, 959);
    TEST_ASSERT_EQUAL(959, p.x);
    TEST_ASSERT_EQUAL(0, p.y);
    TEST_ASSERT_FALSE(landscape_touch(-1, 50).valid());
    TEST_ASSERT_FALSE(landscape_touch(540, 50).valid());
    TEST_ASSERT_FALSE(landscape_touch(50, 960).valid());
}

void stale_and_unknown_are_distinct() {
    Node n{1, Health::Healthy, false, 10};
    TEST_ASSERT_EQUAL(Health::Unknown, health_at(n, 100000));
    n.observed = true;
    TEST_ASSERT_EQUAL(Health::Healthy, health_at(n, 30009));
    TEST_ASSERT_EQUAL(Health::Stale, health_at(n, 30010));
    TEST_ASSERT_EQUAL(Health::Offline, health_at(n, 90010));
    n.health = Health::Offline;
    TEST_ASSERT_EQUAL(Health::Offline, health_at(n, 30010));
    n.health = Health::Warning;
    TEST_ASSERT_EQUAL(Health::Warning, health_at(n, 11));
    TEST_ASSERT_EQUAL(Health::Stale, health_at(n, 30010));
}

void intervals_survive_wraparound() {
    Node n{1, Health::Healthy, true, 0xFFFFFF00U};
    TEST_ASSERT_EQUAL(Health::Healthy, health_at(n, 0x00000100U));
    TEST_ASSERT_EQUAL(Health::Stale, health_at(n, 0x00007530U));
}

void navigation_requires_explicit_deploy() {
    Console c;
    TEST_ASSERT_EQUAL(Page::Diagnostics, c.page);
    const Rect home = button_rect(0);
    TEST_ASSERT_EQUAL(Action::Redraw, c.tap({home.x + 2, home.y + 2}));
    TEST_ASSERT_EQUAL(Page::Overview, c.page);
    for (int i = 0; i < 16; ++i) {
        c.page = Page::Overview;
        const Rect box = card_rect(i);
        TEST_ASSERT_EQUAL(Action::Redraw, c.tap({box.x + 2, box.y + 2}));
        TEST_ASSERT_EQUAL(Page::Detail, c.page);
        TEST_ASSERT_EQUAL(i, c.selected);
        TEST_ASSERT_TRUE(c.can_send_node_commands());
    }
    TEST_ASSERT_EQUAL(Action::Deploy, c.tap({40,400}));
    TEST_ASSERT_EQUAL(Action::None, c.tap({-1, -1}));
    TEST_ASSERT_TRUE(c.can_send_node_commands());
}

void toolbar_and_sleep_transitions() {
    Console c;
    for (int i = 0; i < 4; ++i) {
        const Rect button = button_rect(i);
        TEST_ASSERT_EQUAL(i == 3 ? Action::Refresh : Action::Redraw, c.tap({button.x, button.y}));
        c.page = Page::Overview; // Alignment deliberately records touches in blank space.
        TEST_ASSERT_EQUAL(Action::None, c.tap({button.x + button.w, button.y}));
    }
    const Rect sleep = button_rect(4);
    TEST_ASSERT_EQUAL(Action::Sleep, c.tap({sleep.x + 10, sleep.y + 10}));
    TEST_ASSERT_EQUAL(Page::Sleeping, c.page);
    TEST_ASSERT_EQUAL(Action::None, c.tap({26, 464}));
    TEST_ASSERT_FALSE(c.can_send_node_commands());
}

struct RecordingCanvas {
    std::vector<std::string> strings;
    bool in_bounds = true;
    int card_count = 0;
    void rect(Rect r, bool, uint8_t = 0) {
        in_bounds &= r.x >= 0 && r.y >= 0 && r.x + r.w <= 960 && r.y + r.h <= 540;
        if (r.w == 218 && r.h == 70) ++card_count;
    }
    void text(int x, int y, const char* value, int = 18) {
        in_bounds &= x >= 0 && y >= 0 && x < 960 && y < 540;
        strings.emplace_back(value);
    }
    bool has(const char* needle) const {
        for (const auto& s : strings) if (s.find(needle) != std::string::npos) return true;
        return false;
    }
};

void rendered_pages_retain_live_and_diagnostics() {
    Console c;
    Diagnostics d;
    const auto nodes = demo_nodes();
    for (Page page : {Page::Overview, Page::Detail, Page::Diagnostics, Page::Alignment, Page::Sleeping}) {
        c.page = page;
        RecordingCanvas canvas;
        draw_console(canvas, c, d, nodes, kDemoNow);
        TEST_ASSERT_TRUE(canvas.in_bounds);
        TEST_ASSERT_TRUE(canvas.has("LIVE"));
        if (page == Page::Overview) {
            TEST_ASSERT_EQUAL(16, canvas.card_count);
            TEST_ASSERT_TRUE(canvas.has("Unknown"));
            TEST_ASSERT_TRUE(canvas.has("Offline"));
        }
        if (page == Page::Diagnostics) {
            TEST_ASSERT_TRUE(canvas.has("SD mount failed"));
            TEST_ASSERT_TRUE(canvas.has("unverified"));
        }
        if (page == Page::Sleeping) TEST_ASSERT_TRUE(canvas.has("status frozen"));
    }
}

void image_paths_cannot_escape_or_replace_staging() {
    TEST_ASSERT_TRUE(valid_image_name("node-0.4.1.bin"));
    TEST_ASSERT_FALSE(valid_image_name("../other.bin"));
    TEST_ASSERT_FALSE(valid_image_name(".upload.tmp"));
    TEST_ASSERT_FALSE(valid_image_name("sub/file.bin"));
    TEST_ASSERT_FALSE(valid_image_name(""));
    TEST_ASSERT_FALSE(valid_image_name(std::string(65,'a').c_str()));
}
void health_requires_fresh_single_pending_challenge() {
    uint8_t nonce[16]={1},other[16]={2};
    TEST_ASSERT_TRUE(expected_health(true,200,100,5,5,nonce,nonce));
    TEST_ASSERT_FALSE(expected_health(false,200,100,5,5,nonce,nonce));
    TEST_ASSERT_FALSE(expected_health(true,4101,100,5,5,nonce,nonce));
    TEST_ASSERT_FALSE(expected_health(true,200,100,4,5,nonce,nonce));
    TEST_ASSERT_FALSE(expected_health(true,200,100,5,5,nonce,other));
    TEST_ASSERT_TRUE(expected_health(true,0x10,0xfffffff0,5,5,nonce,nonce));
}
void verification_requires_new_valid_boot_and_expected_image() {
    uint8_t image[32]={1},other[32]={2};
    TEST_ASSERT_TRUE(valid_deployment_boot(8,9,2,1,true,image,image));
    TEST_ASSERT_FALSE(valid_deployment_boot(8,8,2,1,true,image,image));
    TEST_ASSERT_FALSE(valid_deployment_boot(8,9,1,1,true,image,image));
    TEST_ASSERT_FALSE(valid_deployment_boot(8,9,2,0,true,image,image));
    TEST_ASSERT_FALSE(valid_deployment_boot(8,9,2,1,false,image,image));
    TEST_ASSERT_FALSE(valid_deployment_boot(8,9,2,1,true,image,other));
}

void erase_wait_has_bounded_longer_deadline() {
    TEST_ASSERT_FALSE(reply_timed_out(true,59999,0));
    TEST_ASSERT_TRUE(reply_timed_out(true,60000,0));
    TEST_ASSERT_FALSE(reply_timed_out(false,3999,0));
    TEST_ASSERT_TRUE(reply_timed_out(false,4000,0));
    const uint32_t start=0xfffffff0U;
    TEST_ASSERT_FALSE(reply_timed_out(true,start+59999U,start));
    TEST_ASSERT_TRUE(reply_timed_out(true,start+60000U,start));
}

void selection_requires_idle_storage_and_confined_filename() {
    TEST_ASSERT_TRUE(may_select_image(true,false,false,"known-good.bin"));
    TEST_ASSERT_FALSE(may_select_image(true,true,false,"known-good.bin"));
    TEST_ASSERT_FALSE(may_select_image(true,false,true,"known-good.bin"));
    TEST_ASSERT_FALSE(may_select_image(false,false,false,"known-good.bin"));
    TEST_ASSERT_FALSE(may_select_image(true,false,false,"../other.bin"));
}

void automatic_refresh_depends_on_displayed_pixels() {
    uint8_t pixels[16]{};
    RefreshPolicy refresh;
    const uint64_t initial = framebuffer_fingerprint(pixels, sizeof(pixels));
    TEST_ASSERT_TRUE(refresh.needs_refresh(initial, false, false));
    refresh.did_refresh(initial);
    TEST_ASSERT_FALSE(refresh.needs_refresh(framebuffer_fingerprint(pixels,sizeof(pixels)), false, false));
    pixels[7] = 1; // One changed pixel must make the automatic frame eligible.
    const uint64_t changed = framebuffer_fingerprint(pixels,sizeof(pixels));
    TEST_ASSERT_TRUE(refresh.needs_refresh(changed, false, false));
    // Merely drawing a candidate does not change what the panel has displayed.
    TEST_ASSERT_FALSE(refresh.needs_refresh(initial, false, false));
    refresh.did_refresh(changed);
    TEST_ASSERT_FALSE(refresh.needs_refresh(changed, false, false));
}
void manual_and_sleep_refresh_bypass_unchanged_pixel_suppression() {
    RefreshPolicy refresh;
    refresh.did_refresh(0);
    TEST_ASSERT_FALSE(refresh.needs_refresh(0, false, false));
    TEST_ASSERT_TRUE(refresh.needs_refresh(0, true, false));
    TEST_ASSERT_TRUE(refresh.needs_refresh(0, false, true));
    TEST_ASSERT_TRUE(refresh.needs_refresh(0, true, true));
}

void observation_clock_is_sampled_after_concurrent_snapshot_capture() {
    uint32_t clock = 1000;
    Node latest{1, Health::Healthy, true, 999};
    Health rendered = Health::Unknown;
    render_latest_snapshot([&] {
        latest.last_seen_ms = 1001; // Radio updates after the loop sampled 1000.
        clock = 1002;
        return latest;
    }, [&] { return clock; }, [&](const Node& node, uint32_t sampled) {
        rendered = health_at(node, sampled);
        TEST_ASSERT_EQUAL_UINT32(1002, sampled);
    });
    TEST_ASSERT_EQUAL(Health::Healthy, rendered);
    // This is the old call order's exact failure, not a real offline observation.
    TEST_ASSERT_EQUAL(Health::Offline, health_at(latest, 1000));
}
void coherent_snapshot_clock_preserves_millis_wraparound() {
    uint32_t clock = 0xfffffff0U;
    Node latest{1, Health::Healthy, true, 0xffffffe0U};
    render_latest_snapshot([&] { clock = 0x10; return latest; },
        [&] { return clock; }, [&](const Node& node, uint32_t sampled) {
            TEST_ASSERT_EQUAL(Health::Healthy, health_at(node, sampled));
            TEST_ASSERT_EQUAL_UINT32(48, sampled - node.last_seen_ms);
        });
}

void mission_controls_require_explicit_launch() {
    Console c;auto button=button_rect(2);TEST_ASSERT_EQUAL(Action::Redraw,c.tap({button.x+2,button.y+2}));TEST_ASSERT_EQUAL(Page::Missions,c.page);
    TEST_ASSERT_EQUAL(Action::Redraw,c.tap({30,140}));TEST_ASSERT_EQUAL(1,c.draft.scenario);
    TEST_ASSERT_EQUAL(Action::Redraw,c.tap({30,210}));TEST_ASSERT_EQUAL(1,c.draft.goal);
    TEST_ASSERT_EQUAL(Action::Redraw,c.tap({30,280}));TEST_ASSERT_EQUAL(96,c.draft.seconds);
    TEST_ASSERT_EQUAL(Action::Redraw,c.tap({320,280}));TEST_ASSERT_FALSE(c.draft.repeat);
    TEST_ASSERT_EQUAL(Action::MissionStart,c.tap({30,400}));TEST_ASSERT_EQUAL(Action::MissionStop,c.tap({320,400}));
    TEST_ASSERT_EQUAL(Action::None,c.tap({600,400}));
}
void simulation_does_not_mask_stale_health() {
    Console c;c.page=Page::Overview;auto nodes=demo_nodes();nodes[0].mission_capable=true;nodes[0].mission_state=recon::CRASH;nodes[0].last_seen_ms=0;
    RecordingCanvas canvas;draw_console(canvas,c,Diagnostics{},nodes,120000);TEST_ASSERT_FALSE(canvas.has("CRASH"));TEST_ASSERT_TRUE(canvas.has("--"));TEST_ASSERT_TRUE(canvas.has("Offline"));
    c.page=Page::Missions;RecordingCanvas mission;draw_console(mission,c,Diagnostics{},nodes,120000,"Idle","","Launch sent",42,true);TEST_ASSERT_TRUE(mission.in_bounds);TEST_ASSERT_TRUE(mission.has("Confirmed: 0 / 16"));
}
void overview_requires_fresh_authoritative_status() {
    Node n{1, Health::Healthy, true, 100}; n.mission_capable=true;
    TEST_ASSERT_EQUAL_STRING("--", overview_label(n, 101));
    n.mission_overview=recon::decode_overview(1,2);
    TEST_ASSERT_EQUAL_STRING("DOWN", overview_label(n, 6099));
    TEST_ASSERT_EQUAL_STRING("--", overview_label(n, 6100));
    TEST_ASSERT_EQUAL(Health::Stale,overview_health(n,6100));
    n.last_seen_ms=6200;
    TEST_ASSERT_EQUAL_STRING("DOWN", overview_label(n,6201));
    n.mission_overview=recon::decode_overview(2,0);
    TEST_ASSERT_EQUAL_STRING("--", overview_label(n,6201));
    TEST_ASSERT_EQUAL(recon::Overview::Unknown,recon::decode_overview(1,5));
    n.mission_overview=recon::Overview::Ready;n.observed=false;
    TEST_ASSERT_EQUAL_STRING("--", overview_label(n,6201));
    n.observed=true;n.last_seen_ms=0xffffff00u;
    TEST_ASSERT_EQUAL_STRING("READY",overview_label(n,0x10));
}
void overview_does_not_redraw_for_animation_or_fresh_heartbeats() {
    Console c;c.page=Page::Overview;auto nodes=demo_nodes();
    for(auto& n:nodes){n.observed=true;n.health=Health::Healthy;n.last_seen_ms=120000;n.mission_capable=true;n.mission_overview=recon::Overview::OnMission;}
    RecordingCanvas first,second;
    draw_console(first,c,Diagnostics{},nodes,120100,"OTA detail");
    for(auto& n:nodes){n.last_seen_ms=121000;n.mission_state=recon::SHARE;}
    draw_console(second,c,Diagnostics{},nodes,121100,"Different OTA detail");
    TEST_ASSERT_TRUE(first.strings==second.strings);
    TEST_ASSERT_FALSE(first.has("OTA detail"));
    TEST_ASSERT_TRUE(first.has("OM"));
}
void health_retries_are_bounded_and_wrap_safe() {
    TEST_ASSERT_TRUE(health_retry_due(true,0,600,100,100));
    TEST_ASSERT_FALSE(health_retry_due(true,0,599,100,100));
    TEST_ASSERT_TRUE(health_retry_due(true,1,1100,100,600));
    TEST_ASSERT_FALSE(health_retry_due(true,2,1600,100,1100));
    TEST_ASSERT_FALSE(health_retry_due(false,0,600,100,100));
    TEST_ASSERT_FALSE(health_retry_due(true,0,1900,100,100));
    TEST_ASSERT_TRUE(health_retry_due(true,0,0x110,0xffffff10,0xffffff10));
}
int main() {
    UNITY_BEGIN();
    RUN_TEST(health_retries_are_bounded_and_wrap_safe);
    RUN_TEST(overview_requires_fresh_authoritative_status);
    RUN_TEST(overview_does_not_redraw_for_animation_or_fresh_heartbeats);
    RUN_TEST(mission_controls_require_explicit_launch);
    RUN_TEST(simulation_does_not_mask_stale_health);
    RUN_TEST(observation_clock_is_sampled_after_concurrent_snapshot_capture);
    RUN_TEST(coherent_snapshot_clock_preserves_millis_wraparound);
    RUN_TEST(automatic_refresh_depends_on_displayed_pixels);
    RUN_TEST(manual_and_sleep_refresh_bypass_unchanged_pixel_suppression);
    RUN_TEST(selection_requires_idle_storage_and_confined_filename);
    RUN_TEST(erase_wait_has_bounded_longer_deadline);
    RUN_TEST(image_paths_cannot_escape_or_replace_staging);
    RUN_TEST(health_requires_fresh_single_pending_challenge);
    RUN_TEST(verification_requires_new_valid_boot_and_expected_image);
    RUN_TEST(all_cards_and_gaps);
    RUN_TEST(raw_touch_orientation);
    RUN_TEST(stale_and_unknown_are_distinct);
    RUN_TEST(intervals_survive_wraparound);
    RUN_TEST(navigation_requires_explicit_deploy);
    RUN_TEST(toolbar_and_sleep_transitions);
    RUN_TEST(rendered_pages_retain_live_and_diagnostics);
    return UNITY_END();
}
