from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from datetime import datetime
import pdfkit
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.contrib import messages
from .forms import DoctorRegistrationForm, RegisterForm, LoginForm, MedicalRecordForm, PatientReferralForm, ContactForm, AppointmentForm
from .models import Appointment, MedicalRecord, CustomUser, Doctor, PatientReferral
from .utils import send_email_notification, get_doctor_email
import uuid

# Home Page
@login_required(login_url='login')
def home(request):
    return render(request, "index.html")

# Static Pages
def about(request):
    return render(request, "about.html")

def appointment(request):
    form = AppointmentForm()
    return render(request, "appointment.html", {"form": form})

def blog(request):
    return render(request, "blog.html")

def detail(request):
    return render(request, "detail.html")

def price(request):
    return render(request, "price.html")

def search(request):
    return render(request, "search.html")

def service(request):
    return render(request, "service.html")

def team(request):
    return render(request, "team.html")

def testimonial(request):
    return render(request, "testimonial.html")

# Contact Form
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name, email, subject, message = form.cleaned_data.values()
            send_mail(
                f"New Contact Form Submission: {subject}",
                f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                email, ['elikiprop42@gmail.com'], fail_silently=False
            )
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})

# Dashboard Views
@login_required(login_url='login')
def patient_dashboard(request):
    if request.user.role != 'patient':
        messages.error(request, "Only patients can access this page.")
        return redirect('home')
    records = MedicalRecord.objects.filter(patient=request.user)
    appointments = Appointment.objects.filter(patient=request.user)
    return render(request, "patient_dashboard.html", {
        "records": records,
        "appointments": appointments
    })

@login_required(login_url='login')
def doctor_dashboard(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can access this page.")
        return redirect('home')
    records = MedicalRecord.objects.filter(doctor__user=request.user)
    patients = CustomUser.objects.filter(role='patient')
    referrals = PatientReferral.objects.filter(referring_doctor__user=request.user)
    appointments = Appointment.objects.filter(doctor__user=request.user)
    return render(request, "doctor_dashboard.html", {
        "records": records,
        "patients": patients,
        "referrals": referrals,
        "appointments": appointments
    })

@login_required(login_url='login')
def admin_dashboard(request):
    appointments = Appointment.objects.all().order_by("-date", "-time")
    return render(request, "admin_dashboard.html", {"appointments": appointments})

# Add/Edit Medical Record
@login_required(login_url='login')
def add_medical_record(request, patient_id=None, record_id=None):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can add or edit medical records.")
        return redirect('home')
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You do not have a doctor profile.")
        return redirect('doctor_dashboard')

    if record_id:  # Editing
        record = get_object_or_404(MedicalRecord, id=record_id, doctor__user=request.user)
        patient = record.patient
        is_edit = True
    else:  # Adding
        try:
            patient = CustomUser.objects.get(id=patient_id, role='patient')
        except CustomUser.DoesNotExist:
            messages.error(request, "Patient not found or not a valid patient.")
            return redirect('doctor_dashboard')
        record = None
        is_edit = False

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            try:
                medical_record = form.save(commit=False)
                medical_record.patient = patient
                medical_record.doctor = doctor
                medical_record.save()
                messages.success(request, f"Medical record {'updated' if is_edit else 'added'} successfully!")
                return redirect('doctor_dashboard')
            except Exception as e:
                messages.error(request, f"Error saving record: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MedicalRecordForm(instance=record, initial={
            'patient': patient,
            'doctor': doctor
        } if not record else None)

    return render(request, 'add_medical_record.html', {'form': form, 'patient': patient, 'is_edit': is_edit})

