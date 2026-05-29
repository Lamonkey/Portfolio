from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags
from django.utils.text import slugify

from .models import BlogPost, PrivacyPolicy, Project, render_markdown


def index(request):

    # getting raw label
    raw_labels = [x.type for x in Project.objects.all()]

    # split label based on space
    labels = []
    for label in raw_labels:
        tmp_labels = label.split(" ")
        for tmp_label in tmp_labels:
            labels.append(tmp_label)

    # split title lable, remove _
    labels = [((" ").join(label.split("_"))).title() for label in labels]
    labels = set(labels)
    labels_pair = []

    # convert label to (label,raw label)
    for label in labels:
        labels_pair.append((label, convert_label(label)))
    project_list = [project.toDict() for project in Project.objects.all()]
    return render(request, "homepage/index.html", {
        # send unique labels only
        "labels": labels_pair,
        "project_json": project_list,

    })


def convert_label(label):
    raw_label = label.lower()
    raw_label = raw_label.split(" ")
    raw_label = "_".join(raw_label)
    return raw_label


def writing_room(request):

    featured_story = {
        "title": "A Year of Building in Public",
        "summary": (
            "Notes on learning loudly, framing experiments like products, and why "
            "shipping weekly retros turned into my best accountability hack."
        ),
        "link": "https://medium.com/@jchen42",
        "reading_time": "8 min read",
    }

    writing_collections = [
        {
            "title": "Systems & Craft",
            "summary": "Architecture sketches, backend scaling stories, and the tooling I keep rebuilding.",
            "topics": ["Django", "Observability", "Infra notes"],
            "link": "https://medium.com/@jchen42",
        },
        {
            "title": "Learning Logs",
            "summary": "Tighter, more personal reflections on conferences, books, and lessons shipped from side quests.",
            "topics": ["Book notes", "Conferences", "Career"],
            "link": "https://medium.com/@jchen42",
        },
        {
            "title": "Play Projects",
            "summary": "Tiny experiments, browser toys, and prototypes that make it out of the notebook.",
            "topics": ["Creative coding", "Game dev", "Automation"],
            "link": "https://medium.com/@jchen42",
        },
    ]

    notebook_entries = [
        {
            "label": "Now",
            "title": "Serializing my week",
            "detail": "Tracking small wins to keep long projects honest.",
        },
        {
            "label": "Next",
            "title": "Interviewing domain experts",
            "detail": "Collecting prompts from indie hackers about audience building.",
        },
        {
            "label": "Later",
            "title": "Publishing a field guide",
            "detail": "Packaging the best writing workflows into a repeatable kit.",
        },
    ]

    encryption_steps = [
        {
            "title": "Grab the key",
            "detail": "Copy my public key or import it with your preferred GPG tool.",
        },
        {
            "title": "Encrypt your note",
            "detail": "`gpg --encrypt --armor --recipient jessechen note.txt` is a quick start.",
        },
        {
            "title": "Send it over",
            "detail": "Drop the ciphertext via email or even a GitHub issue—I'll reply in kind.",
        },
    ]

    pgp_public_key = (
        "-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
        "Version: Replace with your real public key\n\n"
        "xsBNBGSampleABCDEF12345ExampleFakeKeyDataExampleFakeKeyData\n"
        "=SIGN\n"
        "-----END PGP PUBLIC KEY BLOCK-----"
    )

    return render(request, "homepage/writing_room.html", {
        "featured_story": featured_story,
        "writing_collections": writing_collections,
        "notebook_entries": notebook_entries,
        "encryption_steps": encryption_steps,
        "pgp_public_key": pgp_public_key,
    })


def software_log(request):
    entries = _build_project_entries()
    return render(request, "homepage/software_log.html", {
        "entries": entries,
        "page_title": "Projects",
        "page_description": "Projects I've shipped, with build notes, links, and the tech stack that powered them."
    })


