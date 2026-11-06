from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from accounts.models import ChildProfile


class KidSparkLoginForm(AuthenticationForm):
    """Login form with Tailwind-friendly widgets."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 '
                     'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 '
                     'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
            'placeholder': 'Password',
        })
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shared = ('w-full rounded-xl border border-slate-200 px-4 py-3 '
                  'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none')
        placeholders = {
            'username': 'Choose a username',
            'email': 'you@example.com',
            'password1': 'Create a password',
            'password2': 'Repeat the password',
        }
        for name, field in self.fields.items():
            field.widget.attrs['class'] = shared
            field.widget.attrs['placeholder'] = placeholders.get(name, '')
        self.fields['email'].required = False
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_email(self):
        return self.cleaned_data.get('email', '')


AVATAR_COLORS = ['indigo', 'rose', 'emerald', 'amber', 'sky', 'violet']


class ChildProfileForm(forms.ModelForm):
    avatar_color = forms.ChoiceField(
        choices=[(c, c.title()) for c in AVATAR_COLORS],
        initial='indigo',
        widget=forms.RadioSelect,
        required=False,
    )

    class Meta:
        model = ChildProfile
        fields = ('name', 'age', 'grade', 'avatar_color')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 '
                         'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
                'placeholder': "Child's first name",
            }),
            'age': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 '
                         'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
                'min': 6, 'max': 16, 'placeholder': '6 - 16',
            }),
            'grade': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 '
                         'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
                'placeholder': 'e.g. 6th Grade',
            }),
        }

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 6 or age > 16:
            raise forms.ValidationError(
                'KidSpark is designed for children between 6 and 16 years old.'
            )
        return age

    def clean_avatar_color(self):
        return self.cleaned_data.get('avatar_color') or 'indigo'

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.age_group = ChildProfile.compute_age_group(profile.age)
        if commit:
            profile.save()
        return profile
