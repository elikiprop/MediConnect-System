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
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
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
        messages.error(request, "Only doctors can access this dashboard.")
        return redirect('home')
        
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found. Please contact an administrator.")
        return redirect('home')
    
    # Get pending referrals where this doctor is the referred doctor
    pending_referrals = PatientReferral.objects.filter(
        referred_doctor=doctor,
        status='pending'
    ).order_by('-created_at')
    
    # Get all referrals involving this doctor (either as referring or referred)
    referrals = PatientReferral.objects.filter(
        referred_doctor=doctor
    ).order_by('-created_at')
    
    # Get recent medical records created by this doctor
    records = MedicalRecord.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:10]  # Limit to recent 10
    
    # Get upcoming appointments for this doctor
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date__gte=datetime.now().date()  # Only future appointments
    ).order_by('date', 'time')[:10]  # Limit to next 10
    
    # Get all patients (for the add medical record dropdown)
    patients = CustomUser.objects.filter(role='patient').order_by('username')
    
    # Build the context with all required variables
    context = {
        'pending_referrals': pending_referrals,
        'referrals': referrals,
        'records': records,
        'appointments': appointments,
        'patients': patients,
        'doctor': doctor
    }
    
    return render(request, 'doctor_dashboard.html', context)

@login_required(login_url='login')
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this dashboard.")
        return redirect('home')
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
        return redirect('home')

    if record_id:  # Editing
        record = get_object_or_404(MedicalRecord, id=record_id, doctor=doctor)
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

# Generate Medical Record PDF
@login_required(login_url='login')
def generate_pdf(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)
    
    # Check if user has permission to view this record
    if not (request.user == record.patient or 
            request.user == record.doctor.user or 
            request.user.role == 'admin'):
        messages.error(request, "You don't have permission to access this record.")
        return redirect('home')
        
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
                
                # Notify doctor about rescheduled appointment
                doctor_email = get_doctor_email(appointment.doctor)
                if doctor_email:
                    send_email_notification(
                        doctor_email,
                        "Appointment Rescheduled",
                        f"Patient {appointment.patient.get_full_name() or appointment.patient.username} has rescheduled their appointment to {appointment.date} at {appointment.time}."
                    )
                
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
        # Save doctor email before deleting for notification
        doctor_email = get_doctor_email(appointment.doctor)
        
        # Save info for confirmation message
        doctor_name = appointment.doctor.user.get_full_name() or appointment.doctor.user.username
        appointment_date = appointment.date
        appointment_time = appointment.time
        
        # Delete appointment
        appointment.delete()
        
        # Notify doctor about canceled appointment
        if doctor_email:
            send_email_notification(
                doctor_email,
                "Appointment Canceled",
                f"Patient {request.user.get_full_name() or request.user.username} has canceled their appointment scheduled for {appointment_date} at {appointment_time}."
            )
        
        messages.success(request, f"Appointment with Dr. {doctor_name} on {appointment_date} at {appointment_time} has been canceled successfully.")
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
                selected_doctor = form.cleaned_data['doctor']
                
                # Check if patient already has an appointment with this doctor on the same day/time
                if request.user.is_authenticated and request.user.role == 'patient':
                    existing_appointment = Appointment.objects.filter(
                        patient=request.user,
                        doctor=selected_doctor,
                        date=appointment_date,
                        time=appointment_time
                    ).exists()
                    
                    if existing_appointment:
                        messages.error(request, "You already have an appointment with this doctor at this time.")
                        return render(request, "appointment.html", {"form": form})
                
                # Use the default Google Meet link instead of generating a unique one
                default_meet_link = "https://meet.google.com/bdu-vfen-nwx"
                
                appointment = Appointment(
                    name=form.cleaned_data['name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    department=form.cleaned_data['department'],
                    doctor=selected_doctor,
                    date=appointment_date,
                    time=appointment_time,
                    patient=request.user if request.user.is_authenticated and request.user.role == 'patient' else None,
                    voice_call_link=default_meet_link,
                    video_call_link=default_meet_link
                )
                appointment.clean()
                appointment.save()
                
                # Notify patient and doctor with error handling
                try:
                    send_mail(
                        "Appointment Confirmation",
                        f"Your appointment with Dr. {selected_doctor.user.get_full_name() or selected_doctor.user.username} is confirmed for {appointment_date} at {appointment_time}. Video link: {default_meet_link}",
                        settings.DEFAULT_FROM_EMAIL,
                        [form.cleaned_data['email']],
                        fail_silently=True
                    )
                    
                    doctor_email = selected_doctor.user.email
                    if doctor_email:
                        send_mail(
                            "New Appointment",
                            f"New appointment scheduled with {form.cleaned_data['name']} for {appointment_date} at {appointment_time}. Video link: {default_meet_link}",
                            settings.DEFAULT_FROM_EMAIL,
                            [doctor_email],
                            fail_silently=True
                        )
                except Exception as e:
                    print(f"Email sending error: {str(e)}")
                
                messages.success(request, "Appointment booked successfully!")
                return redirect('view_appointments' if request.user.is_authenticated and request.user.role == 'patient' else 'home')
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
    appointments = Appointment.objects.filter(patient=request.user).order_by('date', 'time')
    return render(request, "view_appointments.html", {"appointments": appointments})

# Call Notifications
@login_required(login_url='login')
def notify_doctor(request, appointment_id, call_type):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: only the patient or admin should be able to initiate calls
    if not (request.user == appointment.patient or request.user.role == 'admin'):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect('home')
    
    subject = f"Patient {appointment.name or appointment.patient.username} {'Joined Video Call' if call_type == 'video' else 'is Calling'}"
    body = f"Meet Link: {appointment.video_call_link}" if call_type == 'video' else f"Phone: {appointment.phone}"
    
    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(doctor_email, subject, body)
    
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
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")

# Voice and Video Call Views
def start_video_call(request):
    return render(request, 'start_video_call.html')

def start_voice_call(request):
    return render(request, 'start_voice_call.html')

def notify_doctor_video_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: only the patient or admin should be able to initiate calls
    if not (request.user == appointment.patient or request.user.role == 'admin'):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect('home')
    
    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(
            doctor_email,
            f"Patient {appointment.name or appointment.patient.username} Joined Video Call",
            f"Meet Link: {appointment.video_call_link}"
        )
    
    return redirect(appointment.video_call_link)

def notify_doctor_voice_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: only the patient or admin should be able to initiate calls
    if not (request.user == appointment.patient or request.user.role == 'admin'):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect('home')
    
    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(
            doctor_email,
            f"Patient {appointment.name or appointment.patient.username} is Calling",
            f"Phone: {appointment.phone}"
        )
    
    return redirect(f"tel:{appointment.phone}")

# Update Medical Record
def update_medical_record(request, record_id):
    if request.user.role != 'doctor':
        # Check if AJAX request
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
        return redirect('home')
    
    # Get the record and check permissions
    record = get_object_or_404(MedicalRecord, id=record_id)
    if record.doctor != doctor:
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
            return JsonResponse({'status': 'success', 'message': 'Medical record updated successfully!'})
        
        messages.success(request, "Medical record updated successfully!")
        return redirect('doctor_dashboard')
    
    # If it's not a POST request, redirect to dashboard
    return redirect('doctor_dashboard')

# Delete Medical Record
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
            request.user.role == 'admin'):
            
            # Save info for confirmation message
            patient_name = record.patient.get_full_name() or record.patient.username
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
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')
    elif request.user.role == 'patient':
        return redirect('patient_dashboard')
    else:
        return redirect('home')

