from datetime import date, timedelta
import math

class PlanGenerationError(Exception):
    def __init__(self, code="SP-4221", message="Not enough days to build a study plan."):
        self.code = code
        self.message = message
        super().__init__(self.message)

DIFFICULTY_WEIGHTS = {
    'easy': 1,
    'medium': 2,
    'hard': 3
}

TECHNIQUE_SUGGESTIONS = {
    'hard': [
        "Pomodoro Deep Focus: 50m concept breakdown + 10m break",
        "Active Recall: Teach key concepts out loud without looking",
        "Targeted Problem Solving: Work through hardest practice exam questions",
        "Feynman Technique: Identify and simplify difficult topics"
    ],
    'medium': [
        "Spaced Repetition: Review notes from 3 days ago",
        "Practice Drills: Complete sample exercise sets",
        "Mind Mapping: Connect central principles and formulas",
        "Flashcard Testing: Test key terminology and definitions"
    ],
    'easy': [
        "Speed Review: High-level scan of summary chapters",
        "Quiz Testing: Rapid self-quiz on core definitions",
        "Light Consolidation: Formula sheet updates and notes clean-up"
    ]
}

def generate_timetable(subjects, exam_date, hours_per_day, start_date=None):
    """
    Generates a day-by-day timetable up to the exam date.
    - subjects: list of dicts [{'name': 'Math', 'difficulty': 'hard'}, ...]
    - exam_date: date object
    - hours_per_day: positive integer
    - start_date: date object (defaults to today)

    Raises PlanGenerationError('SP-4221') if:
    - exam_date <= today
    - (exam_date - today).days < 3 (must have at least 1 study day + 2 revision days)
    - total available hours < number of subjects
    """
    if start_date is None:
        start_date = date.today()

    if isinstance(exam_date, str):
        exam_date = date.fromisoformat(exam_date)

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    total_days = (exam_date - start_date).days

    # Must be at least 3 days: at least 1 study day and 2 revision days
    if total_days < 3:
        raise PlanGenerationError(
            code="SP-4221",
            message="The exam date is too close or in the past. At least 3 full days are required (minimum 1 study day + 2 reserved revision days)."
        )

    if not subjects:
        raise PlanGenerationError(
            code="400",
            message="At least one subject is required to generate a study plan."
        )

    study_days_count = total_days - 2  # Last 2 days reserved for revision
    total_study_hours = study_days_count * hours_per_day

    if total_study_hours < len(subjects):
        raise PlanGenerationError(
            code="SP-4221",
            message=f"With {study_days_count} study days and {hours_per_day} hours/day ({total_study_hours} total hours), there is not enough time to adequately cover {len(subjects)} subjects."
        )

    # Calculate weights and hour allocations
    cleaned_subjects = []
    total_weight = 0
    for s in subjects:
        name = s.get('name', '').strip()
        diff = s.get('difficulty', 'medium').lower()
        if diff not in DIFFICULTY_WEIGHTS:
            diff = 'medium'
        if name:
            weight = DIFFICULTY_WEIGHTS[diff]
            total_weight += weight
            cleaned_subjects.append({
                'name': name,
                'difficulty': diff,
                'weight': weight
            })

    if not cleaned_subjects:
        raise PlanGenerationError(code="400", message="Please provide valid subject names.")

    # Allocate study hours per subject
    allocated_hours = {}
    hours_left = total_study_hours
    for s in cleaned_subjects:
        # Guarantee at least 1 hour per subject
        raw_hours = max(1, round(total_study_hours * (s['weight'] / total_weight)))
        allocated_hours[s['name']] = raw_hours

    # Adjust rounding differences
    current_sum = sum(allocated_hours.values())
    diff_hours = total_study_hours - current_sum
    if diff_hours != 0:
        # Add/subtract from highest weighted subject
        sorted_by_weight = sorted(cleaned_subjects, key=lambda x: x['weight'], reverse=(diff_hours > 0))
        target_subject = sorted_by_weight[0]['name']
        allocated_hours[target_subject] = max(1, allocated_hours[target_subject] + diff_hours)

    # Build subject hour queue for interleaving
    subject_hours_remaining = {s['name']: allocated_hours[s['name']] for s in cleaned_subjects}
    subject_meta = {s['name']: s for s in cleaned_subjects}

    days_plan = []
    subject_index = 0

    for day_idx in range(study_days_count):
        current_day_date = start_date + timedelta(days=day_idx)
        daily_hours_left = hours_per_day
        day_sessions = []
        session_num = 1

        while daily_hours_left > 0:
            # Pick available subject with remaining hours
            available_subs = [s['name'] for s in cleaned_subjects if subject_hours_remaining[s['name']] > 0]
            if not available_subs:
                # If all allocated hours used up, pick from all subjects
                available_subs = [s['name'] for s in cleaned_subjects]

            # Interleave based on subject_index
            chosen_sub_name = available_subs[subject_index % len(available_subs)]
            subject_index += 1

            # Determine slot duration (1 or 2 hours)
            slot_duration = 2 if (daily_hours_left >= 2 and subject_hours_remaining.get(chosen_sub_name, 0) >= 2) else 1
            slot_duration = min(slot_duration, daily_hours_left)

            if chosen_sub_name in subject_hours_remaining:
                subject_hours_remaining[chosen_sub_name] = max(0, subject_hours_remaining[chosen_sub_name] - slot_duration)

            sub_info = subject_meta[chosen_sub_name]
            techniques = TECHNIQUE_SUGGESTIONS[sub_info['difficulty']]
            technique_picked = techniques[(day_idx + session_num) % len(techniques)]

            day_sessions.append({
                'session_number': session_num,
                'subject': chosen_sub_name,
                'difficulty': sub_info['difficulty'],
                'duration_hours': slot_duration,
                'technique': technique_picked
            })
            daily_hours_left -= slot_duration
            session_num += 1

        days_plan.append({
            'day_number': day_idx + 1,
            'date': current_day_date.isoformat(),
            'formatted_date': current_day_date.strftime('%A, %b %d'),
            'type': 'study',
            'sessions': day_sessions,
            'total_hours': hours_per_day,
            'is_revision': False
        })

    # The last 2 days before the exam are reserved for revision
    rev_day_1_date = exam_date - timedelta(days=2)
    rev_day_2_date = exam_date - timedelta(days=1)

    days_plan.append({
        'day_number': study_days_count + 1,
        'date': rev_day_1_date.isoformat(),
        'formatted_date': rev_day_1_date.strftime('%A, %b %d'),
        'type': 'revision',
        'is_revision': True,
        'total_hours': hours_per_day,
        'title': 'Comprehensive Revision & Mock Exam Simulation',
        'description': 'Synthesize all subjects. Complete a timed practice test covering weak areas across all subjects.',
        'sessions': [
            {
                'session_number': 1,
                'subject': 'All Subjects - Mock Exam',
                'difficulty': 'hard',
                'duration_hours': max(1, hours_per_day // 2),
                'technique': 'Timed mock testing under strict exam conditions'
            },
            {
                'session_number': 2,
                'subject': 'Error Analysis & High-Yield Review',
                'difficulty': 'medium',
                'duration_hours': math.ceil(hours_per_day / 2),
                'technique': 'Active correction of mistakes and formula review'
            }
        ]
    })

    days_plan.append({
        'day_number': study_days_count + 2,
        'date': rev_day_2_date.isoformat(),
        'formatted_date': rev_day_2_date.strftime('%A, %b %d'),
        'type': 'revision',
        'is_revision': True,
        'total_hours': hours_per_day,
        'title': 'Final Polish, Formula Recall & Rest',
        'description': 'Light review only. Re-read summary cheat sheets, pack your exam supplies, hydrate, and get a full 8 hours of sleep.',
        'sessions': [
            {
                'session_number': 1,
                'subject': 'Summary Sheet Review',
                'difficulty': 'easy',
                'duration_hours': max(1, hours_per_day // 2),
                'technique': 'Light flashcard recall and mental walkthrough'
            },
            {
                'session_number': 2,
                'subject': 'Mental Readiness & Prep',
                'difficulty': 'easy',
                'duration_hours': math.ceil(hours_per_day / 2),
                'technique': 'Exam equipment checklist, relaxation, and early sleep'
            }
        ]
    })

    summary = {
        'total_days': total_days,
        'study_days': study_days_count,
        'revision_days': 2,
        'exam_date': exam_date.isoformat(),
        'formatted_exam_date': exam_date.strftime('%A, %b %d, %Y'),
        'hours_per_day': hours_per_day,
        'total_hours': total_days * hours_per_day,
        'subject_allocations': allocated_hours,
        'subjects': cleaned_subjects
    }

    return {
        'summary': summary,
        'days': days_plan
    }
