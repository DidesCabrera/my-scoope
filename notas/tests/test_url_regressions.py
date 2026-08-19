from django.test import SimpleTestCase
from django.urls import reverse


class UrlRegressionTests(SimpleTestCase):
    def test_comparator_urls_keep_expected_names(self):
        self.assertEqual(reverse("comparator_index"), "/app/comparators/")
        self.assertEqual(reverse("food_comparator"), "/app/comparators/foods/")
        self.assertEqual(reverse("meal_comparator"), "/app/comparators/meals/")
        self.assertEqual(reverse("dailyplan_comparator"), "/app/comparators/dailyplans/")
        self.assertEqual(reverse("saved_comparisons_index"), "/app/comparators/saved/")
        self.assertEqual(
            reverse("saved_comparisons_list", kwargs={"kind": "foods"}),
            "/app/comparators/saved/foods/",
        )
        self.assertEqual(
            reverse("saved_comparison_detail", kwargs={"kind": "foods", "pk": 10}),
            "/app/comparators/saved/foods/10/",
        )
        self.assertEqual(
            reverse("saved_comparison_rename", kwargs={"kind": "foods", "pk": 10}),
            "/app/comparators/saved/foods/10/rename/",
        )

    def test_inbox_urls_keep_expected_names(self):
        self.assertEqual(reverse("inbox_list"), "/app/inbox/")
        self.assertEqual(reverse("inbox_bulk_delete"), "/app/inbox/bulk-delete/")
        self.assertEqual(
            reverse("inbox_detail", kwargs={"kind": "meal", "share_id": 7}),
            "/app/inbox/meal/7/",
        )
        self.assertEqual(
            reverse("inbox_attachment_detail", kwargs={"kind": "meal", "share_id": 7}),
            "/app/inbox/meal/7/attachment/",
        )
        self.assertEqual(
            reverse("inbox_save_attachment", kwargs={"kind": "meal", "share_id": 7}),
            "/app/inbox/meal/7/save/",
        )
        self.assertEqual(
            reverse("inbox_toggle_favorite", kwargs={"kind": "meal", "share_id": 7}),
            "/app/inbox/meal/7/favorite/",
        )

    def test_primary_library_urls_keep_expected_names(self):
        self.assertEqual(reverse("food_list"), "/app/foods/")
        self.assertEqual(reverse("food_create"), "/app/foods/create/")
        self.assertEqual(reverse("food_detail", kwargs={"pk": 3}), "/app/foods/3/")
        self.assertEqual(reverse("food_edit", kwargs={"pk": 3}), "/app/foods/3/edit/")
        self.assertEqual(reverse("food_delete", kwargs={"pk": 3}), "/app/foods/3/delete/")

        self.assertEqual(reverse("meal_list"), "/app/meals/")
        self.assertEqual(reverse("meal_create"), "/app/meals/create/")
        self.assertEqual(reverse("meal_detail", kwargs={"pk": 4}), "/app/meals/4/")
        self.assertEqual(reverse("meal_rename", kwargs={"pk": 4}), "/app/meals/4/rename/")
        self.assertEqual(reverse("meal_configure", kwargs={"pk": 4}), "/app/meals/4/configure/")

        self.assertEqual(reverse("dailyplan_list"), "/app/dailyplans/")
        self.assertEqual(reverse("dailyplan_create"), "/app/dailyplans/create/")
        self.assertEqual(reverse("dailyplan_detail", kwargs={"pk": 5}), "/app/dailyplans/5/")
        self.assertEqual(reverse("dailyplan_rename", kwargs={"pk": 5}), "/app/dailyplans/5/rename/")
        self.assertEqual(reverse("dailyplan_configure", kwargs={"pk": 5}), "/app/dailyplans/5/configure/")

    def test_program_urls_keep_expected_names(self):
        self.assertEqual(reverse("program_list"), "/app/programs/")
        self.assertEqual(reverse("program_create"), "/app/programs/create/")
        self.assertEqual(reverse("program_detail", kwargs={"pk": 8}), "/app/programs/8/")
        self.assertEqual(reverse("program_rename", kwargs={"pk": 8}), "/app/programs/8/rename/")
        self.assertEqual(reverse("configure_program", kwargs={"pk": 8}), "/app/programs/8/configure/")
        self.assertEqual(reverse("program_add_week", kwargs={"pk": 8}), "/app/programs/8/add-week/")
        self.assertEqual(
            reverse("program_duplicate_week", kwargs={"pk": 8, "week_number": 2}),
            "/app/programs/8/weeks/2/duplicate/",
        )
        self.assertEqual(
            reverse("program_remove_week", kwargs={"pk": 8, "week_number": 2}),
            "/app/programs/8/weeks/2/remove/",
        )

    def test_proposal_urls_keep_expected_names(self):
        self.assertEqual(reverse("proposal_list"), "/app/proposals/")
        self.assertEqual(reverse("proposal_detail", kwargs={"proposal_id": 9}), "/app/proposals/9/")
        self.assertEqual(reverse("proposal_entity_detail", kwargs={"proposal_id": 9}), "/app/proposals/9/entity/")
        self.assertEqual(reverse("proposal_approve", kwargs={"proposal_id": 9}), "/app/proposals/9/approve/")
        self.assertEqual(reverse("proposal_reject", kwargs={"proposal_id": 9}), "/app/proposals/9/reject/")
        self.assertEqual(reverse("proposal_apply", kwargs={"proposal_id": 9}), "/app/proposals/9/apply/")
