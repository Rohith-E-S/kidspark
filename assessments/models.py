from django.db import models

from accounts.models import ChildProfile


class Category(models.Model):
    """One of the 8 assessment dimensions (4 aptitude + 4 interest)."""

    PILLAR_CHOICES = [
        ('APTITUDE', 'Cognitive Aptitude'),
        ('INTEREST', 'Area of Interest'),
    ]
    PILLAR_APTITUDE = 'APTITUDE'
    PILLAR_INTEREST = 'INTEREST'

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    pillar = models.CharField(max_length=20, choices=PILLAR_CHOICES)
    description = models.TextField()
    icon_name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['pillar', 'code']

    def __str__(self):
        return f'{self.name} ({self.code})'

    @property
    def is_aptitude(self):
        return self.pillar == self.PILLAR_APTITUDE


class QuestionQuerySet(models.QuerySet):
    """Questions are shared across ages; a child only sees its own group."""

    def for_age_group(self, age_group):
        return self.filter(age_group__in=['ALL', age_group])


class Question(models.Model):
    AGE_GROUP_CHOICES = [
        ('JUNIOR', '6-9 Years'),
        ('MIDDLE', '10-12 Years'),
        ('SENIOR', '13-16 Years'),
        ('ALL', 'All Ages'),
    ]
    TYPE_OBJECTIVE = 'OBJECTIVE'
    TYPE_PREFERENCE = 'PREFERENCE'
    QUESTION_TYPE_CHOICES = [
        ('OBJECTIVE', 'Aptitude Multiple Choice'),
        ('PREFERENCE', 'Interest Scenario'),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='questions'
    )
    age_group = models.CharField(
        max_length=10, choices=AGE_GROUP_CHOICES, default='ALL'
    )
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    text = models.TextField()
    visual_hint = models.CharField(
        max_length=255, blank=True,
        help_text='Short puzzle or scenario cue printed above the question',
    )
    difficulty_weight = models.IntegerField(default=1)  # 1=Easy, 2=Medium, 3=Hard
    order = models.PositiveIntegerField(default=0)

    objects = QuestionQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'[{self.category.code}] {self.text[:60]}'

    @property
    def is_objective(self):
        return self.question_type == self.TYPE_OBJECTIVE

    @property
    def difficulty_label(self):
        return {1: 'Easy', 2: 'Medium', 3: 'Hard'}.get(self.difficulty_weight, 'Easy')


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='choices'
    )
    text = models.CharField(max_length=255)
    icon_name = models.CharField(
        max_length=40, blank=True, help_text='Lucide icon name'
    )
    is_correct = models.BooleanField(default=False)
    score_weight = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.text


class AssessmentSession(models.Model):
    child = models.ForeignKey(
        ChildProfile, on_delete=models.CASCADE, related_name='sessions'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    current_question_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        status = 'completed' if self.is_completed else 'in progress'
        return f'{self.child.name} - {self.started_at:%d %b %Y} ({status})'

    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def answered_count(self):
        return self.responses.count()

    @property
    def progress_percent(self):
        total = self.total_questions
        if not total:
            return 0
        return round((self.answered_count / total) * 100)

    @property
    def questions(self):
        """The full ordered question set for the child's age group."""
        return Question.objects.for_age_group(self.child.age_group)

    def next_question(self):
        answered = self.responses.values_list('question_id', flat=True)
        return self.questions.exclude(id__in=answered).first()


class SessionResponse(models.Model):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name='responses'
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    time_taken_seconds = models.PositiveIntegerField(default=5)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'question')
        ordering = ['question__order', 'id']

    def __str__(self):
        return f'{self.session.child.name}: {self.question.text[:40]}'

    @property
    def is_correct(self):
        return self.selected_choice.is_correct

    @property
    def earned_points(self):
        return self.selected_choice.score_weight * self.question.difficulty_weight

    @property
    def max_points(self):
        return 10 * self.question.difficulty_weight
