from django.shortcuts import render
from django.db.models import Q, Count, Avg
from .models import Result, Department, Session, Student, Course

def result_print_view(request):
    department_id = request.GET.get('department')
    session_id = request.GET.get('session')
    semester = request.GET.get('semester', 'First')
    level = request.GET.get('level')
    
    results = Result.objects.all()
    
    if department_id:
        results = results.filter(student__department_id=department_id)
    if session_id:
        results = results.filter(session_id=session_id)
    if semester:
        results = results.filter(semester=semester)
    if level:
        results = results.filter(course__level=level)
    
    # Order by student matric number and course code
    results = results.select_related(
        'student', 
        'course', 
        'session',
        'student__department',
        'student__department__faculty'
    ).order_by('student__matric_number', 'course__code')
    
    context = {
        'results': results,
        'departments': Department.objects.all(),
        'sessions': Session.objects.all(),
        'selected_department': department_id,
        'selected_session': session_id,
        'selected_semester': semester,
        'selected_level': level,
    }
    
    return render(request, 'results/print_results.html', context)


def graduating_students_report(request):
    """
    Report for graduating students showing courses they passed
    Filters by admission session and graduation session
    A student passes a course if:
    - Average score of both semesters >= threshold (if both semesters exist)
    - Single semester score >= threshold (if only one semester exists)
    """
    admission_session_id = request.GET.get('admission_session')
    graduation_session_id = request.GET.get('graduation_session')
    department_id = request.GET.get('department')
    min_pass_score = float(request.GET.get('min_pass_score', 40))  # Default pass mark is 40
    
    # Get all departments for the filter
    departments = Department.objects.select_related('faculty').all()
    sessions = Session.objects.all().order_by('-start_year')
    
    graduating_data = []
    
    if admission_session_id and graduation_session_id:
        # Get students who were admitted in the specified session
        students_query = Student.objects.select_related(
            'department', 
            'department__faculty', 
            'session_admitted'
        ).filter(session_admitted_id=admission_session_id)
        
        # Filter by department if specified
        if department_id:
            students_query = students_query.filter(department_id=department_id)
        
        students_query = students_query.order_by('department__name', 'matric_number')
        
        # For each student, get their passed courses
        for student in students_query:
            # Get all results for this student up to graduation session
            results = Result.objects.filter(
                student=student,
                session__start_year__lte=Session.objects.get(id=graduation_session_id).start_year
            ).select_related('course', 'session').order_by('course', 'session', 'semester')
            
            # Group results by course and session to calculate averages
            from collections import defaultdict
            course_scores = defaultdict(lambda: {'sessions': defaultdict(dict)})
            
            for result in results:
                course_key = (result.course.id, result.course.code, result.course.name, result.course.level)
                session_key = result.session.id
                semester = result.semester
                
                course_scores[course_key]['sessions'][session_key][semester] = {
                    'score': result.total_score,
                    'session_name': result.session.name
                }
            
            # Determine passed and failed courses
            passed_courses = []
            failed_courses = []
            courses_by_level = {}
            
            for course_key, course_data in course_scores.items():
                course_id, course_code, course_name, course_level = course_key
                
                # For each session this course was taken
                for session_id, semesters in course_data['sessions'].items():
                    first_sem = semesters.get('First')
                    second_sem = semesters.get('Second')
                    
                    # Calculate average or use single semester
                    if first_sem and second_sem:
                        # Both semesters available - calculate average
                        avg_score = (first_sem['score'] + second_sem['score']) / 2
                        display_score = avg_score
                        semester_info = 'Both (Avg)'
                    elif first_sem:
                        # Only first semester
                        avg_score = first_sem['score']
                        display_score = first_sem['score']
                        semester_info = 'First'
                    else:
                        # Only second semester
                        avg_score = second_sem['score']
                        display_score = second_sem['score']
                        semester_info = 'Second'
                    
                    session_name = first_sem['session_name'] if first_sem else second_sem['session_name']
                    
                    course_info = {
                        'code': course_code,
                        'name': course_name,
                        'score': round(display_score, 2),
                        'session': session_name,
                        'semester': semester_info,
                        'level': course_level
                    }
                    
                    # Check if passed
                    if avg_score >= min_pass_score:
                        passed_courses.append(course_info)
                        
                        # Group by level
                        if course_level not in courses_by_level:
                            courses_by_level[course_level] = []
                        courses_by_level[course_level].append(course_info)
                    else:
                        failed_courses.append(course_info)
            
            # Sort courses by level and code
            for level in courses_by_level:
                courses_by_level[level].sort(key=lambda x: x['code'])
            
            # Only include students who have at least some results
            if results.exists():
                graduating_data.append({
                    'student': student,
                    'passed_courses': passed_courses,
                    'failed_courses': failed_courses,
                    'courses_by_level': dict(sorted(courses_by_level.items())),
                    'total_passed': len(passed_courses),
                    'total_failed': len(failed_courses),
                    'total_courses': len(passed_courses) + len(failed_courses),
                })
    
    context = {
        'graduating_data': graduating_data,
        'departments': departments,
        'sessions': sessions,
        'selected_admission_session': admission_session_id,
        'selected_graduation_session': graduation_session_id,
        'selected_department': department_id,
        'min_pass_score': min_pass_score,
    }
    
    return render(request, 'results/graduating_students.html', context)


