from django.urls import path
from . import views

app_name = "homepage"
try:
    urlpatterns = [
        path("", views.index, name="index")
    ]
except Exception as e:
    print(e)