from django.urls import path
from . import views

app_name = "homepage"
urlpatterns = [
    path("<str:name>",views.greet,name='greet'),
    path("",views.index,name="index"),
]
