from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ProductAnnouncement(models.Model):
    """A staff-authored message shown to every signed-in user after publication."""

    title = models.CharField(max_length=160)
    body = models.TextField()
    published_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title


class ProductAnnouncementRead(models.Model):
    announcement = models.ForeignKey(ProductAnnouncement, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_announcement_reads")
    read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("announcement", "user"), name="product_announcement_user_read_uniq"),
        ]
