from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MIN_AGE = 6
MAX_AGE = 16


class ChildProfile(models.Model):
    """A child whose aptitude and interests are being assessed."""

    AGE_GROUP_CHOICES = [
        ('JUNIOR', '6-9 Years'),
        ('MIDDLE', '10-12 Years'),
        ('SENIOR', '13-16 Years'),
    ]

    parent = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='children'
    )
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_AGE), MaxValueValidator(MAX_AGE)]
    )
    age_group = models.CharField(
        max_length=10, choices=AGE_GROUP_CHOICES, blank=True
    )
    grade = models.CharField(max_length=50)
    avatar_color = models.CharField(max_length=20, default='indigo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.name} ({self.age})'

    @staticmethod
    def compute_age_group(age):
        if age <= 9:
            return 'JUNIOR'
        if age <= 12:
            return 'MIDDLE'
        return 'SENIOR'

    def save(self, *args, **kwargs):
        self.age_group = self.compute_age_group(self.age)
        super().save(*args, **kwargs)

    @property
    def age_group_label(self):
        return dict(self.AGE_GROUP_CHOICES).get(self.age_group, self.age_group)

    @property
    def initials(self):
        return self.name.strip()[:1].upper() or '?'

    @property
    def completed_sessions(self):
        return self.sessions.filter(is_completed=True)

    @property
    def completed_count(self):
        return self.completed_sessions.count()

    @property
    def active_session(self):
        return self.sessions.filter(is_completed=False).order_by('-started_at').first()

    @property
    def latest_result(self):
        from analytics.models import AssessmentResult

        return (
            AssessmentResult.objects.filter(session__child=self, session__is_completed=True)
            .order_by('-generated_at')
            .first()
        )
