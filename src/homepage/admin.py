from django.contrib import admin

from .models import Project
# Register your models here.
# admin.site.register(Project)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title","description","type","image","link")