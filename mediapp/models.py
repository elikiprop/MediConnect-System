from django.db import models

class Appointment(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=100)
    doctor = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    
    def __str__(self):
        return f"{self.name} - {self.doctor} on {self.date}"
