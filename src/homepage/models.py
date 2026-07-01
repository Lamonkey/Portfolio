from django.db import models
import markdown


def render_markdown(raw_text):
    text = (raw_text or "").strip()

    # If the entire document was pasted as one fenced block, unwrap it.
    if text.startswith("```") and text.endswith("```"):
        parts = text.splitlines()
        if len(parts) >= 2:
            text = "\n".join(parts[1:-1]).strip()

    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
    )


class Project(models.Model):
    title = models.CharField(max_length=64)
    subtitle = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Short one-liner describing what this project is. Shown on the list page card.",
    )
    description = models.TextField(default=None, blank=True, null=True)
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text=(
            "SEO meta description used in <meta name=\"description\"> and og:description. "
            "Aim for 120-160 chars. Falls back to subtitle, then to a truncated description."
        ),
    )
    link = models.TextField(default=None, blank=True, null=True)
    github_link = models.TextField(default=None, blank=True, null=True)
    image = models.ImageField(
        upload_to="media/",
        height_field=None,
        width_field=None,
        max_length=None)
    type = models.CharField(max_length=64, blank=True)

    def toDict(self):
        return {'title': self.title.title(),
                'description': render_markdown(self.description),
                'github_link': self.github_link,
                'link': self.link, 'image': self.image.url,
                'type': self.type.split(" ")}

    def __str__(self):
        return f"{self.title}"


class ProjectCost(models.Model):
    """A single recurring cost line for the private budget dashboard.

    One row per billed thing — e.g. "Heroku Eco dynos" ($5/mo),
    "Postgres Essential-0" ($5/mo), "AWS S3" ($1/mo). This is operational
    data for the site owner only; it is never shown on the public site.

    ``project`` is nullable on purpose: a cost that isn't tied to a single
    project (a database or box shared across several MVPs, an account-level
    subscription) is recorded with ``project=None`` and rolled up under a
    "Shared / overhead" bucket on the dashboard.
    """

    MONTHLY = "monthly"
    YEARLY = "yearly"
    CADENCE_CHOICES = [
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    project = models.ForeignKey(
        "Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="costs",
        help_text=(
            "The project this cost belongs to. Leave blank for a shared cost "
            "(e.g. a database used across several projects, or an "
            "account-level subscription)."
        ),
    )
    label = models.CharField(
        max_length=120,
        help_text="What the charge is, e.g. 'Heroku Eco dynos' or 'Postgres Essential-0'.",
    )
    provider = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text="Who bills you, e.g. 'Heroku', 'Neon', 'AWS'. Used for per-provider totals.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The charge per billing period (see cadence). Use the currency you think in.",
    )
    cadence = models.CharField(
        max_length=10,
        choices=CADENCE_CHOICES,
        default=MONTHLY,
        help_text="How often you're billed. Yearly charges are divided by 12 for the monthly rollup.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck when you cancel a charge. Inactive costs drop out of the totals but stay for history.",
    )
    notes = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Optional reminder, e.g. 'move to Neon free tier' or 'renews in March'.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__title", "-amount"]
        verbose_name = "Project cost"
        verbose_name_plural = "Project costs"

    @property
    def monthly_amount(self):
        """Cost normalized to a per-month figure, for apples-to-apples totals."""
        from decimal import Decimal

        if self.cadence == self.YEARLY:
            return (self.amount / Decimal(12)).quantize(Decimal("0.01"))
        return self.amount

    def __str__(self):
        where = self.project.title if self.project_id else "Shared"
        return f"{where} · {self.label} ({self.amount}/{self.cadence})"


class BlogPost(models.Model):
    """A casual blog post on jchen42.com/blog/.

    The site owner's "post whatever" channel — quick, raw, frequent.
    More polished long-form continues to live on Medium / Substack and is
    linked from elsewhere on the portfolio.
    """

    title = models.CharField(max_length=140)
    slug = models.SlugField(
        max_length=160,
        unique=True,
        blank=True,
        help_text="Auto-generated from title on first save if left blank.",
    )
    subtitle = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Short one-liner shown on the list-page card.",
    )
    content_markdown = models.TextField(
        blank=True,
        default="",
        help_text="The post body, written in Markdown.",
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text=(
            "SEO meta description used in <meta name=\"description\"> and og:description. "
            "Aim for 120-160 chars. Falls back to subtitle, then to a truncated body."
        ),
    )
    published = models.BooleanField(
        default=True,
        help_text="If False, the post is a draft — hidden from the public list and 404s on the detail page.",
    )
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Defaults to first publication time. Hand-edit to reorder.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    @property
    def content_html(self) -> str:
        return render_markdown(self.content_markdown)

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        from django.utils import timezone

        if not self.slug:
            base = slugify(self.title) or "post"
            slug = base
            i = 2
            # Resolve collisions deterministically by appending -2, -3, …
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        if self.published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class LandingPage(models.Model):
    """Editable content for the site's landing page (jchen42.com/).

    Treated as a singleton — edit the single row in admin to curate the
    intro, photo, and the featured project / post shown on the home page.
    """

    name = models.CharField(max_length=120, default="Jesse Chen")
    headline = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Short tagline shown under the name, e.g. 'Software engineer building in public'.",
    )
    intro_markdown = models.TextField(
        blank=True,
        default="",
        help_text="A short bio / introduction, written in Markdown.",
    )
    photo = models.ImageField(
        upload_to="media/landing/",
        blank=True,
        null=True,
        help_text="A photo of you. Upload here; shown in the landing hero.",
    )

    # Section headings on the landing page. What appears under each section is
    # controlled by the FeaturedItem table below, not by fields here.
    project_section_title = models.CharField(
        max_length=80,
        default="Currently building",
        help_text="Heading above the featured projects.",
    )
    post_section_title = models.CharField(
        max_length=80,
        default="Latest writing",
        help_text="Heading above the featured writing.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Landing page"
        verbose_name_plural = "Landing page"

    @property
    def intro_html(self) -> str:
        return render_markdown(self.intro_markdown)

    def __str__(self) -> str:
        return f"Landing page ({self.name})"


class FeaturedItem(models.Model):
    """A single row on the landing page's "featured" table.

    Each row spotlights EITHER a project OR a blog post. The set of active
    rows — and their order — is what the landing page renders. Add, reorder,
    or toggle rows in admin like a little newspaper layout table.
    """

    project = models.ForeignKey(
        "Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="Feature a project. Leave blank if this row features a post.",
    )
    post = models.ForeignKey(
        "BlogPost",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="Feature a blog post. Leave blank if this row features a project.",
    )
    note = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Optional blurb shown instead of the item's own subtitle/summary.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers show first.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this row without deleting it.",
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Featured item"
        verbose_name_plural = "Featured items"

    def clean(self):
        from django.core.exceptions import ValidationError

        if bool(self.project_id) == bool(self.post_id):
            raise ValidationError("Choose exactly one: a project OR a post (not both, not neither).")

    @property
    def is_project(self) -> bool:
        return self.project_id is not None

    def __str__(self) -> str:
        target = self.project or self.post
        kind = "Project" if self.is_project else "Post"
        return f"#{self.order} · {kind}: {target}" if target else f"#{self.order} · (empty)"


class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=120, default="Privacy Policy")
    slug = models.SlugField(unique=True)
    content_markdown = models.TextField(help_text="Privacy policy content in Markdown.")
    projects = models.ManyToManyField(Project, blank=True, related_name="privacy_policies")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def content_html(self):
        return render_markdown(self.content_markdown)

    def __str__(self):
        return self.title
