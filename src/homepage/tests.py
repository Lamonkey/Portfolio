from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectCost


class ProjectCostModelTests(TestCase):
    def test_monthly_amount_passes_through_for_monthly(self):
        cost = ProjectCost(label="Dyno", amount=Decimal("5.00"), cadence=ProjectCost.MONTHLY)
        self.assertEqual(cost.monthly_amount, Decimal("5.00"))

    def test_monthly_amount_divides_yearly_by_twelve(self):
        cost = ProjectCost(label="Domain", amount=Decimal("12.00"), cadence=ProjectCost.YEARLY)
        self.assertEqual(cost.monthly_amount, Decimal("1.00"))


class BudgetDashboardTests(TestCase):
    def setUp(self):
        self.url = reverse("homepage:budget-dashboard")
        self.p1 = Project.objects.create(title="Flashcard app", type="mvp")
        self.p2 = Project.objects.create(title="Budget tracker", type="mvp")
        ProjectCost.objects.create(project=self.p1, label="Heroku Eco dynos", provider="Heroku", amount="5.00")
        ProjectCost.objects.create(project=self.p1, label="Postgres Essential-0", provider="Heroku", amount="5.00")
        ProjectCost.objects.create(
            project=self.p2, label="Domain", provider="Namecheap", amount="12.00", cadence=ProjectCost.YEARLY
        )
        ProjectCost.objects.create(project=None, label="Shared Neon Postgres", provider="Neon", amount="3.00")
        # Inactive cost must be excluded from every rollup.
        ProjectCost.objects.create(project=self.p2, label="cancelled", provider="Heroku", amount="99.00", is_active=False)

    def test_dashboard_is_private(self):
        """Anonymous users are redirected to the admin login, not served the page."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login", resp["Location"])

    def test_staff_sees_totals_and_rollups(self):
        staff = User.objects.create_user("staff", password="pw", is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

        # 5 + 5 + (12/12=1) + 3 = 14.00; inactive 99 excluded.
        self.assertEqual(resp.context["monthly_total"], Decimal("14.00"))
        self.assertEqual(resp.context["yearly_total"], Decimal("168.00"))
        self.assertEqual(resp.context["active_count"], 4)

        # Project groups sorted by spend descending.
        groups = resp.context["project_groups"]
        self.assertEqual([g["title"] for g in groups], ["Flashcard app", "Budget tracker"])
        self.assertEqual(groups[0]["monthly_total"], Decimal("10.00"))

        # Shared / overhead bucket holds the project-less cost.
        self.assertEqual(resp.context["shared_group"]["monthly_total"], Decimal("3.00"))

        # Inactive cost never reaches the page.
        self.assertNotContains(resp, "cancelled")
