from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Faculty(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name

class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return f"{self.name} ({self.faculty.code})"

class Session(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g., "2023/24"
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    is_current = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    level = models.IntegerField(choices=[(100, '100L'), (200, '200L'), (300, '300L'), (400, '400L'), (500, '500L'), (600, '600L')])
    
    class Meta:
        unique_together = ['department', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Student(models.Model):
    matric_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200,default='test') 
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level = models.IntegerField(choices=[(100, '100L'), (200, '200L'), (300, '300L'), (400, '400L'), (500, '500L'), (600, '600L')])
    session_admitted = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='admitted_students')
    
    def __str__(self):
        return f"{self.matric_number} - {self.name}"

class Result(models.Model):
    SEMESTER_CHOICES = [
        ('First', 'First Semester'),
        ('Second', 'Second Semester'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    test_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'course', 'session', 'semester']
        ordering = ['student__matric_number', 'course__code']
    
    def save(self, *args, **kwargs):
        # Auto-calculate total score if both test and exam scores are provided
        if self.test_score is not None and self.exam_score is not None:
            self.total_score = self.test_score + self.exam_score
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student.matric_number} - {self.course.code} - {self.total_score}"