# Refer a Patient
@login_required(login_url='login')
def refer_patient(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can refer patients.")
        return redirect('home')
    try:
        referring_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You do not have a doctor profile.")
        return redirect('doctor_dashboard')
    if request.method == 'POST':
        form = PatientReferralForm(request.POST)
        if form.is_valid():
            try:
                referral = form.save(commit=False)
                referral.referring_doctor = referring_doctor
                if referral.referred_doctor == referring_doctor:
                    form.add_error("referred_doctor", "Referring and referred doctors cannot be the same.")
                    return render(request, "refer_patient.html", {'form': form})
                referral.save()
                messages.success(request, "Referral submitted successfully!")
                return redirect('doctor_dashboard')
            except Exception as e:
                messages.error(request, f"Error saving referral: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientReferralForm(initial={'referring_doctor': referring_doctor})
    return render(request, "refer_patient.html", {'form': form})

# Success Page
def success_page(request):
    messages.success(request, "Action completed successfully!")
    return redirect('doctor_dashboard')

# Generate Medical Record PDF
@login_required(login_url='login')
def generate_pdf(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)
    html = render_to_string("medical_record_pdf.html", {"record": record})
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    pdf = pdfkit.from_string(html, False, configuration=config)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{record.patient.username}_record.pdf"'
    return response

# Appointment Actions
@login_required(login_url='login')
def reschedule_appointment(request, appointment_id):
    if request.user.role != 'patient':
        messages.error(request, "Only patients can reschedule appointments.")
        return redirect('home')
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            try:
                appointment = form.save(commit=False)
                appointment.clean()
                appointment.save()
                messages.success(request, "Appointment rescheduled successfully!")
                return redirect('view_appointments')
            except forms.ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForm(instance=appointment)
    return render(request, 'reschedule_appointment.html', {'form': form, 'appointment': appointment})

@login_required(login_url='login')
def delete_appointment(request, appointment_id):
    if request.user.role != 'patient':
        messages.error(request, "Only patients can delete appointments.")
        return redirect('home')
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, "Appointment deleted successfully!")
        return redirect('view_appointments')
    return redirect('view_appointments')

@login_required(login_url='login')
def book_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            try:
                appointment_date = form.cleaned_data['date']
                appointment_time = form.cleaned_data['time']
                unique_id = str(uuid.uuid4())
                appointment = Appointment(
                    name=form.cleaned_data['name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    department=form.cleaned_data['department'],
                    doctor=form.cleaned_data['doctor'],
                    date=appointment_date,
                    time=appointment_time,
                    patient=request.user if request.user.is_authenticated and request.user.role == 'patient' else None,
                    voice_call_link=f"https://example.com/voice-call/{unique_id}",
                    video_call_link=f"https://example.com/video-call/{unique_id}"
                )
                appointment.clean()
                appointment.save()
                send_email_notification(
                    form.cleaned_data['email'],
                    "Appointment Confirmation",
                    f"Your appointment with Dr. {appointment.doctor.user.username} is confirmed."
                )
                send_email_notification(
                    get_doctor_email(appointment.doctor),
                    "New Appointment",
                    f"New appointment scheduled with {form.cleaned_data['name']}."
                )
                messages.success(request, "Appointment booked successfully!")
                return redirect('view_appointments')
            except forms.ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForm()
    return render(request, "appointment.html", {"form": form})

@login_required(login_url='login')
def view_appointments(request):
    if request.user.role != 'patient':
        messages.error(request, "Only patients can view appointments.")
        return redirect('home')
    appointments = Appointment.objects.filter(patient=request.user)
    return render(request, "view_appointments.html", {"appointments": appointments})

# Call Notifications
@login_required(login_url='login')
def notify_doctor(request, appointment_id, call_type):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    subject = f"Patient {appointment.name or appointment.patient.username} {'Joined Video Call' if call_type == 'video' else 'is Calling'}"
    body = f"Meet Link: {appointment.video_call_link}" if call_type == 'video' else f"Phone: {appointment.phone}"
    send_email_notification(get_doctor_email(appointment.doctor), subject, body)
    redirect_url = appointment.video_call_link if call_type == 'video' else f"tel:{appointment.phone}"
    return redirect(redirect_url)

# Authentication
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            role = user.role
            if role == 'doctor':
                return redirect('doctor_dashboard')
            elif role == 'patient':
                return redirect('patient_dashboard')
            elif role == 'admin':
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Unknown user role.')
                return redirect('login')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect("login")

# Placeholder Views (Comment out unless needed)
"""
@login_required(login_url='login')
def diagnose_patient(request, appointment_id):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can diagnose patients.")
        return redirect('home')
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor__user=request.user)
    if request.method == 'POST':
        try:
            diagnosis = request.POST.get('diagnosis')
            medication = request.POST.get('medication')
            recommendations = request.POST.get('recommendations')
            if not diagnosis or not medication:
                messages.error(request, "Diagnosis and medication are required.")
                return render(request, "diagnose_patient.html", {'appointment': appointment})
            MedicalRecord.objects.create(
                patient=appointment.patient,
                doctor=appointment.doctor,
                diagnosis=diagnosis,
                medication=medication
            )
            messages.success(request, "Diagnosis saved successfully!")
            return redirect('doctor_dashboard')
        except Exception as e:
            messages.error(request, f"Error saving diagnosis: {str(e)}")
    return render(request, "diagnose_patient.html", {'appointment': appointment})

@login_required(login_url='login')
def medical_records(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can view medical records.")
        return redirect('home')
    records = MedicalRecord.objects.filter(doctor__user=request.user).order_by('-created_at')
    return render(request, "medical_records.html", {'records': records})

@login_required(login_url='login')
def view_patient_records(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can view patient records.")
        return redirect('home')
    records = MedicalRecord.objects.filter(doctor__user=request.user).order_by('-created_at')
    patient_records = [{
        'id': record.id,
        'patient_name': record.patient.get_full_name() or record.patient.username,
        'doctor_name': record.doctor.user.get_full_name() or record.doctor.user.username,
        'diagnosis': record.diagnosis,
        'medication': record.medication
    } for record in records]
    return render(request, "view_patient_records.html", {'patient_records': patient_records})
"""

def start_video_call(request):
    return render(request, 'start_video_call.html')

def start_voice_call(request):
    return render(request, 'start_voice_call.html')

def notify_doctor_video_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    send_email_notification(
        get_doctor_email(appointment.doctor),
        f"Patient {appointment.name} Joined Video Call",
        f"Meet Link: {appointment.video_call_link}"
    )
    return redirect(appointment.video_call_link)

def notify_doctor_voice_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    send_email_notification(
        get_doctor_email(appointment.doctor),
        f"Patient {appointment.name} is Calling",
        f"Phone: {appointment.phone}"
    )
    return redirect(f"tel:{appointment.phone}")

# Add this new function to your views.py file

def update_medical_record(request, record_id):
    if request.user.role != 'doctor':
        # Check if AJAX request using the proper method for newer Django versions
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Only doctors can edit medical records.'})
        messages.error(request, "Only doctors can edit medical records.")
        return redirect('home')
    
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'You do not have a doctor profile.'})
        messages.error(request, "You do not have a doctor profile.")
        return redirect('doctor_dashboard')
    
    # Get the record and check permissions
    record = get_object_or_404(MedicalRecord, id=record_id)
    if record.doctor.user != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'You can only edit your own medical records.'})
        messages.error(request, "You can only edit your own medical records.")
        return redirect('doctor_dashboard')
    
    if request.method == 'POST':
        # Update only the fields that are submitted
        if 'diagnosis' in request.POST:
            record.diagnosis = request.POST.get('diagnosis')
        if 'medication' in request.POST:
            record.medication = request.POST.get('medication')
        
        # Add any other fields you want to update here
        
        record.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        messages.success(request, "Medical record updated successfully!")
        return redirect('doctor_dashboard')
    
    # If it's not a POST request, redirect to dashboard
    return redirect('doctor_dashboard')

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import MedicalRecord

