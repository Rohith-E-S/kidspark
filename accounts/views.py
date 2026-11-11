from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.forms import ChildProfileForm, JoinClassroomForm, KidSparkLoginForm, RegisterForm
from accounts.models import ChildProfile, Classroom

DEMO_USERNAME = 'demo_parent'
DEMO_PASSWORD = 'demo1234'

AVATAR_CLASSES = {
    'indigo': 'bg-indigo-500',
    'rose': 'bg-rose-500',
    'emerald': 'bg-emerald-500',
    'amber': 'bg-amber-500',
    'sky': 'bg-sky-500',
    'violet': 'bg-violet-500',
}


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    from assessments.palette import DIMENSIONS

    return render(request, 'home.html', {
        'demo_username': DEMO_USERNAME,
        'demo_password': DEMO_PASSWORD,
        'dimensions': DIMENSIONS,
    })


class KidSparkLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = KidSparkLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['demo_username'] = DEMO_USERNAME
        context['demo_password'] = DEMO_PASSWORD
        return context


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Your KidSpark account is ready. Add your first child to begin.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def demo_login(request):
    """One-click evaluator login as the pre-seeded demo parent."""
    from django.contrib.auth import authenticate

    user = authenticate(request, username=DEMO_USERNAME, password=DEMO_PASSWORD)
    if user is None:
        messages.error(
            request,
            'Demo account is not seeded yet. Run "python manage.py seed_data" and try again.',
        )
        return redirect('home')
    login(request, user)
    messages.success(request, 'Signed in to the KidSpark demo account.')
    return redirect('accounts:dashboard')


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('home')


@login_required
def dashboard(request):
    children = (
        request.user.children
        .annotate(
            total_tests=Count('sessions', filter=Q(sessions__is_completed=True)),
            active_tests=Count('sessions', filter=Q(sessions__is_completed=False)),
        )
    )
    children = list(children)

    for child in children:
        child.avatar_class = AVATAR_CLASSES.get(child.avatar_color, 'bg-indigo-500')
        child.latest = child.latest_result
        child.in_progress = child.active_session

    completed_total = sum(child.total_tests for child in children)

    strength_counter = {}
    for child in children:
        result = child.latest
        if not result:
            continue
        for row in result.aptitude_breakdown + result.interest_breakdown:
            strength_counter[row['name']] = max(
                strength_counter.get(row['name'], 0), row['score']
            )

    top_strengths = sorted(
        strength_counter.items(), key=lambda item: item[1], reverse=True
    )[:3]

    return render(request, 'accounts/dashboard.html', {
        'children': children,
        'children_count': len(children),
        'completed_total': completed_total,
        'top_strengths': top_strengths,
        'avatar_colors': AVATAR_CLASSES,
    })


@login_required
def child_create(request):
    form = ChildProfileForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        child = form.save(commit=False)
        child.parent = request.user
        if not child.avatar_color:
            child.avatar_color = 'indigo'
        child.save()
        messages.success(request, f'{child.name} is ready to take the assessment.')
        return redirect(reverse('assessments:select_test') + f'?child={child.id}')
    return render(request, 'accounts/child_form.html', {
        'form': form,
        'mode': 'add',
        'title': 'Add a child profile',
    })


@login_required
def child_edit(request, child_id):
    child = get_object_or_404(ChildProfile, id=child_id, parent=request.user)
    form = ChildProfileForm(request.POST or None, instance=child)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{child.name}\'s profile was updated.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/child_form.html', {
        'form': form,
        'child': child,
        'mode': 'edit',
        'title': f'Edit {child.name}',
    })


@login_required
@require_POST
def child_delete(request, child_id):
    child = get_object_or_404(ChildProfile, id=child_id, parent=request.user)
    name = child.name
    child.delete()
    messages.info(request, f'{name}\'s profile and all their reports were removed.')
    return redirect('accounts:dashboard')


@login_required
def join_classroom(request):
    """Allow a parent to enroll their child in a classroom using an educator's join code."""
    children = request.user.children.all()
    if not children.exists():
        messages.info(request, 'Please create a child profile first before joining a classroom.')
        return redirect('accounts:child_create')

    initial = {}
    code_param = request.GET.get('code', '').strip()
    child_id_param = request.GET.get('child')

    if code_param:
        initial['class_code'] = code_param.lstrip('#').upper()
    if child_id_param and children.filter(id=child_id_param).exists():
        initial['child'] = child_id_param

    if request.method == 'POST':
        form = JoinClassroomForm(request.user, request.POST)
        if form.is_valid():
            child = form.cleaned_data['child']
            classroom = form.cleaned_data['class_code']
            if child.classroom == classroom:
                messages.info(request, f'{child.name} is already enrolled in {classroom.name}.')
            else:
                child.classroom = classroom
                child.save(update_fields=['classroom'])
                messages.success(
                    request,
                    f'🎉 {child.name} successfully joined {classroom.name} (Grade: {classroom.grade})!'
                )
            return redirect('accounts:dashboard')
    else:
        form = JoinClassroomForm(request.user, initial=initial)

    return render(request, 'accounts/join_classroom.html', {
        'form': form,
        'children_count': children.count(),
        'code_param': code_param,
    })


@login_required
@require_POST
def leave_classroom(request, child_id):
    """Allow a parent to unenroll their child from a classroom cohort."""
    child = get_object_or_404(ChildProfile, id=child_id, parent=request.user)
    if child.classroom:
        class_name = child.classroom.name
        child.classroom = None
        child.save(update_fields=['classroom'])
        messages.info(request, f'{child.name} has left {class_name}.')
    return redirect('accounts:dashboard')

