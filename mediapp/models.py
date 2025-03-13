from django.db import models
from django.contrib.auth.models import User


class Appointment(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    department = models.CharField(max_length=255)
    doctor = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    google_meet_link = models.URLField(default="https://meet.google.com/bdu-vfen-nwx")  # Default Meet link

    def __str__(self):
        return f"Appointment: {self.name} with {self.doctor} on {self.date}"


class MedicalRecord(models.Model):
    patient_name = models.CharField(max_length=255)
    doctor_name = models.CharField(max_length=255)
    diagnosis = models.TextField()
    medication = models.TextField()
    referred_to = models.CharField(max_length=255, blank=True, null=True)  # Optional
    department_sent_to = models.CharField(max_length=255, blank=True, null=True)  # Optional
    created_at = models.DateTimeField(auto_now_add=True)  # Auto add timestamp

    def __str__(self):
        return f"Medical Record: {self.patient_name} - {self.doctor_name} ({self.created_at.date()})"


class PatientReferral(models.Model):
    patient_name = models.CharField(max_length=255)
    referring_doctor = models.CharField(max_length=255)
    referred_doctor = models.CharField(max_length=255)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Auto add timestamp

    def __str__(self):
        return f"Referral: {self.patient_name} from {self.referring_doctor} to {self.referred_doctor} ({self.created_at.date()})"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
