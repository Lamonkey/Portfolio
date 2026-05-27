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
