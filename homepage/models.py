from django.db import models

# Create your models here.
class Project(models.Model):
    title = models.CharField(max_length=64)
    description = models.TextField()
    link = models.TextField()
    image = models.ImageField(upload_to="homepage/", height_field=None, width_field=None, max_length=None)
    type = models.CharField(max_length=64,blank=True)
