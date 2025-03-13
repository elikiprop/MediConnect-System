from django import forms
from django.contrib.auth.models import User
from .models import MedicalRecord, PatientReferral, UserProfile


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["patient_name", "doctor_name", "diagnosis", "medication", "referred_to", "department_sent_to"]
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control"}),
            "doctor_name": forms.TextInput(attrs={"class": "form-control"}),
            "diagnosis": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "medication": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "referred_to": forms.TextInput(attrs={"class": "form-control"}),
            "department_sent_to": forms.TextInput(attrs={"class": "form-control"}),
        }


class PatientReferralForm(forms.ModelForm):
    referred_doctor = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role="doctor"),  # Only show doctors in dropdown
        empty_label="Select Doctor",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = PatientReferral
        fields = ["patient_name", "referring_doctor", "referred_doctor", "reason"]
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control"}),
            "referring_doctor": forms.TextInput(attrs={"class": "form-control", "readonly": True}),  # Auto-filled by logged-in doctor
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirm_password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash password before saving
        if commit:
            user.save()
            UserProfile.objects.create(user=user, role=self.cleaned_data["role"])  # Assign role
        return user


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
