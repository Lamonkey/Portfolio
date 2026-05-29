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