# Patient Referral
@login_required
def refer_patient(request):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can refer patients.")
        return redirect('home')
    
    # Get the doctor profile associated with the current user
    try:
        referring_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You don't have a doctor profile.")
        return redirect('home')
    
    if request.method == 'POST':
        # Create a modified POST data that includes referring_doctor
        post_data = request.POST.copy()  # Make a mutable copy
        post_data['referring_doctor'] = referring_doctor.id  # Set referring_doctor ID explicitly
        
        form = PatientReferralForm(post_data)
        if form.is_valid():
            try:
                # Create but don't save the instance yet
                referral = form.save(commit=False)
                # Double-check that referring_doctor is set
                referral.referring_doctor = referring_doctor
                
                # Set initial status
                referral.status = 'pending'
                
                # Now save the referral
                referral.save()
                
                # Notify referred doctor about the referral
                referred_doctor = referral.referred_doctor
                if referred_doctor and hasattr(referred_doctor, 'user') and referred_doctor.user.email:
                    send_email_notification(
                        referred_doctor.user.email,
                        "New Patient Referral",
                        f"You have received a patient referral from Dr. {referring_doctor.user.get_full_name() or referring_doctor.user.username}."
                    )
                
                messages.success(request, "Patient referred successfully!")
                return redirect('doctor_dashboard')
            except Exception as e:
                messages.error(request, f"Error referring patient: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
            # For debugging
            print(f"Form errors: {form.errors}")
    else:
        form = PatientReferralForm(initial={'referring_doctor': referring_doctor.id})
    
    # Get all patients and doctors for dropdowns
    patients = CustomUser.objects.filter(role='patient')
    doctors = Doctor.objects.exclude(user=request.user)  # Exclude current doctor
    
    return render(request, 'refer_patient.html', {
        'form': form,
        'patients': patients,
        'doctors': doctors
    })

# Update Referral Status
@login_required
def update_referral_status(request, referral_id):
    if request.user.role != 'doctor':
        messages.error(request, "Only doctors can update referral statuses.")
        return redirect('home')
    
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You don't have a doctor profile.")
        return redirect('home')
    
    if request.method == 'POST':
        referral_obj = get_object_or_404(PatientReferral, id=referral_id)
        new_status = request.POST.get('status')
        
        # Validate status value
        if new_status not in ['pending', 'accepted', 'rejected']:
            messages.error(request, "Invalid status value.")
            return redirect('doctor_dashboard')
        
        # Check if doctor is the referred doctor
        if referral_obj.referred_doctor != doctor:
            messages.error(request, "You can only update referrals that were sent to you.")
            return redirect('doctor_dashboard')
        
        # Update the status
        old_status = referral_obj.status
        referral_obj.status = new_status
        referral_obj.save()
        
        # Notify referring doctor about status change - with error handling
        referring_doctor = referral_obj.referring_doctor
        if referring_doctor and hasattr(referring_doctor, 'user') and referring_doctor.user.email:
            try:
                send_mail(
                    f"PatientReferral Status Updated to {new_status.capitalize()}",
                    f"A referral you made has been {new_status} by Dr. {doctor.user.get_full_name() or doctor.user.username}.",
                    settings.DEFAULT_FROM_EMAIL,
                    [referring_doctor.user.email],
                    fail_silently=True  # This prevents SMTP errors from breaking the flow
                )
            except Exception as e:
                # Log the error but continue execution
                print(f"Email sending error: {str(e)}")
        
        messages.success(request, f"Referral status updated from {old_status} to {new_status}.")
    
    return redirect('doctor_dashboard')