def student_result_sheet(request, student_id):
    # Individual student result sheet
    pass


def department_results(request, department_id):
    # Department-wide results
    pass

def attendance_sheet_view(request):
    """
    Display attendance sheet for a specific course/class
    Filtered by department, level, and session
    """
    department_id = request.GET.get('department')
    level = request.GET.get('level')
    session_id = request.GET.get('session')
    
    students = Student.objects.all()
    
    # Apply filters
    if department_id:
        students = students.filter(department_id=department_id)
    if level:
        students = students.filter(level=level)
    if session_id:
        students = students.filter(session_admitted_id=session_id)
    
    # Get related data and order by matric number
    students = students.select_related(
        'department', 
        'department__faculty',
        'session_admitted'
    ).order_by('matric_number')
    
    # Get selected objects for display
    selected_department = None
    selected_session = None
    
    if department_id:
        try:
            selected_department = Department.objects.select_related('faculty').get(id=department_id)
        except Department.DoesNotExist:
            pass
    
    if session_id:
        try:
            selected_session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            pass
    
    # Level choices for dropdown
    level_choices = [
        (100, '100L'),
        (200, '200L'),
        (300, '300L'),
        (400, '400L'),
        (500, '500L'),
        (600, '600L')
    ]
    
    context = {
        'students': students,
        'departments': Department.objects.select_related('faculty').all(),
        'sessions': Session.objects.all().order_by('-start_year'),
        'level_choices': level_choices,
        'selected_department': selected_department,
        'selected_department_id': department_id,
        'selected_session': selected_session,
        'selected_session_id': session_id,
        'selected_level': level,
        'student_count': students.count(),
    }
    
    return render(request, 'results/attendance_sheet.html', context)

