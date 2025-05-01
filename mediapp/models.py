from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from datetime import date

# Custom User model with roles
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')

    def __str__(self):
        return self.username

    @property
    def doctor_profile(self):
        return self.doctor if self.role == 'doctor' else None

# Doctor model, linking to CustomUser
class Doctor(models.Model):
    SPECIALTY_CHOICES = [
        ('general', 'General'),
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('pediatrics', 'Pediatrics'),
    ]
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='doctor',
        db_index=True
    )
    specialty = models.CharField(
        max_length=255,
        choices=SPECIALTY_CHOICES,
        default='general'
    )
    biography = models.TextField(blank=True, default="No biography provided")

    def clean(self):
        if self.user.role != 'doctor':
            raise ValidationError("User must have role 'doctor'.")

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialty or 'No Specialty'}"

# Appointment model
class Appointment(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='appointments',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=255)
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments",
        db_index=True
    )
    date = models.DateField(db_index=True)
    time = models.TimeField()
    voice_call_link = models.URLField(max_length=500, blank=True, null=True)
    video_call_link = models.URLField(max_length=500, blank=True, null=True)

    def clean(self):
        if not (self.patient or self.name or self.email or self.phone):
            raise ValidationError("Either a patient or contact details must be provided.")
        if self.date < date.today():
            raise ValidationError("Appointment date cannot be in the past.")
        if self.patient and self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date', 'time'],
                name='unique_appointment'
            )
        ]
        indexes = [
            models.Index(fields=['date', 'doctor']),
        ]

    def __str__(self):
        return f"Appointment: {self.name or self.patient} with Dr. {self.doctor} on {self.date}"

# PatientReferral model
class PatientReferral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="referrals"
    )
    referring_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="referring_patients"
    )
    referred_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="referred_patients"
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    is_treated = models.BooleanField(default=False)

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")
        if self.referring_doctor == self.referred_doctor:
            raise ValidationError("Referring and referred doctors cannot be the same.")

    def __str__(self):
        return f"Referral for {self.patient} from Dr. {self.referring_doctor} to Dr. {self.referred_doctor} ({self.created_at.date()})"

    @property
    def has_treatment(self):
        return self.medical_records.exists()

# MedicalRecord model
class MedicalRecord(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="medical_records"
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="medical_records"
    )
    diagnosis = models.TextField()
    medication = models.TextField()
    referred_to = models.ForeignKey(
        Doctor,
        null=True,
        blank=True,
        related_name="referrals",
        on_delete=models.SET_NULL
    )
    department_sent_to = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    referral = models.ForeignKey(
        PatientReferral,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records"
    )

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")

    def __str__(self):
        return f"Medical Record for {self.patient} by Dr. {self.doctor} ({self.created_at.date()})"

# Prescription model (new)
class Prescription(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="prescriptions",
        limit_choices_to={'role': 'patient'}
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )
    medication = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date.")

    def __str__(self):
        return f"Prescription for {self.patient} by Dr. {self.doctor} ({self.medication})"

# LabResult model (new)
class LabResult(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="lab_results",
        limit_choices_to={'role': 'patient'}
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="lab_results"
    )
    test_name = models.CharField(max_length=100)
    result_value = models.TextField()
    test_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('Normal', 'Normal'), ('Abnormal', 'Abnormal')])
    report_file = models.FileField(upload_to='lab_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")

    def __str__(self):
        return f"Lab Result for {self.patient} ({self.test_name}) on {self.test_date}"

# PatientNote model (new)
class PatientNote(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="notes",
        limit_choices_to={'role': 'patient'}
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="notes"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")

    def __str__(self):
        return f"Note for {self.patient} by Dr. {self.doctor} ({self.created_at.date()})"

# PatientHistory model (new)
class PatientHistory(models.Model):
    patient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="history",
        limit_choices_to={'role': 'patient'}
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="history"
    )
    event_type = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.patient.role != 'patient':
            raise ValidationError("Patient must have role 'patient'.")

    def __str__(self):
        return f"History event for {self.patient} ({self.event_type}) on {self.created_at.date()}"
    
