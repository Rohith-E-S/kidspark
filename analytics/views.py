import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from analytics.services import generate_assessment_result
from assessments.models import AssessmentSession


@login_required
def report_detail(request, session_id):
    if request.user.is_staff:
        session = get_object_or_404(
            AssessmentSession.objects.select_related('child', 'child__parent'),
            id=session_id,
        )
    else:
        session = get_object_or_404(
            AssessmentSession.objects.select_related('child', 'child__parent'),
            id=session_id,
            child__parent=request.user,
        )

    if not session.is_completed:
        messages.info(request, 'That assessment is still in progress.')
        return redirect('assessments:session', session_id=session.id)

    result = getattr(session, 'result', None)
    if result is None:
        result = generate_assessment_result(session)

    responses = (
        session.responses
        .select_related('question', 'question__category', 'selected_choice')
        .order_by('question__order', 'id')
    )

    objective_review = []
    preference_review = []
    for response in responses:
        row = {
            'response': response,
            'question': response.question,
            'choice': response.selected_choice,
            'correct': response.selected_choice.is_correct,
        }
        if response.question.is_objective:
            objective_review.append(row)
        else:
            preference_review.append(row)

    objective_answered = len(objective_review)
    objective_correct = sum(1 for row in objective_review if row['correct'])
    objective_accuracy = (
        round((objective_correct / objective_answered) * 100) if objective_answered else 0
    )

    chart_aptitude = {
        'labels': [row['name'] for row in result.aptitude_breakdown],
        'values': [row['score'] for row in result.aptitude_breakdown],
    }
    chart_interest = {
        'labels': [row['name'] for row in result.interest_breakdown],
        'values': [row['score'] for row in result.interest_breakdown],
    }

    return render(request, 'analytics/report_detail.html', {
        'session': session,
        'child': session.child,
        'result': result,
        'objective_review': objective_review,
        'preference_review': preference_review,
        'objective_answered': objective_answered,
        'objective_correct': objective_correct,
        'objective_accuracy': objective_accuracy,
        'aptitude_breakdown': result.aptitude_breakdown,
        'interest_breakdown': result.interest_breakdown,
        'chart_aptitude_json': json.dumps(chart_aptitude),
        'chart_interest_json': json.dumps(chart_interest),
        'activities': result.recommended_activities,
        'future_domains': result.recommended_future_domains,
    })


@login_required
def all_reports(request):
    """Every completed assessment belonging to the signed-in parent."""
    sessions = (
        AssessmentSession.objects
        .filter(child__parent=request.user, is_completed=True)
        .select_related('child')
        .order_by('-completed_at')
    )
    rows = [{'session': session, 'result': getattr(session, 'result', None)}
            for session in sessions]
    return render(request, 'analytics/all_reports.html', {'rows': rows})
