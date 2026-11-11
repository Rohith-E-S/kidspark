from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import ChildProfile
from assessments.models import AssessmentSession, Choice, SessionResponse


def _owned_child(request, child_id):
    if request.user.is_staff:
        return get_object_or_404(ChildProfile, id=child_id)
    return get_object_or_404(ChildProfile, id=child_id, parent=request.user)


def _owned_session(request, session_id):
    if request.user.is_staff:
        return get_object_or_404(
            AssessmentSession.objects.select_related('child'),
            id=session_id,
        )
    return get_object_or_404(
        AssessmentSession.objects.select_related('child'),
        id=session_id,
        child__parent=request.user,
    )


@login_required
def select_test(request):
    children = request.user.children.all()
    selected_child = None
    child_id = request.GET.get('child')
    if child_id:
        selected_child = children.filter(id=child_id).first()

    rows = []
    for child in children:
        rows.aphttp://127.0.0.1:8000/pend({
            'child': child,
            'active_session': child.active_session,
            'completed_count': child.completed_count,
            'latest_result': child.latest_result,
        })

    return render(request, 'assessments/select_test.html', {
        'rows': rows,
        'selected_child': selected_child,
        'has_children': bool(rows),
    })


@login_required
def start_test(request, child_id):
    child = _owned_child(request, child_id)

    session = child.active_session
    if session is None:
        session = AssessmentSession.objects.create(child=child)
        messages.success(request, f'New assessment started for {child.name}.')
    else:
        messages.info(request, f'Resuming {child.name}\'s unfinished assessment.')

    return redirect('assessments:session', session_id=session.id)


def _stage_context(session, question=None, index=None, total=None):
    """Everything the quiz stage (full page or HTMX partial) needs."""
    question = question if question is not None else session.next_question()
    answered = session.answered_count
    total = total if total is not None else session.total_questions
    return {
        'session': session,
        'child': session.child,
        'question': question,
        'question_number': (index if index is not None else answered) + 1,
        'answered_count': answered,
        'total_questions': total,
        'progress_percent': round((answered / total) * 100) if total else 0,
        'dots': list(range(1, total + 1)),
        'is_last_question': answered + 1 >= total,
    }


@login_required
def quiz_play(request, session_id):
    session = _owned_session(request, session_id)

    if session.is_completed:
        messages.info(
            request, 'That assessment is already complete — here is the report.'
        )
        return redirect('analytics:report_detail', session_id=session.id)

    if request.method == 'POST':
        return _handle_answer(request, session)

    if not session.total_questions:
        messages.error(
            request,
            f'No questions are available for {session.child.name}\'s age group yet. '
            'Run "python manage.py seed_data".',
        )
        return redirect('assessments:select_test')

    context = _stage_context(session)

    if request.headers.get('HX-Request'):
        return render(request, 'assessments/partials/question_card.html', context)
    return render(request, 'assessments/quiz_play.html', context)


def _handle_answer(request, session):
    question = session.next_question()
    if question is None:
        _finish_session(session)
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = f'/analytics/report/{session.id}/'
            return response
        return redirect('analytics:report_detail', session_id=session.id)

    raw_choice = request.POST.get('choice')
    choice = Choice.objects.filter(id=raw_choice, question=question).first()

    if choice is None:
        context = _stage_context(session, question=question)
        context['error'] = 'Please pick an answer before moving on.'
        if request.headers.get('HX-Request'):
            return render(
                request, 'assessments/partials/question_card.html', context, status=400
            )
        return render(request, 'assessments/quiz_play.html', context, status=400)

    try:
        time_taken = max(1, int(request.POST.get('time_taken', 5)))
    except (TypeError, ValueError):
        time_taken = 5

    SessionResponse.objects.update_or_create(
        session=session,
        question=question,
        defaults={'selected_choice': choice, 'time_taken_seconds': time_taken},
    )

    answered = session.answered_count
    session.current_question_index = answered
    session.save(update_fields=['current_question_index'])

    next_question = session.next_question()
    if next_question is None:
        _finish_session(session)
        target = f'/analytics/report/{session.id}/'
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = target
            return response
        return redirect('analytics:report_detail', session_id=session.id)

    context = _stage_context(session, question=next_question)
    if request.headers.get('HX-Request'):
        return render(request, 'assessments/partials/question_card.html', context)
    return redirect('assessments:session', session_id=session.id)


def _finish_session(session):
    """Mark complete and generate the analytics result exactly once."""
    from analytics.services import generate_assessment_result

    if not session.is_completed:
        session.is_completed = True
        session.completed_at = timezone.now()
        session.save(update_fields=['is_completed', 'completed_at'])
    generate_assessment_result(session)
    return session
