from django.urls import path
from . import views

app_name = "homepage"

urlpatterns = [
    path("oldVersion/", views.index, name="index"),
    path("writing-room/", views.writing_room, name="writing-room"),
    path("", views.software_log, name="software-log"),
    path("software-log/<slug:slug>/", views.software_log_detail, name="software-log-detail"),
    path("privacy-policy/<slug:slug>/", views.privacy_policy_detail, name="privacy-policy-detail"),
]