def software_log_detail(request, slug):
    entries = _build_project_entries()
    entry = next((entry for entry in entries if entry["slug"] == slug), None)
    if not entry:
        raise Http404("Project not found")

    return render(request, "homepage/software_log_detail.html", {
        "entry": entry,
    })


def privacy_policy_detail(request, slug):
    policy = get_object_or_404(
        PrivacyPolicy.objects.prefetch_related("projects").filter(is_active=True),
        slug=slug,
    )
    related_projects = []
    for project in policy.projects.all().order_by("title"):
        slug_base = slugify(project.title) or f"project-{project.pk}"
        related_projects.append({
            "title": project.title,
            "slug": f"{slug_base}-{project.pk}",
        })
    return render(request, "homepage/privacy_policy_detail.html", {
        "policy": policy,
        "related_projects": related_projects,
    })


def _build_project_entries():
    projects = Project.objects.prefetch_related("privacy_policies").all().order_by('-id')
    entries = []

    for project in projects:
        raw_description = project.description or ""
        html_description = render_markdown(raw_description)
        plain_description = strip_tags(html_description).strip()
        summary = plain_description[:220].rstrip()
        if plain_description and len(plain_description) > 220:
            summary = f"{summary}…"
        summary = summary or "Notes coming soon."

        tags = [tag for tag in (project.type or "").split(" ") if tag]
        slug_base = slugify(project.title) or f"project-{project.pk}"
        slug_value = f"{slug_base}-{project.pk}"

        image_url = None
        try:
            if project.image:
                image_url = project.image.url
        except ValueError:
            image_url = None

        linked_policies = [p for p in project.privacy_policies.all() if p.is_active]
        linked_policies.sort(key=lambda p: p.updated_at, reverse=True)
        primary_policy = linked_policies[0] if linked_policies else None

        # SEO meta description: explicit override -> subtitle -> truncated summary.
        meta_description = (
            (project.meta_description or "").strip()
            or (project.subtitle or "").strip()
            or summary
        )

        entries.append({
            "id": project.id,
            "slug": slug_value,
            "title": project.title,
            "subtitle": (project.subtitle or "").strip(),
            "summary": summary,
            "meta_description": meta_description,
            "description_html": html_description,
            "tags": tags,
            "link": project.link,
            "github_link": project.github_link,
            "image_url": image_url,
            "privacy_policy_slug": primary_policy.slug if primary_policy else None,
        })

    return entries


def _build_blog_summary(post: BlogPost) -> str:
    plain = strip_tags(render_markdown(post.content_markdown or "")).strip()
    summary = plain[:220].rstrip()
    if plain and len(plain) > 220:
        summary = f"{summary}…"
    return summary or "(no body yet)"


def blog_list(request):
    posts_qs = BlogPost.objects.filter(published=True)
    entries = []
    for post in posts_qs:
        subtitle = (post.subtitle or "").strip()
        summary = _build_blog_summary(post)
        meta_description = (
            (post.meta_description or "").strip()
            or subtitle
            or summary
        )
        entries.append({
            "slug": post.slug,
            "title": post.title,
            "subtitle": subtitle,
            "summary": summary,
            "meta_description": meta_description,
            "published_at": post.published_at,
        })
    return render(request, "homepage/blog_list.html", {
        "entries": entries,
        "page_title": "Blog",
        "page_description": "Quick notes, weeknotes, and unpolished writing. Longer-form essays live on Medium.",
    })


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    subtitle = (post.subtitle or "").strip()
    summary = _build_blog_summary(post)
    meta_description = (
        (post.meta_description or "").strip()
        or subtitle
        or summary
    )
    entry = {
        "slug": post.slug,
        "title": post.title,
        "subtitle": subtitle,
        "summary": summary,
        "meta_description": meta_description,
        "content_html": render_markdown(post.content_markdown or ""),
        "published_at": post.published_at,
    }
    return render(request, "homepage/blog_detail.html", {
        "entry": entry,
    })
