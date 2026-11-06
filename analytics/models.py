from django.db import models

from assessments.models import AssessmentSession, Category


class AssessmentResult(models.Model):
    session = models.OneToOneField(
        AssessmentSession, on_delete=models.CASCADE, related_name='result'
    )
    aptitude_scores = models.JSONField(default=dict)
    interest_scores = models.JSONField(default=dict)
    overall_aptitude_percentage = models.FloatField(default=0.0)
    dominant_aptitude = models.ForeignKey(
        Category, null=True, on_delete=models.SET_NULL, related_name='+'
    )
    dominant_interest = models.ForeignKey(
        Category, null=True, on_delete=models.SET_NULL, related_name='+'
    )
    persona_title = models.CharField(max_length=100)
    persona_summary = models.TextField()
    recommended_activities = models.JSONField(default=list)
    recommended_future_domains = models.JSONField(default=list)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'Result: {self.session.child.name} - {self.persona_title}'

    # --- Presentation helpers -------------------------------------------------
    @property
    def aptitude_breakdown(self):
        return self._breakdown(self.aptitude_scores)

    @property
    def interest_breakdown(self):
        return self._breakdown(self.interest_scores)

    def _breakdown(self, scores):
        rows = []
        for code, score in scores.items():
            category = Category.objects.filter(code=code).first()
            status = status_for_score(score)
            rows.append({
                'code': code,
                'name': category.name if category else code,
                'icon_name': category.icon_name if category else 'sparkles',
                'description': category.description if category else '',
                'pillar': category.pillar if category else '',
                'score': score,
                'status': status,
                'badge_class': LEVEL_META[status]['badge'],
                'bar_class': LEVEL_META[status]['bar'],
            })
        return rows

    @property
    def strengths(self):
        rows = self.aptitude_breakdown + self.interest_breakdown
        return [row for row in rows if row['score'] >= 75]

    @property
    def chart_labels_aptitude(self):
        return [row['name'] for row in self.aptitude_breakdown]

    @property
    def chart_values_aptitude(self):
        return [row['score'] for row in self.aptitude_breakdown]


LEVEL_META = {
    'Strong': {'badge': 'bg-emerald-100 text-emerald-700', 'bar': 'bg-emerald-500'},
    'Developing': {'badge': 'bg-amber-100 text-amber-700', 'bar': 'bg-amber-500'},
    'Emerging': {'badge': 'bg-rose-100 text-rose-700', 'bar': 'bg-rose-400'},
}


def status_for_score(score):
    """Shared strong/developing/emerging banding used across the UI."""
    if score >= 75:
        return 'Strong'
    if score >= 45:
        return 'Developing'
    return 'Emerging'
