from django.contrib import admin

from .models import BlogPost, PrivacyPolicy, Project


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
