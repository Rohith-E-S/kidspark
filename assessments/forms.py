from django import forms
from django.db import transaction

from accounts.forms import AVATAR_COLORS
from accounts.models import ChildProfile, Classroom
from assessments.models import Category, Choice, Question


class ClassroomForm(forms.ModelForm):
    """Teacher form to create or update a classroom."""

    class Meta:
        model = Classroom
        fields = ('name', 'grade', 'academic_year', 'description')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Grade 5 - Section A / Eagles',
            }),
            'grade': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 5th Grade',
            }),
            'academic_year': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 2026-2027',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this classroom cohort...',
            }),
        }


class StudentEnrollmentForm(forms.ModelForm):
    """Teacher form to enroll or edit a student in a classroom."""

    avatar_color = forms.ChoiceField(
        choices=[(c, c.title()) for c in AVATAR_COLORS],
        initial='indigo',
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = ChildProfile
        fields = ('name', 'age', 'grade', 'avatar_color')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Student Full Name',
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 6,
                'max': 16,
                'placeholder': 'Age (6 - 16)',
            }),
            'grade': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 5th Grade',
            }),
        }

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 6 or age > 16:
            raise forms.ValidationError('Student age must be between 6 and 16.')
        return age


class TeacherQuestionForm(forms.ModelForm):
    """
    Teacher-friendly form to create or edit a question along with its 4 choices.
    Simplifies choice management into structured fields with clear validation.
    """

    # Choice 1
    choice_1_text = forms.CharField(
        max_length=255, label='Option A Text',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Joyful or 10'})
    )
    choice_1_icon = forms.CharField(
        max_length=40, required=False, label='Option A Icon (optional)',
        widget=forms.TextInput(attrs={'class': 'form-input font-mono text-sm', 'placeholder': 'e.g. smile, puzzle'})
    )
    choice_1_weight = forms.IntegerField(
        initial=0, label='Option A Weight (for preferences)',
        widget=forms.NumberInput(attrs={'class': 'form-input text-sm', 'min': 0, 'max': 10})
    )

    # Choice 2
    choice_2_text = forms.CharField(
        max_length=255, label='Option B Text',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Sad or 11'})
    )
    choice_2_icon = forms.CharField(
        max_length=40, required=False, label='Option B Icon (optional)',
        widget=forms.TextInput(attrs={'class': 'form-input font-mono text-sm', 'placeholder': 'e.g. user, shapes'})
    )
    choice_2_weight = forms.IntegerField(
        initial=0, label='Option B Weight (for preferences)',
        widget=forms.NumberInput(attrs={'class': 'form-input text-sm', 'min': 0, 'max': 10})
    )

    # Choice 3
    choice_3_text = forms.CharField(
        max_length=255, label='Option C Text',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Sleepy or 12'})
    )
    choice_3_icon = forms.CharField(
        max_length=40, required=False, label='Option C Icon (optional)',
        widget=forms.TextInput(attrs={'class': 'form-input font-mono text-sm', 'placeholder': 'e.g. star, book'})
    )
    choice_3_weight = forms.IntegerField(
        initial=0, label='Option C Weight (for preferences)',
        widget=forms.NumberInput(attrs={'class': 'form-input text-sm', 'min': 0, 'max': 10})
    )

    # Choice 4
    choice_4_text = forms.CharField(
        max_length=255, label='Option D Text',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Angry or 13'})
    )
    choice_4_icon = forms.CharField(
        max_length=40, required=False, label='Option D Icon (optional)',
        widget=forms.TextInput(attrs={'class': 'form-input font-mono text-sm', 'placeholder': 'e.g. heart, lightbulb'})
    )
    choice_4_weight = forms.IntegerField(
        initial=0, label='Option D Weight (for preferences)',
        widget=forms.NumberInput(attrs={'class': 'form-input text-sm', 'min': 0, 'max': 10})
    )

    # For Aptitude questions: which choice index is correct (1, 2, 3, or 4)
    correct_choice = forms.ChoiceField(
        choices=[('1', 'Option A'), ('2', 'Option B'), ('3', 'Option C'), ('4', 'Option D')],
        initial='1',
        widget=forms.RadioSelect(attrs={'class': 'choice-radio'}),
        required=False,
        label='Correct Answer (for Cognitive Aptitude puzzles)',
        help_text='Select which option is marked as correct for scored aptitude questions.'
    )

    class Meta:
        model = Question
        fields = (
            'category',
            'question_type',
            'age_group',
            'difficulty_weight',
            'text',
            'visual_hint',
            'order',
        )
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'age_group': forms.Select(attrs={'class': 'form-select'}),
            'difficulty_weight': forms.Select(
                choices=[(1, 'Level 1 · Easy'), (2, 'Level 2 · Medium'), (3, 'Level 3 · Hard')],
                attrs={'class': 'form-select'}
            ),
            'text': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Type the question or scenario prompt here...',
            }),
            'visual_hint': forms.TextInput(attrs={
                'class': 'form-input font-mono text-sm',
                'placeholder': 'e.g. 2, 4, 6, 8, ? or Ravi > Sam > Mia',
            }),
            'order': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style all standard inputs consistently
        for name, field in self.fields.items():
            if 'class' not in field.widget.attrs and not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-input'

        # If editing an existing question, prefill choices
        if self.instance and self.instance.pk:
            choices = list(self.instance.choices.all()[:4])
            for i, choice in enumerate(choices, start=1):
                self.fields[f'choice_{i}_text'].initial = choice.text
                self.fields[f'choice_{i}_icon'].initial = choice.icon_name
                self.fields[f'choice_{i}_weight'].initial = choice.score_weight
                if choice.is_correct:
                    self.fields['correct_choice'].initial = str(i)

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get('question_type')
        correct_choice = cleaned_data.get('correct_choice')

        if q_type == Question.TYPE_OBJECTIVE and not correct_choice:
            self.add_error('correct_choice', 'Please mark one option as the correct answer for scored puzzles.')

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        question = super().save(commit=commit)
        if not commit:
            return question

        # Extract and save choices
        is_objective = (question.question_type == Question.TYPE_OBJECTIVE)
        correct_idx = self.cleaned_data.get('correct_choice')

        # Existing choices
        existing_choices = list(question.choices.all()[:4])

        choice_data = []
        for i in range(1, 5):
            text = self.cleaned_data.get(f'choice_{i}_text', '').strip()
            if not text:
                continue
            icon = self.cleaned_data.get(f'choice_{i}_icon', '').strip()
            is_correct = is_objective and (str(i) == correct_idx)
            if is_objective:
                weight = 10 if is_correct else 0
            else:
                weight = self.cleaned_data.get(f'choice_{i}_weight', 0)

            choice_data.append({
                'text': text,
                'icon_name': icon,
                'is_correct': is_correct,
                'score_weight': weight,
            })

        for i, data in enumerate(choice_data):
            if i < len(existing_choices):
                choice = existing_choices[i]
                for key, val in data.items():
                    setattr(choice, key, val)
                choice.save()
            else:
                Choice.objects.create(question=question, **data)

        # Remove extra choices if any exist
        if len(existing_choices) > len(choice_data):
            for extra in existing_choices[len(choice_data):]:
                extra.delete()

        return question
