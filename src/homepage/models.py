from django.db import models
import markdown
# Create your models here.


class Project(models.Model):
    title = models.CharField(max_length=64)
    description = models.TextField(default=None, blank=True, null=True)
    link = models.TextField(default=None, blank=True, null=True)
    github_link = models.TextField(default=None, blank=True, null=True)
    image = models.ImageField(
        upload_to="media/", height_field=None, width_field=None, max_length=None)
    type = models.CharField(max_length=64, blank=True)

    def toDict(self):
        return {'title': self.title.title(),
                'description': markdown.markdown(self.description),
                'github_link': self.github_link,
                'link': self.link, 'image': self.image.url,
                'type': self.type.split(" ")}

    def __str__(self):
        return f"{self.title}"