@login_required
def delete_record(request, record_id):
    """
    Delete a medical record by ID.
    Supports both regular POST requests and AJAX requests.
    Only allows deletion if the user is authorized (either the patient, the doctor, or an admin).
    """
    if request.method == 'POST':
        record = get_object_or_404(MedicalRecord, id=record_id)
        
        # Authorization check - only allow if user is the patient, the doctor, or has admin rights
        if (request.user == record.patient or 
            request.user == record.doctor.user or 
            request.user.is_staff):
            
            # Save info for confirmation message
            patient_name = record.patient.username
            date = record.created_at.date()
            
            # Delete the record
            record.delete()
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"Medical record for {patient_name} dated {date} has been deleted successfully."
                })
            
            messages.success(
                request, 
                f"Medical record for {patient_name} dated {date} has been deleted successfully."
            )
        else:
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': "You don't have permission to delete this medical record."
                }, status=403)  # Return 403 Forbidden status
            
            messages.error(
                request, 
                "You don't have permission to delete this medical record."
            )
    
    # For AJAX requests that aren't POST
    if request.method != 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': "Invalid request method. Please use POST to delete records."
        }, status=400)  # Return 400 Bad Request status
    
    # Redirect back to the medical records page for non-AJAX requests
    return redirect('doctor_dashboard')  # Replace with your actual URL name