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
    class_code = forms.CharField(
        max_length=20,
        required=False,
        label='Classroom Join Code (optional)',
        help_text='If your teacher gave you a 6-character class code, enter it to link this profile.',
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-xl border border-slate-200 px-4 py-3 uppercase font-mono tracking-wider '
                     'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none',
            'placeholder': 'e.g. A1B2C3',
        }),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.classroom:
            self.fields['class_code'].initial = self.instance.classroom.code

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 6 or age > 16:
            raise forms.ValidationError(
                'KidSpark is designed for children between 6 and 16 years old.'
            )
        return age

    def clean_avatar_color(self):
        return self.cleaned_data.get('avatar_color') or 'indigo'

    def clean_class_code(self):
        code = self.cleaned_data.get('class_code', '').strip().lstrip('#').upper()
        if not code:
            return None
        from accounts.models import Classroom
        try:
            classroom = Classroom.objects.get(code__iexact=code)
            return classroom
        except Classroom.DoesNotExist:
            raise forms.ValidationError(f"No classroom found with code '{code}'. Please check with your teacher.")

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.age_group = ChildProfile.compute_age_group(profile.age)
        classroom = self.cleaned_data.get('class_code')
        if classroom is not None:
            profile.classroom = classroom
        if commit:
            profile.save()
        return profile


class JoinClassroomForm(forms.Form):
    """Form for parents/students to join a classroom cohort using a join code."""

    child = forms.ModelChoiceField(
        queryset=ChildProfile.objects.none(),
        label='Select Child Profile',
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    class_code = forms.CharField(
        max_length=20,
        label='Classroom Join Code',
        widget=forms.TextInput(attrs={
            'class': 'form-input uppercase font-mono tracking-widest text-lg font-bold text-center',
            'placeholder': 'e.g. E4B82A',
            'autofocus': 'autofocus',
        }),
        help_text='Enter the 6-character code provided by your educator.',
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['child'].queryset = user.children.all().order_by('name')

    def clean_class_code(self):
        code = self.cleaned_data.get('class_code', '').strip().lstrip('#').upper()
        if not code:
            raise forms.ValidationError('Please enter a classroom join code.')
        from accounts.models import Classroom
        try:
            return Classroom.objects.get(code__iexact=code)
        except Classroom.DoesNotExist:
            raise forms.ValidationError(f"No classroom found matching code '{code}'. Check with your teacher and try again.")

