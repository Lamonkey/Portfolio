from django.shortcuts import render
from .models import Project
from json import dumps

# Create your views here.
def index(request):
    labels = [(x.type).lower().capitalize() for x in Project.objects.all()]
    jsonData = dumps([(project.toDict()) for project in Project.objects.all()])
    return render(request,"homepage/index.html",{
        "projects":Project.objects.all(),
        #send unique labels only
        "labels":set(labels),
        "jsonData":jsonData,

    })