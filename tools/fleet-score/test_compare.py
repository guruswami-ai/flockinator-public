import unittest

from compare import compare


def row(seed, *, contacts=10, recall=0.2, mislabelled=1, discoveries=10,
        enemy_as_friendly=0, energy=0.04, units=16, landed_home=None,
        violations=0):
    return {
        "seed": seed,
        "contacts_total": contacts,
        "units": units,
        "recall": recall,
        "mislabelled": mislabelled,
        "discoveries": discoveries,
        "mislabelled_enemy_as_friendly": enemy_as_friendly,
        "discoveries_per_energy": energy,
        "units_landed_home": units if landed_home is None else landed_home,
        "reserve_floor_violations": violations,
    }


def payload(rows):
    return {"per_seed": rows}


class CompareTest(unittest.TestCase):
    def test_dev_pass_and_zero_contact_exclusion(self):
        baseline = [row(seed) for seed in range(16)]
        baseline += [row(seed, contacts=0, recall=None, discoveries=0,
                         mislabelled=0) for seed in range(16, 20)]
        candidate = [row(seed, recall=0.4) for seed in range(16)]
        candidate += [row(seed, contacts=0, recall=None, discoveries=0,
                          mislabelled=0) for seed in range(16, 20)]

        result = compare(payload(baseline), payload(candidate), "dev")

        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["values"]["eligible_seed_count"], 16)
        self.assertEqual(result["values"]["non_worse_seeds"], 16)

    def test_enemy_as_friendly_rate_fails_gate(self):
        baseline = [row(seed, enemy_as_friendly=1) for seed in range(16)]
        candidate = [row(seed, recall=0.4, enemy_as_friendly=2)
                     for seed in range(16)]

        result = compare(payload(baseline), payload(candidate), "dev")

        self.assertFalse(result["all_gates_pass"])
        self.assertFalse(
            result["gates"]["3_pooled_mislabel_rates_not_worse"])


if __name__ == "__main__":
    unittest.main()
