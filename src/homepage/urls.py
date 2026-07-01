from django.urls import path
from . import views

app_name = "homepage"

urlpatterns = [
    path("oldVersion/", views.index, name="index"),
    path("writing-room/", views.writing_room, name="writing-room"),
    path("", views.home, name="home"),
    path("projects/", views.software_log, name="software-log"),
    path("software-log/<slug:slug>/", views.software_log_detail, name="software-log-detail"),
    path("privacy-policy/<slug:slug>/", views.privacy_policy_detail, name="privacy-policy-detail"),
    path("blog/", views.blog_list, name="blog-list"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog-detail"),
    path("dashboard/budget/", views.budget_dashboard, name="budget-dashboard"),
]
