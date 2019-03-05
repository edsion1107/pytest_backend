from django.db import models


class AccessToken(models.Model):
    key = models.CharField(max_length=512)
    expires_in = models.DateTimeField()
    create = models.DateTimeField(auto_now_add=True)
