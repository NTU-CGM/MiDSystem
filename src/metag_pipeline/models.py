from django.db import models
# Create your models here.

class meta_ip_log(models.Model):
    ip=models.CharField(max_length=25)
    country=models.CharField(max_length=50,default="NA")
    functions=models.CharField(max_length=25,default="NA")
    submission_time=models.DateTimeField(auto_now_add=True)
    
class meta_User_Job(models.Model):
    user_id=models.CharField(max_length=50)
    upload_id=models.CharField(max_length=64)
    ip=models.CharField(max_length=25)
    mail=models.EmailField(max_length=254)
    submission_time=models.DateTimeField(auto_now_add=True)
    start_time=models.DateTimeField(auto_now_add=True)
    end_time=models.DateTimeField(auto_now_add=True)
    total_status=models.CharField(max_length=10,default='WAITING')
    data_preparation_status=models.CharField(max_length=10,default='WAITING')
    quality_check=models.CharField(max_length=10,default='WAITING')
    a5_status=models.CharField(max_length=10,default='WAITING')
    abundance_status=models.CharField(max_length=10,default='WAITING')
    gene_prediction_status=models.CharField(max_length=10,default='WAITING')
    functional_status=models.CharField(max_length=10,default='WAITING')
    non_annotate_status=models.CharField(max_length=10,default='WAITING')
    parsing_status=models.CharField(max_length=10,default='WAITING')
    error_log=models.CharField(max_length=50,default='NA')
