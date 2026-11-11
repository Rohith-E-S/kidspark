from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MIN_AGE = 6
MAX_AGE = 16


class Classroom(models.Model):
    """A classroom managed by a teacher/staff member."""

    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='classrooms'
    )
    name = models.CharField(max_length=100, help_text="e.g. Grade 5 - Section A")
    grade = models.CharField(max_length=50, help_text="e.g. 5th Grade")
    academic_year = models.CharField(max_length=20, default='2026-2027')
    code = models.CharField(max_length=12, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['grade', 'name', 'id']

    def __str__(self):
        return f"{self.name} ({self.grade})"

    def save(self, *args, **kwargs):
        if not self.code:
            import secrets
            self.code = secrets.token_hex(3).upper()
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return self.students.count()

    @property
    def completed_assessments_count(self):
        from assessments.models import AssessmentSession
        return AssessmentSession.objects.filter(
            child__classroom=self, is_completed=True
        ).count()


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
    classroom = models.ForeignKey(
        Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='students'
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
