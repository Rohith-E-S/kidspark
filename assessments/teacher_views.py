from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import ChildProfile, Classroom
from assessments.forms import TeacherQuestionForm
from assessments.models import Category, Choice, Question, SessionResponse
from assessments.palette import CATEGORY_COLORS, CATEGORY_ICONS, DIMENSIONS


@staff_member_required(login_url='accounts:login')
def teacher_dashboard(request):
    """
    Main hub for school teachers to view, filter, and manage question banks.
    Provides at-a-glance distribution metrics and search/filtering.
    """
    categories = Category.objects.all().order_by('pillar', 'code')
    questions = Question.objects.select_related('category').prefetch_related('choices').order_by('order', 'id')

    # Metrics
    total_count = questions.count()
    aptitude_count = questions.filter(question_type=Question.TYPE_OBJECTIVE).count()
    interest_count = questions.filter(question_type=Question.TYPE_PREFERENCE).count()

    age_stats = {
        'ALL': questions.filter(age_group='ALL').count(),
        'JUNIOR': questions.filter(age_group='JUNIOR').count(),
        'MIDDLE': questions.filter(age_group='MIDDLE').count(),
        'SENIOR': questions.filter(age_group='SENIOR').count(),
    }

    # Filters
    selected_pillar = request.GET.get('pillar', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_age = request.GET.get('age_group', '').strip()
    selected_difficulty = request.GET.get('difficulty', '').strip()
    search_query = request.GET.get('q', '').strip()

    if selected_pillar:
        questions = questions.filter(category__pillar=selected_pillar)
    if selected_category:
        questions = questions.filter(category__code=selected_category)
    if selected_age:
        questions = questions.filter(age_group=selected_age)
    if selected_difficulty:
        questions = questions.filter(difficulty_weight=selected_difficulty)
    if search_query:
        questions = questions.filter(
            Q(text__icontains=search_query) |
            Q(visual_hint__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(category__code__icontains=search_query)
        )

    # Question count per dimension
    dimension_counts = {
        cat.code: questions.filter(category=cat).count() if not selected_category else (1 if cat.code == selected_category else 0)
        for cat in categories
    }

    return render(request, 'teacher/dashboard.html', {
        'questions': questions,
        'categories': categories,
        'dimensions': DIMENSIONS,
        'total_count': total_count,
        'filtered_count': questions.count(),
        'aptitude_count': aptitude_count,
        'interest_count': interest_count,
        'age_stats': age_stats,
        'dimension_counts': dimension_counts,
        # Active filter values
        'selected_pillar': selected_pillar,
        'selected_category': selected_category,
        'selected_age': selected_age,
        'selected_difficulty': selected_difficulty,
        'search_query': search_query,
    })


@staff_member_required(login_url='accounts:login')
def teacher_question_create(request):
    """Create a new question with choices via teacher-friendly UI."""
    if request.method == 'POST':
        form = TeacherQuestionForm(request.POST)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Question #{question.order} created successfully in {question.category.name}!')
            return redirect(f"{reverse('assessments:teacher_dashboard')}#q-{question.id}")
    else:
        # Suggest next order
        last_order = Question.objects.order_by('-order').values_list('order', flat=True).first() or 0
        initial_cat = request.GET.get('category')
        initial_data = {'order': last_order + 1}
        if initial_cat:
            cat = Category.objects.filter(code=initial_cat).first()
            if cat:
                initial_data['category'] = cat
                initial_data['question_type'] = Question.TYPE_OBJECTIVE if cat.is_aptitude else Question.TYPE_PREFERENCE

        form = TeacherQuestionForm(initial=initial_data)

    return render(request, 'teacher/question_form.html', {
        'form': form,
        'is_edit': False,
        'title': 'Add New Question',
    })


@staff_member_required(login_url='accounts:login')
def teacher_question_edit(request, question_id):
    """Edit an existing question and its choices."""
    question = get_object_or_404(Question.objects.select_related('category').prefetch_related('choices'), id=question_id)

    if request.method == 'POST':
        form = TeacherQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Question #{question.order} updated successfully!')
            return redirect(f"{reverse('assessments:teacher_dashboard')}#q-{question.id}")
    else:
        form = TeacherQuestionForm(instance=question)

    return render(request, 'teacher/question_form.html', {
        'form': form,
        'question': question,
        'is_edit': True,
        'title': f'Edit Question #{question.order} ({question.category.code})',
    })


@staff_member_required(login_url='accounts:login')
def teacher_question_delete(request, question_id):
    """Safely delete a question after teacher confirmation."""
    question = get_object_or_404(Question, id=question_id)
    response_count = SessionResponse.objects.filter(question=question).count()

    if request.method == 'POST':
        order_num = question.order
        cat_name = question.category.name
        question.delete()
        messages.success(request, f'Question #{order_num} from {cat_name} was removed.')
        return redirect('assessments:teacher_dashboard')

    return render(request, 'teacher/question_delete_confirm.html', {
        'question': question,
        'response_count': response_count,
    })


@staff_member_required(login_url='accounts:login')
def teacher_question_preview(request, question_id):
    """
    Renders an exact student-facing preview of how the question card
    appears to a child during the quiz.
    """
    question = get_object_or_404(
        Question.objects.select_related('category').prefetch_related('choices'),
        id=question_id
    )

    return render(request, 'teacher/question_preview_modal.html', {
        'question': question,
        'choices': question.choices.all(),
    })


# ==============================================================================
# CLASSROOM & STUDENT MANAGEMENT
# ==============================================================================

@staff_member_required(login_url='accounts:login')
def classroom_list(request):
    """View all classrooms managed by the educator or institution."""
    classrooms = Classroom.objects.filter(
        Q(teacher=request.user) | Q(teacher__is_staff=True)
    ).distinct().annotate(
        total_students=Count('students', distinct=True)
    ).order_by('grade', 'name')

    total_classrooms = classrooms.count()
    total_enrolled_students = ChildProfile.objects.filter(classroom__isnull=False).count()

    return render(request, 'teacher/classroom_list.html', {
        'classrooms': classrooms,
        'total_classrooms': total_classrooms,
        'total_enrolled_students': total_enrolled_students,
    })


@staff_member_required(login_url='accounts:login')
def classroom_create(request):
    """Create a new classroom cohort."""
    from assessments.forms import ClassroomForm

    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.save()
            messages.success(request, f'Classroom "{classroom.name}" created with code {classroom.code}!')
            return redirect('assessments:classroom_detail', classroom_id=classroom.id)
    else:
        form = ClassroomForm()

    return render(request, 'teacher/classroom_form.html', {
        'form': form,
        'is_edit': False,
        'title': 'Create New Classroom',
    })


@staff_member_required(login_url='accounts:login')
def classroom_edit(request, classroom_id):
    """Edit an existing classroom's details."""
    from assessments.forms import ClassroomForm

    classroom = get_object_or_404(Classroom, id=classroom_id)

    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            classroom = form.save()
            messages.success(request, f'Classroom "{classroom.name}" updated successfully!')
            return redirect('assessments:classroom_detail', classroom_id=classroom.id)
    else:
        form = ClassroomForm(instance=classroom)

    return render(request, 'teacher/classroom_form.html', {
        'form': form,
        'classroom': classroom,
        'is_edit': True,
        'title': f'Edit Classroom: {classroom.name}',
    })


@staff_member_required(login_url='accounts:login')
def classroom_detail(request, classroom_id):
    """
    Detailed classroom view showing:
    - Enrolled student roster
    - Individual completion statuses (Not Started, In Progress, Completed)
    - Latest persona cards
    - Classroom cohort strengths radar (average across all completed students)
    """
    classroom = get_object_or_404(
        Classroom.objects.prefetch_related('students__sessions'),
        id=classroom_id
    )
    students = classroom.students.all().order_by('name')

    # Student status breakdown
    student_rows = []
    completed_results = []
    not_started_count = 0
    in_progress_count = 0
    completed_count = 0

    for s in students:
        active_sess = s.active_session
        latest_res = s.latest_result
        if latest_res:
            completed_count += 1
            completed_results.append(latest_res)
            status = 'COMPLETED'
        elif active_sess:
            in_progress_count += 1
            status = 'IN_PROGRESS'
        else:
            not_started_count += 1
            status = 'NOT_STARTED'

        student_rows.append({
            'student': s,
            'status': status,
            'active_session': active_sess,
            'latest_result': latest_res,
        })

    # Calculate cohort average strengths across 8 dimensions
    cohort_averages = {
        'LOGICAL': 0, 'VERBAL': 0, 'SPATIAL': 0, 'CRITICAL': 0,
        'STEM': 0, 'ARTS': 0, 'NATURE': 0, 'SOCIAL': 0,
    }
    num_completed = len(completed_results)
    if num_completed > 0:
        for r in completed_results:
            for item in r.aptitude_breakdown:
                code = item['code']
                if code in cohort_averages:
                    cohort_averages[code] += item['score']
            for item in r.interest_breakdown:
                code = item['code']
                if code in cohort_averages:
                    cohort_averages[code] += item['score']

        for code in cohort_averages:
            cohort_averages[code] = round(cohort_averages[code] / num_completed)

    # Class persona distribution
    persona_counts = {}
    for r in completed_results:
        persona = r.persona_title
        persona_counts[persona] = persona_counts.get(persona, 0) + 1

    return render(request, 'teacher/classroom_detail.html', {
        'classroom': classroom,
        'student_rows': student_rows,
        'total_students': students.count(),
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'not_started_count': not_started_count,
        'cohort_averages': cohort_averages,
        'cohort_averages_json': [cohort_averages[code] for code in ['LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL', 'STEM', 'ARTS', 'NATURE', 'SOCIAL']],
        'persona_counts': persona_counts,
    })


@staff_member_required(login_url='accounts:login')
def student_add(request, classroom_id):
    """Add a new student directly into this classroom."""
    from accounts.models import ChildProfile
    from assessments.forms import StudentEnrollmentForm

    classroom = get_object_or_404(Classroom, id=classroom_id)

    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.parent = request.user
            student.classroom = classroom
            student.save()
            messages.success(request, f'Student "{student.name}" enrolled in {classroom.name}!')
            return redirect('assessments:classroom_detail', classroom_id=classroom.id)
    else:
        form = StudentEnrollmentForm(initial={'grade': classroom.grade})

    return render(request, 'teacher/student_form.html', {
        'form': form,
        'classroom': classroom,
        'is_edit': False,
        'title': f'Add Student to {classroom.name}',
    })


@staff_member_required(login_url='accounts:login')
def student_edit(request, student_id):
    """Edit student details from teacher perspective."""
    from accounts.models import ChildProfile
    from assessments.forms import StudentEnrollmentForm

    student = get_object_or_404(ChildProfile, id=student_id)
    classroom = student.classroom

    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'Student "{student.name}" updated!')
            if classroom:
                return redirect('assessments:classroom_detail', classroom_id=classroom.id)
            return redirect('assessments:classroom_list')
    else:
        form = StudentEnrollmentForm(instance=student)

    return render(request, 'teacher/student_form.html', {
        'form': form,
        'classroom': classroom,
        'student': student,
        'is_edit': True,
        'title': f'Edit Student: {student.name}',
    })


@staff_member_required(login_url='accounts:login')
def student_remove(request, student_id):
    """Remove student from classroom (or unenroll)."""
    from accounts.models import ChildProfile

    student = get_object_or_404(ChildProfile, id=student_id)
    classroom = student.classroom

    if request.method == 'POST':
        student_name = student.name
        student.classroom = None
        student.save(update_fields=['classroom'])
        messages.success(request, f'Student "{student_name}" was unenrolled from {classroom.name if classroom else "the class"}.')
        if classroom:
            return redirect('assessments:classroom_detail', classroom_id=classroom.id)
        return redirect('assessments:classroom_list')

    return render(request, 'teacher/student_remove_confirm.html', {
        'student': student,
        'classroom': classroom,
    })

