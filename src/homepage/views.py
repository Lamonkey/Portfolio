from django.shortcuts import render
from .models import Project

# Create your views here.


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
# convert label to raw label


def convert_label(label):
    raw_label = label.lower()
    raw_label = raw_label.split(" ")
    raw_label = "_".join(raw_label)
    return raw_label
