import re

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import ChildProfile
from assessments.models import AssessmentSession, Category, Choice, Question, SessionResponse

# Emoji / pictograph ranges. The plain typographic arrows (U+2190–U+21FF) are
# deliberately excluded — they are text, not emoji — but a variation selector
# (U+FE0F), which forces emoji presentation, is never allowed.
EMOJI = re.compile('[\u2600-\u27bf\u2b00-\u2bff\ufe0f\u20e3'
                   '\U0001f000-\U0001f0ff\U0001f300-\U0001faff\U0001f900-\U0001f9ff]')
LUCIDE_NAME = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


class QuizFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user('parent', password='strongpass123')
        self.client.force_login(self.user)
        self.child = ChildProfile.objects.create(
            parent=self.user, name='Mira', age=11, grade='6th'
        )

    # -- helpers ----------------------------------------------------------
    def _answer_current(self, session):
        question = session.next_question()
        self.assertIsNotNone(question, 'session should still have questions')
        choice = question.choices.first()
        return self.client.post(
            reverse('assessments:session', args=[session.id]),
            {'choice': choice.id, 'time_taken': 7},
            follow=False,
        )

    def _complete_session(self, session):
        guard = 0
        while not session.is_completed and guard < 60:
            guard += 1
            self._answer_current(session)
            session.refresh_from_db()
        self.assertTrue(session.is_completed, 'session should complete')

    # -- tests ------------------------------------------------------------
    def test_start_test_creates_an_incomplete_session(self):
        response = self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        self.assertRedirects(
            response, reverse('assessments:session', args=[session.id])
        )
        self.assertFalse(session.is_completed)
        self.assertEqual(session.total_questions, 24)

    def test_starting_twice_resumes_the_same_session(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        self._answer_current(AssessmentSession.objects.get(child=self.child))
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        self.assertEqual(AssessmentSession.objects.filter(child=self.child).count(), 1)

    def test_quiz_page_renders_first_question(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        response = self.client.get(reverse('assessments:session', args=[session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Question 1 of 24')
        self.assertContains(response, session.next_question().text)

    def test_answer_records_response_and_advances(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        question = session.next_question()
        self._answer_current(session)

        session.refresh_from_db()
        self.assertEqual(session.responses.count(), 1)
        response = SessionResponse.objects.get(session=session)
        self.assertEqual(response.question, question)
        self.assertEqual(response.time_taken_seconds, 7)

    def test_htmx_request_returns_partial_with_next_question(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        question = session.next_question()

        response = self.client.post(
            reverse('assessments:session', args=[session.id]),
            {'choice': question.choices.first().id, 'time_taken': 4},
            headers={'hx-request': 'true'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="quiz-stage"')
        self.assertContains(response, 'Question 2 of 24')
        self.assertNotContains(response, '<html')

    def test_choice_from_another_question_is_rejected(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        foreign_choice = Choice.objects.exclude(
            question=session.next_question()
        ).first()
        response = self.client.post(
            reverse('assessments:session', args=[session.id]),
            {'choice': foreign_choice.id},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(session.responses.count(), 0)

    def test_completing_all_questions_generates_a_result(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        self._complete_session(session)

        self.assertEqual(session.responses.count(), 24)
        result = session.result
        self.assertEqual(
            set(result.aptitude_scores), {'LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL'}
        )
        self.assertEqual(
            set(result.interest_scores), {'STEM', 'ARTS', 'NATURE', 'SOCIAL'}
        )
        for score in list(result.aptitude_scores.values()) + list(result.interest_scores.values()):
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

        self.assertIsNotNone(result.dominant_aptitude)
        self.assertIn(
            result.dominant_aptitude.code, {'LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL'}
        )
        self.assertIn(
            result.dominant_interest.code, {'STEM', 'ARTS', 'NATURE', 'SOCIAL'}
        )
        self.assertTrue(result.persona_title)
        self.assertEqual(len(result.recommended_activities), 4)
        self.assertEqual(len(result.recommended_future_domains), 4)

    def test_final_answer_redirects_to_the_report(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)

        guard = 0
        response = None
        while not session.is_completed and guard < 60:
            guard += 1
            response = self._answer_current(session)
            session.refresh_from_db()

        self.assertRedirects(
            response,
            reverse('analytics:report_detail', args=[session.id]),
            fetch_redirect_response=False,
        )

    def test_completed_session_redirects_away_from_the_quiz(self):
        self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        session = AssessmentSession.objects.get(child=self.child)
        self._complete_session(session)

        response = self.client.get(reverse('assessments:session', args=[session.id]))
        self.assertRedirects(
            response, reverse('analytics:report_detail', args=[session.id])
        )


class OwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='strongpass123')
        self.stranger = User.objects.create_user('stranger', password='strongpass123')
        self.child = ChildProfile.objects.create(
            parent=self.owner, name='Mira', age=8, grade='3rd'
        )

    def test_cannot_start_another_parents_child(self):
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('assessments:start_test', args=[self.child.id]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_open_another_parents_session(self):
        session = AssessmentSession.objects.create(child=self.child)
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('assessments:session', args=[session.id]))
        self.assertEqual(response.status_code, 404)

    def test_select_page_lists_only_own_children(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('assessments:select_test'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mira')
        self.assertNotContains(response, 'Aarav')


class SeedDataTests(TestCase):
    def test_seed_data_is_idempotent(self):
        call_command('seed_data', verbosity=0)
        counts = (
            Question.objects.count(),
            Choice.objects.count(),
            ChildProfile.objects.count(),
            User.objects.count(),
        )
        call_command('seed_data', verbosity=0)
        self.assertEqual(
            counts,
            (
                Question.objects.count(),
                Choice.objects.count(),
                ChildProfile.objects.count(),
                User.objects.count(),
            ),
        )
        self.assertEqual(Question.objects.count(), 24)
        self.assertEqual(SessionResponse.objects.count(), 24)


class IconTests(TestCase):
    """The UI uses Lucide icon names, never emoji, as its visual vocabulary."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)

    def test_no_seeded_text_contains_an_emoji(self):
        fields = []
        for category in Category.objects.all():
            fields += [('category.name', category.name),
                       ('category.description', category.description),
                       ('category.icon_name', category.icon_name)]
        for question in Question.objects.all():
            fields += [('question.text', question.text),
                       ('question.visual_hint', question.visual_hint)]
        for choice in Choice.objects.all():
            fields += [('choice.text', choice.text),
                       ('choice.icon_name', choice.icon_name)]

        offenders = [(name, value) for name, value in fields if EMOJI.search(value or '')]
        self.assertEqual(offenders, [], 'emoji found in seeded content')

    def test_every_icon_name_is_a_lucide_name(self):
        names = list(Category.objects.values_list('icon_name', flat=True)) + list(
            Choice.objects.exclude(icon_name='').values_list('icon_name', flat=True)
        )
        for name in names:
            with self.subTest(icon=name):
                self.assertRegex(name, LUCIDE_NAME)

    def test_every_choice_has_a_usable_icon_or_none(self):
        for choice in Choice.objects.all():
            with self.subTest(choice=choice.text, icon=choice.icon_name):
                # Either a real icon name, or empty when the text is the answer
                # (a bare number or a clock time, where an icon adds nothing).
                self.assertTrue(choice.icon_name or choice.text.strip())

    def test_palette_and_categories_agree(self):
        for category in Category.objects.all():
            with self.subTest(code=category.code):
                self.assertTrue(category.icon_name)

    def test_quiz_template_renders_icons_not_emoji(self):
        user = User.objects.create_user('parent', password='strongpass123')
        self.client.force_login(user)
        child = ChildProfile.objects.create(
            parent=user, name='Mira', age=11, grade='6th'
        )
        self.client.get(reverse('assessments:start_test', args=[child.id]))
        session = AssessmentSession.objects.get(child=child)
        response = self.client.get(reverse('assessments:session', args=[session.id]))

        body = response.content.decode()
        self.assertNotRegex(body, EMOJI)
        self.assertContains(response, 'data-lucide=')

    def test_report_template_renders_icons_not_emoji(self):
        user = User.objects.create_user('parent', password='strongpass123')
        self.client.force_login(user)
        session = AssessmentSession.objects.filter(is_completed=True).first()
        session.child.parent = user
        session.child.save()

        response = self.client.get(
            reverse('analytics:report_detail', args=[session.id])
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotRegex(body, EMOJI)
        self.assertContains(response, 'data-lucide=')


class TeacherPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)
        cls.staff_user = User.objects.create_user('teacher_user', password='password123', is_staff=True)
        cls.normal_user = User.objects.create_user('normal_parent', password='password123', is_staff=False)
        cls.category = Category.objects.get(code='LOGICAL')

    def test_teacher_dashboard_requires_staff(self):
        # Anonymous redirect
        response = self.client.get(reverse('assessments:teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Non-staff redirect
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('assessments:teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Staff user allowed
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('assessments:teacher_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Question Bank Manager')
        self.assertContains(response, 'Logical &amp; Mathematical')

    def test_teacher_filter_by_dimension_and_search(self):
        self.client.force_login(self.staff_user)

        # Filter by category
        response = self.client.get(reverse('assessments:teacher_dashboard'), {'category': 'LOGICAL'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Which number finishes the pattern?')

        # Search
        response = self.client.get(reverse('assessments:teacher_dashboard'), {'q': 'snail'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You find a tiny snail on the path')

    def test_teacher_create_question_with_choices(self):
        self.client.force_login(self.staff_user)
        payload = {
            'category': self.category.id,
            'question_type': 'OBJECTIVE',
            'age_group': 'JUNIOR',
            'difficulty_weight': 1,
            'text': 'What is 3 + 4?',
            'visual_hint': '3 + 4 = ?',
            'order': 99,
            'choice_1_text': '7',
            'choice_1_icon': '',
            'choice_1_weight': 0,
            'choice_2_text': '6',
            'choice_2_icon': '',
            'choice_2_weight': 0,
            'choice_3_text': '8',
            'choice_3_icon': '',
            'choice_3_weight': 0,
            'choice_4_text': '5',
            'choice_4_icon': '',
            'choice_4_weight': 0,
            'correct_choice': '1',
        }
        response = self.client.post(reverse('assessments:teacher_question_create'), data=payload)
        self.assertEqual(response.status_code, 302)

        question = Question.objects.filter(text='What is 3 + 4?').first()
        self.assertIsNotNone(question)
        self.assertEqual(question.choices.count(), 4)
        correct_choice = question.choices.get(is_correct=True)
        self.assertEqual(correct_choice.text, '7')
        self.assertEqual(correct_choice.score_weight, 10)

    def test_teacher_edit_question(self):
        self.client.force_login(self.staff_user)
        q = Question.objects.first()
        payload = {
            'category': q.category.id,
            'question_type': q.question_type,
            'age_group': q.age_group,
            'difficulty_weight': 2,
            'text': 'Updated Question Text Here?',
            'visual_hint': 'Updated Cue',
            'order': q.order,
            'choice_1_text': 'Updated Choice A',
            'choice_1_icon': 'smile',
            'choice_1_weight': 0,
            'choice_2_text': 'Updated Choice B',
            'choice_2_icon': '',
            'choice_2_weight': 0,
            'choice_3_text': 'Updated Choice C',
            'choice_3_icon': '',
            'choice_3_weight': 0,
            'choice_4_text': 'Updated Choice D',
            'choice_4_icon': '',
            'choice_4_weight': 0,
            'correct_choice': '1',
        }
        response = self.client.post(reverse('assessments:teacher_question_edit', args=[q.id]), data=payload)
        self.assertEqual(response.status_code, 302)

        q.refresh_from_db()
        self.assertEqual(q.text, 'Updated Question Text Here?')
        self.assertEqual(q.difficulty_weight, 2)
        choice_a = q.choices.first()
        self.assertEqual(choice_a.text, 'Updated Choice A')

    def test_student_preview_endpoint(self):
        self.client.force_login(self.staff_user)
        q = Question.objects.first()
        response = self.client.get(reverse('assessments:teacher_question_preview', args=[q.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Simulated Quiz Card · Student View')
        self.assertContains(response, q.text)


class ClassroomManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', verbosity=0)
        cls.teacher = User.objects.create_user('teacher_jenny', password='password123', is_staff=True)
        cls.normal_parent = User.objects.create_user('parent_john', password='password123', is_staff=False)

    def test_classroom_requires_staff(self):
        # Anonymous redirect
        res = self.client.get(reverse('assessments:classroom_list'))
        self.assertEqual(res.status_code, 302)

        # Non-staff redirect
        self.client.force_login(self.normal_parent)
        res = self.client.get(reverse('assessments:classroom_list'))
        self.assertEqual(res.status_code, 302)

        # Staff allowed
        self.client.force_login(self.teacher)
        res = self.client.get(reverse('assessments:classroom_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Classrooms &amp; Student Cohorts')

    def test_classroom_create_and_list(self):
        self.client.force_login(self.teacher)
        payload = {
            'name': 'Grade 5 - Section A (Dolphins)',
            'grade': '5th Grade',
            'academic_year': '2026-2027',
            'description': 'Advanced STEM and logic cohort.',
        }
        res = self.client.post(reverse('assessments:classroom_create'), data=payload)
        from accounts.models import Classroom
        classroom = Classroom.objects.filter(name='Grade 5 - Section A (Dolphins)').first()
        self.assertIsNotNone(classroom)
        self.assertEqual(classroom.teacher, self.teacher)
        self.assertEqual(classroom.grade, '5th Grade')
        self.assertTrue(len(classroom.code) >= 6)
        self.assertRedirects(res, reverse('assessments:classroom_detail', args=[classroom.id]))

        # View in classroom list
        list_res = self.client.get(reverse('assessments:classroom_list'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, 'Grade 5 - Section A (Dolphins)')
        self.assertContains(list_res, classroom.code)

    def test_classroom_edit(self):
        from accounts.models import Classroom
        self.client.force_login(self.teacher)
        c = Classroom.objects.create(
            teacher=self.teacher, name='Grade 4 Cohort', grade='4th Grade'
        )
        res = self.client.post(reverse('assessments:classroom_edit', args=[c.id]), data={
            'name': 'Grade 4 - Hawks',
            'grade': '4th Grade',
            'academic_year': '2026-2027',
            'description': 'Updated description',
        })
        self.assertRedirects(res, reverse('assessments:classroom_detail', args=[c.id]))
        c.refresh_from_db()
        self.assertEqual(c.name, 'Grade 4 - Hawks')

    def test_student_enrollment_and_detail(self):
        from accounts.models import Classroom
        self.client.force_login(self.teacher)
        c = Classroom.objects.create(
            teacher=self.teacher, name='Grade 6 Cohort', grade='6th Grade'
        )

        # Enroll student
        res = self.client.post(reverse('assessments:student_add', args=[c.id]), data={
            'name': 'Lucas Vance',
            'age': 11,
            'grade': '6th Grade',
            'avatar_color': 'sky',
        })
        self.assertRedirects(res, reverse('assessments:classroom_detail', args=[c.id]))

        lucas = c.students.filter(name='Lucas Vance').first()
        self.assertIsNotNone(lucas)
        self.assertEqual(lucas.age_group, 'MIDDLE')
        self.assertEqual(lucas.parent, self.teacher)

        # Classroom detail page shows student
        detail_res = self.client.get(reverse('assessments:classroom_detail', args=[c.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Lucas Vance')
        self.assertContains(detail_res, 'Not Started')

    def test_student_edit_and_unenroll(self):
        from accounts.models import Classroom
        self.client.force_login(self.teacher)
        c = Classroom.objects.create(teacher=self.teacher, name='Test Cohort', grade='5th Grade')
        student = ChildProfile.objects.create(
            parent=self.teacher, classroom=c, name='Ella Blue', age=9, grade='5th Grade'
        )
        self.assertEqual(student.age_group, 'JUNIOR')

        # Edit student age
        edit_res = self.client.post(reverse('assessments:student_edit', args=[student.id]), data={
            'name': 'Ella Blue',
            'age': 10,
            'grade': '5th Grade',
            'avatar_color': 'rose',
        })
        self.assertRedirects(edit_res, reverse('assessments:classroom_detail', args=[c.id]))
        student.refresh_from_db()
        self.assertEqual(student.age, 10)
        self.assertEqual(student.age_group, 'MIDDLE')

        # Unenroll student
        unenroll_res = self.client.post(reverse('assessments:student_remove', args=[student.id]))
        self.assertRedirects(unenroll_res, reverse('assessments:classroom_detail', args=[c.id]))
        student.refresh_from_db()
        self.assertIsNone(student.classroom)

    def test_cohort_analytics_with_completed_session(self):
        from accounts.models import Classroom
        self.client.force_login(self.teacher)
        c = Classroom.objects.create(teacher=self.teacher, name='Analytics Cohort', grade='6th Grade')

        # Aarav was seeded with a completed session and AssessmentResult
        aarav = ChildProfile.objects.filter(name='Aarav').first()
        self.assertIsNotNone(aarav)
        aarav.classroom = c
        aarav.save()

        res = self.client.get(reverse('assessments:classroom_detail', args=[c.id]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Aarav')
        self.assertContains(res, 'Completed')
        self.assertContains(res, '8-Dimension Cohort Radar')
        self.assertContains(res, 'cohortRadarChart')
        self.assertContains(res, 'Class Persona Archetypes')