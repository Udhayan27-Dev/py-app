from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

from .models import StudyPlan
from .services import generate_timetable, PlanGenerationError
from faq.models import ErrorCode

def plan_generator_view(request):
    """
    Plan Generator Page:
    Displays the form with dynamic subject rows, difficulty selections, exam date,
    and study hours per day. Generates timetable and saves StudyPlan.
    """
    error_context = None
    generated_result = None
    study_plan_obj = None

    if request.method == 'POST':
        exam_date_str = request.POST.get('exam_date', '').strip()
        hours_per_day_str = request.POST.get('hours_per_day', '4').strip()

        # Extract multiple subjects from form inputs
        subject_names = request.POST.getlist('subject_name[]')
        subject_diffs = request.POST.getlist('subject_difficulty[]')

        subjects = []
        for name, diff in zip(subject_names, subject_diffs):
            name_clean = name.strip()
            if name_clean:
                subjects.append({
                    'name': name_clean,
                    'difficulty': diff.lower()
                })

        try:
            hours_per_day = int(hours_per_day_str)
            if hours_per_day < 1 or hours_per_day > 18:
                raise ValueError("Hours per day must be between 1 and 18.")

            if not exam_date_str:
                raise ValueError("Please provide a valid exam date.")

            exam_date = date.fromisoformat(exam_date_str)
            today = date.today()

            if exam_date <= today or (exam_date - today).days < 3:
                raise PlanGenerationError(
                    code="SP-4221",
                    message="Not enough days to build a study plan. The exam date is too close or already in the past. At least 3 full days are required (1 study day + 2 revision days)."
                )

            # Generate the timetable
            generated_result = generate_timetable(
                subjects=subjects,
                exam_date=exam_date,
                hours_per_day=hours_per_day,
                start_date=today
            )

            # Ensure session key exists for guests
            if not request.session.session_key:
                request.session.create()
            session_id = request.session.session_key or ""

            # Save to PostgreSQL
            study_plan_obj = StudyPlan.objects.create(
                user=request.user if request.user.is_authenticated else None,
                subjects=subjects,
                exam_date=exam_date,
                hours_per_day=hours_per_day,
                generated_plan=generated_result,
                session_id=session_id
            )

        except PlanGenerationError as e:
            # Look up error details from Postgres ErrorCode table
            err_obj = ErrorCode.objects.filter(code=e.code).first()
            return render(request, 'errors/error_page.html', {
                'error_code': e.code,
                'error_title': err_obj.title if err_obj else 'Study Plan Generation Error',
                'error_message': e.message,
                'suggested_fix': err_obj.suggested_fix if err_obj else 'Choose an exam date at least 3 days in the future.',
                'back_url': '/generate/'
            }, status=422 if e.code == 'SP-4221' else 400)

        except Exception as e:
            err_obj = ErrorCode.objects.filter(code='400').first()
            return render(request, 'errors/error_page.html', {
                'error_code': '400',
                'error_title': 'Invalid Study Plan Request',
                'error_message': str(e),
                'suggested_fix': err_obj.suggested_fix if err_obj else 'Check your inputs and try again.',
                'back_url': '/generate/'
            }, status=400)

    # Defaults for form
    today_iso = date.today().isoformat()

    return render(request, 'planner/generator.html', {
        'generated_result': generated_result,
        'plan': study_plan_obj,
        'today_iso': today_iso,
    })


def plan_detail_view(request, pk):
    """
    View a specific study plan.
    Ownership check: Only the plan's owner or matching guest session can view it.
    Otherwise returns custom 403 page.
    """
    plan = get_object_or_404(StudyPlan, pk=pk)

    # Ownership verification
    if plan.user:
        if plan.user != request.user:
            return render(request, 'errors/403.html', {
                'error_code': '403',
                'error_title': 'Access Forbidden',
                'error_message': 'You do not have permission to view this study plan because it belongs to another user.'
            }, status=403)
    else:
        # Guest plan check
        current_session = request.session.session_key
        if not current_session or plan.session_id != current_session:
            # If logged in, maybe the user wants to claim a session plan
            if not request.user.is_authenticated:
                return render(request, 'errors/403.html', {
                    'error_code': '403',
                    'error_title': 'Access Forbidden',
                    'error_message': 'This plan was created in a different guest session. Sign in to view your saved plans.'
                }, status=403)

    return render(request, 'planner/plan_detail.html', {
        'plan': plan,
        'generated_result': plan.generated_plan
    })


@login_required(login_url='/login/')
def my_plans_view(request):
    """
    List all study plans owned by the logged-in user.
    """
    # Also associate any plans from current guest session to this user
    if request.session.session_key:
        StudyPlan.objects.filter(
            session_id=request.session.session_key,
            user__isnull=True
        ).update(user=request.user)

    plans = StudyPlan.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'planner/my_plans.html', {
        'plans': plans
    })


@login_required(login_url='/login/')
@require_POST
def delete_plan_view(request, pk):
    """
    Delete a study plan owned by the logged-in user.
    Non-owners get custom 403 error page.
    """
    plan = get_object_or_404(StudyPlan, pk=pk)

    if plan.user != request.user:
        return render(request, 'errors/403.html', {
            'error_code': '403',
            'error_title': 'Forbidden',
            'error_message': 'You cannot delete a study plan that does not belong to you.'
        }, status=403)

    plan.delete()
    messages.success(request, 'Study plan has been successfully deleted.')
    return redirect('my_plans')
