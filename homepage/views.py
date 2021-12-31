from django.shortcuts import render
from .models import Project

# Create your views here.
def index(request):
    labels = [x.type for x in Project.objects.all()]
    return render(request,"homepage/index.html",{
        "projects":Project.objects.all(),
        #send unique labels only
        "labels":set(labels)

    })