from kulira_core.operations import (STRATEGIES, pareto_frontier,
                                    run_operation, run_operations)


def test_deterministic_same_seed():
    a = run_operation(3, "K8")
    b = run_operation(3, "K8")
    assert a == b


def test_all_strategies_bounded():
    for name in STRATEGIES:
        r = run_operation(1, name)
        assert 0 <= r["found"] <= 4
        assert 0 <= r["ready_end"] <= 16
        assert r["lost"] <= 16


def test_more_aircraft_find_faster_on_average():
    agg = run_operations(range(20))
    assert agg["K16"]["find_rate"] >= agg["K1"]["find_rate"]
    assert agg["K16"]["mean_find_turns"] <= agg["K1"]["mean_find_turns"]


def test_perfect_detection_finds_every_attempted_incident():
    r = run_operation(5, "K16", p_detect=1.0, p_fail=0.0)
    assert r["found"] == r["attempted"] and r["attempted"] > 0


def test_pareto_frontier_nonempty_and_valid():
    agg = run_operations(range(10))
    front = pareto_frontier(agg)
    assert front and set(front) <= set(STRATEGIES)


def test_escalation_differs_from_fixed_small():
    a = run_operation(2, "ESC")
    b = run_operation(2, "K4")
    assert a["strategy"] != b["strategy"]


BINDING = dict(incidents=8, daylight_turns=160, recharge=4, ground_rest=True)


def test_binding_regime_is_deterministic():
    assert run_operation(21, "K14", **BINDING) == run_operation(21, "K14", **BINDING)


def test_binding_regime_records_readiness_metrics():
    r = run_operation(21, "ESC", **BINDING)
    assert r["ready_before_2nd"] is not None
    assert r["attempted"] + r["unattempted"] == 8
