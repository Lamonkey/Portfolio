from django.db import models

# Create your models here.
class Project(models.Model):
    title = models.CharField(max_length=64)
    description = models.TextField()
    link = models.TextField()
    image = models.ImageField(upload_to="media/", height_field=None, width_field=None, max_length=None)
    type = models.CharField(max_length=64,blank=True)

    def toDict(self):
        return {'title':self.title,'description':self.description,'link':self.link,'image':self.image.url,'type':self.type.split(" ")}

    def __str__(self):
        return f"{self.title}"