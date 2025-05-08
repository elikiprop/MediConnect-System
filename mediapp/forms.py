from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Doctor, MedicalRecord, PatientReferral, Appointment
from datetime import datetime, timedelta

class MedicalRecordForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='patient'),
        widget=forms.HiddenInput(),
        required=True  # Changed to True - this is crucial
    )
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        widget=forms.HiddenInput(),
        required=True  # Changed to True - this is crucial
    )
    diagnosis = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=True
    )
    medication = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=True
    )
    referred_to = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Doctor (Optional)",
        required=False
    )
    department_sent_to = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = MedicalRecord
        fields = ['patient', 'doctor', 'diagnosis', 'medication', 'referred_to', 'department_sent_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If instance is provided, make sure referred_to excludes the current doctor
        if 'initial' in kwargs and 'doctor' in kwargs['initial']:
            current_doctor = kwargs['initial']['doctor']
            if current_doctor:
                self.fields['referred_to'].queryset = Doctor.objects.exclude(id=current_doctor.id)

    def clean(self):
        cleaned_data = super().clean()
        referred_to = cleaned_data.get('referred_to')
        department_sent_to = cleaned_data.get('department_sent_to')
        if referred_to and not department_sent_to:
            raise forms.ValidationError("Please specify a department for the referral.")
        if department_sent_to and not referred_to:
            raise forms.ValidationError("Please select a doctor to refer to.")
        return cleaned_data

class PatientReferralForm(forms.ModelForm):
    referred_doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        empty_label="Select Doctor",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = PatientReferral
        fields = ["patient", "referring_doctor", "referred_doctor", "reason", "status", "department"]
        widgets = {
            "patient": forms.Select(attrs={"class": "form-control"}),
            "referring_doctor": forms.HiddenInput(),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = CustomUser.objects.filter(role='patient')
        if user and user.role == 'doctor':
            try:
                self.fields['referring_doctor'].initial = user.doctor
            except Doctor.DoesNotExist:
                raise ValidationError("Logged-in user does not have a doctor profile.")
        if self.instance.pk and self.instance.referring_doctor:
            self.fields['referred_doctor'].queryset = Doctor.objects.exclude(
                id=self.instance.referring_doctor.id
            )

    def clean(self):
        cleaned_data = super().clean()
        referring_doctor = cleaned_data.get("referring_doctor")
        referred_doctor = cleaned_data.get("referred_doctor")
        if referring_doctor == referred_doctor:
            self.add_error("referred_doctor", "Referring and referred doctors cannot be the same.")
        return cleaned_data

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
        required=True
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ["username", "email", "first_name", "last_name", "role", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "password1": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
            "password2": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        if role not in dict(CustomUser.ROLE_CHOICES).keys():
            self.add_error("role", "Invalid role selected.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
            if user.role == "doctor":
                Doctor.objects.get_or_create(
                    user=user,
                    defaults={"specialty": "general", "biography": "No biography provided"}
                )
        return user

class DoctorRegistrationForm(UserCreationForm):
    specialty = forms.ChoiceField(
        choices=Doctor.SPECIALTY_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True
    )
    biography = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "password1": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
            "password2": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = "doctor"
        if commit:
            user.save()
            Doctor.objects.create(
                user=user,
                specialty=self.cleaned_data["specialty"],
                biography=self.cleaned_data.get("biography", "No biography provided")
            )
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your Name"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Your Email"})
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Subject"})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "placeholder": "Message", "rows": 5}),
        min_length=10,
        max_length=1000
    )

    def clean_message(self):
        message = self.cleaned_data.get("message")
        if len(message) < 10:
            raise ValidationError("Message must be at least 10 characters long.")
        return message

class AppointmentForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control bg-light border-0", "placeholder": "Your Name"}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control bg-light border-0", "placeholder": "Your Email"}),
        required=True
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control bg-light border-0", "placeholder": "Phone Number"}),
        required=True
    )
    department = forms.ChoiceField(
        choices=[
            ('', 'Choose Department'),
            ('Emergency Medicine', 'Emergency Medicine'),
            ('General Medicine', 'General Medicine'),
            ('Surgery', 'Surgery'),
            ('Pediatrics', 'Pediatrics'),
            ('Cardiology', 'Cardiology'),
            ('Neurology', 'Neurology'),
            ('Oncology', 'Oncology'),
            ('Orthopedics', 'Orthopedics'),
            
           
        ],
        widget=forms.Select(attrs={"class": "form-select bg-light border-0"}),
        required=True
    )
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        widget=forms.Select(attrs={"class": "form-select bg-light border-0"}),
        empty_label="Select Doctor",
        required=True
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control bg-light border-0", "type": "date", "id": "appointment-date"}),
        required=True
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={"class": "form-control bg-light border-0", "type": "time", "id": "appointment-time"}),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        doctor = cleaned_data.get('doctor')
        if date and time and doctor:
            appointment_datetime = datetime.combine(date, time)
            if appointment_datetime < datetime.now():
                raise forms.ValidationError("Cannot book appointments in the past.")
            start_time = appointment_datetime - timedelta(minutes=30)
            end_time = appointment_datetime + timedelta(minutes=30)
            conflicting_appointments = Appointment.objects.filter(
                doctor=doctor,
                date=date,
                time__range=(start_time.time(), end_time.time())
            )
            if conflicting_appointments.exists():
                raise forms.ValidationError("Doctor is booked within 30 minutes of this time.")
        return cleaned_data
    
    class RescheduleForm(forms.ModelForm):
      class Meta:
        model = Appointment
        fields = ['date', 'time']  # or whatever fields you need