def student_breakdown_view(request):
    """
    Breakdown of total students per level and per department for a given session.
    """
    from django.db.models import Count

    session_id = request.GET.get('session')
    department_id = request.GET.get('department')   # optional filter

    sessions = Session.objects.all().order_by('-start_year')
    departments = Department.objects.select_related('faculty').all()

    breakdown = []          # list of dicts, one per department
    grand_total = 0
    level_totals = {}       # {level: count} across all departments
    selected_session = None

    LEVEL_CHOICES = [100, 200, 300, 400, 500, 600]

    if session_id:
        try:
            selected_session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            pass

        if selected_session:
            dept_qs = departments
            if department_id:
                dept_qs = dept_qs.filter(id=department_id)

            for dept in dept_qs:
                level_counts = (
                    Student.objects
                    .filter(department=dept, session_admitted=selected_session)
                    .values('level')
                    .annotate(count=Count('id'))
                )
                counts = {row['level']: row['count'] for row in level_counts}
                dept_total = sum(counts.values())

                if dept_total == 0:
                    continue  # skip empty departments

                # accumulate grand totals
                grand_total += dept_total
                for lvl, cnt in counts.items():
                    level_totals[lvl] = level_totals.get(lvl, 0) + cnt

                breakdown.append({
                    'department': dept,
                    'counts': counts,           # {100: 12, 200: 8, ...}
                    'total': dept_total,
                })

    context = {
        'sessions': sessions,
        'departments': departments,
        'selected_session': selected_session,
        'selected_session_id': session_id,
        'selected_department_id': department_id,
        'breakdown': breakdown,
        'level_choices': LEVEL_CHOICES,
        'level_totals': level_totals,
        'grand_total': grand_total,
    }

    return render(request, 'results/student_breakdown.html', context)


import os
import mimetypes
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
from .models import Department, Session


# ---------------------------------------------------------------------------
# Place your downloadable files inside:
#   <your_app>/static/downloads/
# or use MEDIA_ROOT – adjust DOWNLOAD_ROOT below to match your setup.
# ---------------------------------------------------------------------------
DOWNLOAD_ROOT = os.path.join(settings.BASE_DIR, 'results', 'static', 'downloads')

# ---- Resource catalogue ---------------------------------------------------
# Each entry defines one downloadable resource card shown on the page.
# Add / remove entries here whenever you upload new materials.
# ---------------------------------------------------------------------------
RESOURCES = [
    {
        "id": "excel_instructions",
        "title": "Excel Assessment — Instructions",
        "description": (
            "Full exam brief for the Microsoft Excel Skills Assessment. "
            "Read this carefully before opening the practice file. "
            "Covers all 25 questions across Filtering, Sorting, Conditional "
            "Formatting, IF Formulas, SUMIF, Charts and the Bonus section."
        ),
        "filename": "Excel_Assessment_Instructions.docx",
        "icon": "📄",
        "badge": "Instructions",
        "badge_color": "primary",
        "audience": "Excel Assessment students",
    },
    {
        "id": "excel_workbook",
        "title": "Excel Assessment — Practice Workbook",
        "description": (
            "The structured Excel workbook you will submit as your answer. "
            "Each question already has its own dedicated worksheet. "
            "Rename the file to [Your Full Name] — Excel Assessment.xlsx "
            "before submitting to the Class Representative."
        ),
        "filename": "excel_practice_restructured.xlsx",
        "icon": "📊",
        "badge": "Workbook",
        "badge_color": "success",
        "audience": "Excel Assessment students",
    },
]
# ---------------------------------------------------------------------------


def downloads_page(request):
    """
    Renders the student downloads page.
    No authentication is enforced here – add @login_required if needed.
    """
    context = {
        "resources": RESOURCES,
        "page_title": "Student Resources & Downloads",
    }
    return render(request, "results/downloads.html", context)


def download_file(request, file_id):
    """
    Serves a file for download by its resource id.
    Only files declared in RESOURCES above can be served – nothing else
    on the filesystem is reachable through this view.
    """
    resource = next((r for r in RESOURCES if r["id"] == file_id), None)
    if resource is None:
        raise Http404("Resource not found.")

    file_path = os.path.join(DOWNLOAD_ROOT, resource["filename"])

    if not os.path.isfile(file_path):
        raise Http404(
            f"File '{resource['filename']}' has not been uploaded to the server yet. "
            "Please contact your instructor."
        )

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    response = FileResponse(
        open(file_path, "rb"),
        content_type=mime_type,
        as_attachment=True,
        filename=resource["filename"],
    )
    return response