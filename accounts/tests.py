from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import ChildProfile


class HomePageTests(TestCase):
    def test_home_page_renders_with_demo_button(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instant demo login')
        self.assertContains(response, 'demo_parent')

    def test_home_page_redirects_signed_in_users_to_dashboard(self):
        user = User.objects.create_user('parent', password='strongpass123')
        self.client.force_login(user)
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('accounts:dashboard'))


class DemoLoginTests(TestCase):
    def setUp(self):
        call_command('seed_data', verbosity=0)

    def test_demo_login_signs_in_and_redirects(self):
        response = self.client.post(reverse('accounts:demo_login'))
        self.assertRedirects(response, reverse('accounts:dashboard'))
        self.assertEqual(
            int(self.client.session['_auth_user_id']),
            User.objects.get(username='demo_parent').id,
        )

    def test_dashboard_is_reachable_after_demo_login(self):
        self.client.post(reverse('accounts:demo_login'))
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aarav')
        self.assertContains(response, 'Diya')

    def test_demo_login_rejects_get(self):
        self.assertEqual(
            self.client.get(reverse('accounts:demo_login')).status_code, 405
        )


class AgeGroupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('parent', password='strongpass123')

    def _child(self, age):
        return ChildProfile.objects.create(
            parent=self.user, name='Test', age=age, grade='5th'
        )

    def test_age_group_is_computed_on_save(self):
        expected = {
            6: 'JUNIOR', 8: 'JUNIOR', 9: 'JUNIOR',
            10: 'MIDDLE', 11: 'MIDDLE', 12: 'MIDDLE',
            13: 'SENIOR', 15: 'SENIOR', 16: 'SENIOR',
        }
        for age, group in expected.items():
            with self.subTest(age=age):
                self.assertEqual(self._child(age).age_group, group)

    def test_age_group_updates_when_age_changes(self):
        child = self._child(8)
        child.age = 14
        child.save()
        self.assertEqual(child.age_group, 'SENIOR')

    def test_edit_child_updates_age_group(self):
        child = self._child(8)
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('accounts:child_edit', args=[child.id]),
            {'name': child.name, 'age': 12, 'grade': '7th', 'avatar_color': 'sky'},
        )
        self.assertRedirects(response, reverse('accounts:dashboard'))
        child.refresh_from_db()
        self.assertEqual((child.age, child.age_group), (12, 'MIDDLE'))


class ChildProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('parent', password='strongpass123')
        self.client.force_login(self.user)

    def test_add_child_form_creates_profile(self):
        response = self.client.post(reverse('accounts:child_create'), {
            'name': 'Mira', 'age': 9, 'grade': '4th', 'avatar_color': 'emerald',
        })
        self.assertEqual(response.status_code, 302)
        child = ChildProfile.objects.get(name='Mira')
        self.assertEqual(child.parent, self.user)
        self.assertEqual(child.age_group, 'JUNIOR')

    def test_age_outside_range_is_rejected(self):
        response = self.client.post(reverse('accounts:child_create'), {
            'name': 'TooOld', 'age': 20, 'grade': 'College',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChildProfile.objects.filter(name='TooOld').exists())
        self.assertContains(response, 'between 6 and 16')

    def test_delete_child_removes_profile(self):
        child = ChildProfile.objects.create(
            parent=self.user, name='Mira', age=9, grade='4th'
        )
        response = self.client.post(reverse('accounts:child_delete', args=[child.id]))
        self.assertRedirects(response, reverse('accounts:dashboard'))
        self.assertFalse(ChildProfile.objects.filter(id=child.id).exists())

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])


class RegistrationTests(TestCase):
    def test_register_creates_and_logs_in_user(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newparent',
            'email': 'new@example.com',
            'password1': 'very-strong-pass-42',
            'password2': 'very-strong-pass-42',
        })
        self.assertRedirects(response, reverse('accounts:dashboard'))
        self.assertTrue(User.objects.filter(username='newparent').exists())