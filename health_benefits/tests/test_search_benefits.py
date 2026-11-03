import unittest

from health_benefits.recommendation.search_benefits import extract_benefits, region_info


class SearchBenefitsTests(unittest.TestCase):
    def row(self, **changes):
        return dict(dict(id=1, source="central", life_cycle_names=["청년"],
                         target_group_names=["장애인"], provider_province="전국",
                         provider_municipality=None), **changes)

    def test_null_preserved_and_not_all_ages(self):
        row = self.row(life_cycle_names=None, target_group_names=None)
        result = extract_benefits([row], life_cycles=["청년"])
        self.assertEqual(result["matched"], [])
        item = result["needs_review"][0]
        self.assertIsNone(item["life_cycle_names"])
        self.assertEqual(item["display"]["life_cycle"], "대상 원문 확인")
        self.assertEqual(item["display"]["target_group"], "대상 원문 확인")
        self.assertNotIn("display", row)

    def test_central_null_region_is_unknown(self):
        row = self.row(provider_province=None)
        self.assertEqual(region_info(row)[0], "unknown")
        self.assertEqual(len(extract_benefits([row], province="전국")["needs_review"]), 1)

    def test_explicit_nationwide_matches_local_selection(self):
        self.assertEqual(len(extract_benefits([self.row()], province="서울특별시")["matched"]), 1)

    def test_known_mismatch_excluded_even_with_null(self):
        row = self.row(life_cycle_names=["노년"], target_group_names=None)
        result = extract_benefits([row], ["청년"], ["장애인"])
        self.assertEqual(result, {"matched": [], "needs_review": []})

    def test_or_within_and_across_dimensions(self):
        result = extract_benefits([self.row()], ["아동", "청년"], ["장애인"])
        self.assertEqual(len(result["matched"]), 1)
        self.assertEqual(extract_benefits([self.row()], ["청년"], ["다문화"])["matched"], [])

    def test_unfiltered_keeps_missing_with_review_labels(self):
        row = self.row(life_cycle_names=None, provider_province=None)
        item = extract_benefits([row])["matched"][0]
        self.assertEqual(item["display"]["region"], "대상 원문 확인")

    def test_empty_array_is_unknown_and_explicit_all_matches(self):
        for value in (None, [], [" "]):
            self.assertEqual(len(extract_benefits([self.row(target_group_names=value)],
                                                 target_groups=["장애인"])["needs_review"]), 1)
        self.assertEqual(len(extract_benefits([self.row(life_cycle_names=["전체"])],
                                             life_cycles=["노년"])["matched"]), 1)

    def test_municipality_missing_is_not_province_wide(self):
        row = self.row(provider_province="서울특별시")
        self.assertEqual(len(extract_benefits([row], province="서울특별시",
                                             municipality="강남구")["needs_review"]), 1)
        self.assertEqual(extract_benefits([row], province="부산광역시")["needs_review"], [])
        with self.assertRaises(ValueError):
            extract_benefits([row], municipality="강남구")


if __name__ == "__main__":
    unittest.main()
