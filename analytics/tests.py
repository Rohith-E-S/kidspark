from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import ChildProfile
from analytics.models import AssessmentResult
from analytics.services import PERSONA_MATRIX, generate_assessment_result
from assessments.models import (
    AssessmentSession,
    Category,
    Choice,
    Question,
    SessionResponse,
)


class ScoringEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user('parent', password='strongpass123')
        self.child = ChildProfile.objects.create(
            parent=self.user, name='Mira', age=11, grade='6th'
        )
        self.session = AssessmentSession.objects.create(child=self.child)

    def _answer_all(self, correct=True):
        for question in Question.objects.for_age_group('MIDDLE').prefetch_related('choices'):
            if question.is_objective:
                choice = question.choices.filter(is_correct=correct).first()
            else:
                choice = question.choices.first()
            SessionResponse.objects.create(
                session=self.session, question=question, selected_choice=choice
            )
        self.session.is_completed = True
        self.session.save()

    def test_perfect_answers_score_one_hundred(self):
        self._answer_all(correct=True)
        result = generate_assessment_result(self.session)
        for code, score in result.aptitude_scores.items():
            self.assertEqual(score, 100, code)
        self.assertEqual(result.overall_aptitude_percentage, 100.0)

    def test_all_wrong_answers_score_zero(self):
        self._answer_all(correct=False)
        result = generate_assessment_result(self.session)
        for score in result.aptitude_scores.values():
            self.assertEqual(score, 0)

    def test_difficulty_weight_changes_the_normalised_score(self):
        """A hard question is worth more than an easy one in the same category."""
        category = Category.objects.get(code='LOGICAL')
        easy = category.questions.get(difficulty_weight=1)
        hard = category.questions.get(difficulty_weight=3)

        def answer(question, correct):
            SessionResponse.objects.create(
                session=self.session, question=question,
                selected_choice=question.choices.filter(is_correct=correct).first(),
            )

        # Easy right, hard wrong: 10 / (10 + 30) = 25%
        answer(easy, True)
        answer(hard, False)
        self.assertEqual(
            generate_assessment_result(self.session).aptitude_scores['LOGICAL'], 25
        )

        # Hard right, easy wrong: 30 / (10 + 30) = 75%
        self.session.responses.all().delete()
        answer(easy, False)
        answer(hard, True)
        self.assertEqual(
            generate_assessment_result(self.session).aptitude_scores['LOGICAL'], 75
        )

    def test_result_is_idempotent(self):
        self._answer_all(correct=True)
        first = generate_assessment_result(self.session)
        second = generate_assessment_result(self.session)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            AssessmentResult.objects.filter(session=self.session).count(), 1
        )

    def test_persona_matrix_covers_all_sixteen_combinations(self):
        aptitudes = ['LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL']
        interests = ['STEM', 'ARTS', 'NATURE', 'SOCIAL']
        self.assertEqual(len(PERSONA_MATRIX), 16)
        for aptitude in aptitudes:
            for interest in interests:
                with self.subTest(aptitude=aptitude, interest=interest):
                    entry = PERSONA_MATRIX[(aptitude, interest)]
                    self.assertTrue(entry['title'])
                    self.assertTrue(entry['summary'])
                    self.assertEqual(len(entry['domains']), 4)
                    for group in ('JUNIOR', 'MIDDLE', 'SENIOR'):
                        self.assertEqual(len(entry['activities'][group]), 4)

    def test_activities_match_the_child_age_group(self):
        self._answer_all(correct=True)
        result = generate_assessment_result(self.session)
        expected = PERSONA_MATRIX[
            (result.dominant_aptitude.code, result.dominant_interest.code)
        ]['activities'][self.child.age_group]
        self.assertEqual(result.recommended_activities, list(expected))

    def test_breakdown_reports_status_bands(self):
        self._answer_all(correct=True)
        result = generate_assessment_result(self.session)
        for row in result.aptitude_breakdown + result.interest_breakdown:
            self.assertIn(row['status'], {'Strong', 'Developing', 'Emerging'})
            self.assertTrue(row['badge_class'])
            self.assertTrue(row['bar_class'])


class ReportViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user('parent', password='strongpass123')
        self.child = ChildProfile.objects.create(
            parent=self.user, name='Mira', age=9, grade='4th'
        )
        self.session = AssessmentSession.objects.create(child=self.child)
        for question in Question.objects.for_age_group('JUNIOR').prefetch_related('choices'):
            choice = (
                question.choices.get(is_correct=True)
                if question.is_objective
                else question.choices.first()
            )
            SessionResponse.objects.create(
                session=self.session, question=question, selected_choice=choice
            )
        self.session.is_completed = True
        self.session.save()
        self.result = generate_assessment_result(self.session)

    def test_report_renders_with_chart_data(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('analytics:report_detail', args=[self.session.id])
        )
        self.assertEqual(response.status_code, 200)

        # Chart payloads are inlined as JSON for Chart.js.
        self.assertContains(response, 'id="aptitudeRadar"')
        self.assertContains(response, 'id="interestBars"')
        self.assertContains(response, 'const aptitudeData =')
        self.assertContains(response, 'const interestData =')
        for code in ('Logical & Mathematical', 'STEM & Discovery'):
            self.assertContains(response, code)

    def test_report_shows_persona_and_recommendations(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('analytics:report_detail', args=[self.session.id])
        )
        self.assertContains(response, escape(self.result.persona_title))
        for activity in self.result.recommended_activities:
            self.assertContains(response, escape(activity))
        for domain in self.result.recommended_future_domains:
            self.assertContains(response, escape(domain))

    def test_report_is_private_to_the_owner(self):
        stranger = User.objects.create_user('stranger', password='strongpass123')
        self.client.force_login(stranger)
        response = self.client.get(
            reverse('analytics:report_detail', args=[self.session.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_report_requires_login(self):
        response = self.client.get(
            reverse('analytics:report_detail', args=[self.session.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])

    def test_incomplete_session_redirects_back_to_quiz(self):
        incomplete = AssessmentSession.objects.create(child=self.child)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('analytics:report_detail', args=[incomplete.id])
        )
        self.assertRedirects(
            response, reverse('assessments:session', args=[incomplete.id])
        )

    def test_result_is_backfilled_when_missing(self):
        self.result.delete()
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('analytics:report_detail', args=[self.session.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AssessmentResult.objects.filter(session=self.session).exists())

    def test_all_reports_lists_only_own_sessions(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('analytics:all_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mira')
        self.assertNotContains(response, 'Aarav')  # seeded demo child, different parent