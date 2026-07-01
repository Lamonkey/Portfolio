from django.contrib import admin

from .models import BlogPost, FeaturedItem, LandingPage, PrivacyPolicy, Project, ProjectCost


class ProjectCostInline(admin.TabularInline):
    """Edit a project's recurring costs right on the project page."""

    model = ProjectCost
    extra = 0
    fields = ("label", "provider", "amount", "cadence", "is_active", "notes")


@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = ("name", "headline", "updated_at")
    readonly_fields = ("updated_at",)
    fields = (
        "name",
        "headline",
        "intro_markdown",
        "photo",
        "project_section_title",
        "post_section_title",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Singleton: only allow one landing page row.
        return not LandingPage.objects.exists()


@admin.register(FeaturedItem)
class FeaturedItemAdmin(admin.ModelAdmin):
    """The 'featured' table that drives the landing page.

    Reads like a spreadsheet: edit order / on-off inline, one row per
    spotlighted project or post.
    """

    list_display = ("order", "kind", "target", "is_active", "note")
    list_display_links = ("target",)
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    autocomplete_fields = ("project", "post")
    fields = ("order", "is_active", "project", "post", "note")

    @admin.display(description="Type")
    def kind(self, obj):
        return "Project" if obj.is_project else "Post"

    @admin.display(description="Featured")
    def target(self, obj):
        return obj.project or obj.post or "(empty)"


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "published", "published_at", "updated_at")
    list_filter = ("published",)
    search_fields = ("title", "subtitle", "content_markdown", "meta_description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "title",
        "slug",
        "subtitle",
        "content_markdown",
        "meta_description",
        "published",
        "published_at",
        "created_at",
        "updated_at",
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "subtitle", "type", "image", "link")
    search_fields = ("title", "subtitle", "meta_description")
    inlines = (ProjectCostInline,)
    fields = (
        "title",
        "subtitle",
        "description",
        "meta_description",
        "type",
        "link",
        "github_link",
        "image",
    )


@admin.register(ProjectCost)
class ProjectCostAdmin(admin.ModelAdmin):
    list_display = ("label", "project", "provider", "amount", "cadence", "monthly_amount", "is_active")
    list_filter = ("is_active", "cadence", "provider")
    list_editable = ("amount", "cadence", "is_active")
    search_fields = ("label", "provider", "notes", "project__title")
    autocomplete_fields = ("project",)
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "project",
        "label",
        "provider",
        "amount",
        "cadence",
        "is_active",
        "notes",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Monthly")
    def monthly_amount(self, obj):
        return obj.monthly_amount


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active", "updated_at")
    list_filter = ("is_active", "updated_at")
    search_fields = ("title", "slug", "content_markdown")
    filter_horizontal = ("projects",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "title",
        "slug",
        "is_active",
        "projects",
        "content_markdown",
        "created_at",
        "updated_at",
    )
