from django.shortcuts import render,render_to_response
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET
from django.template import RequestContext
from django.utils.html import mark_safe
from django.core.mail import send_mail
from django.conf import settings
from .models import meta_User_Job,meta_ip_log
import uuid
import numpy as np
import pandas as pd
import os
import shutil
import json
import pickle
from pathlib import Path
from ipware.ip import get_real_ip
import subprocess as sp
from django_q.tasks import async, result,async_chain,Chain
import datetime
from geolite2 import geolite2
import re
import gzip
import ast
from collections import Counter
from .googledrive_downloader import GoogleDriveDownloader
import requests, requests_ftp
from pipeline.views import data_upload,delete_upload,confirm_urls
from tempfile import gettempdir

reader = geolite2.reader()
web_url=web_url=settings.WEB_URL
error_map={
"DATA":"Data Preparation",
"QC":"Quality Control",
"A5":"Assembly",
"ABUND":"Taxanomic Abundance",
"GM":"Gene Prediction and Clustering",
"EGG":"Functional Annotation and Abundance",
"NONANNO":"Domain Mapping for Genes Predicted but Not Annotated ",
"PARSER":"Parsing Result",
"SYSTEM":"System Error"
}
UPLOAD_BASE_PATH=gettempdir()
DATA=settings.OUTPUT_BASE_DIR
obo_file=str(Path(settings.SUPPLEMENT_APP_BIN).joinpath('go-basic.obo'))


# Create your views here.
def meta_retrieve(request,task_id="not_passed"):
    if(list(meta_User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    else:
        myjob=meta_User_Job.objects.get(user_id=task_id)
        status_dict={}
        status_dict['total_status']=myjob.total_status
        status_dict['quality_check']=myjob.quality_check
        status_dict['a5_status']=myjob.a5_status
        status_dict['abundance_status']=myjob.abundance_status
        status_dict['gene_prediction_status']=myjob.gene_prediction_status
        status_dict['functional_status']=myjob.functional_status
        status_dict['non_annotate_status']=myjob.non_annotate_status
        status_dict['parsing_status']=myjob.parsing_status
        status_dict['task_id']=task_id
    return HttpResponse(json.dumps(status_dict))

def meta_status(request,task_id="not_passed"):
    return render(request,'meta_status.html',{})

def merge_sample(request):
    return render(request,'merge_sample.html',{})
    
def meta_home(request):
    
    return render(request,'meta_home.html',{})

def meta_report(request,task_id="not_passed"):   
    out_dic={}
    
    summary={}
    if(list(meta_User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    task=meta_User_Job.objects.filter(user_id=task_id)[0]
    
    #overview page
    overview={}
    overview['submit_time']=task.submission_time
    overview['start_time']=task.start_time
    overview['end_time']=task.end_time
    
    
    success=1
    total_file=1
    if(task.total_status=="FAILED"):
        success=0
        failed_step=error_map[task.error_log]
        if(task.error_log=="SYSTEM"):
            try:
                Path(DATA+'/'+task_id+'/myjob.tar.gz').resolve()
            except:
                total_file=0
        return render(request,'meta_report.html',
                    {
                     'task_id':task_id,
                     'success':success,
                     'failed_step':failed_step,
                     'overview':overview,
                     'total_file':total_file,
                    })
    elif(task.total_status=="WAITING" or task.total_status=="RUNNING"):
        return render(request,'meta_status.html',{})
    
    basic_dic={
               'success':success,
               'task_id':task_id,
               'overview':overview,
               'total_file':total_file,
              }
              
    with open(DATA+'/'+task_id+'/output_dict', 'rb') as fp:
        out_dic=pickle.load(fp)
    
    out_dic.update(basic_dic)
    
    
    return render(request,'meta_report.html',out_dic)  
    
def meta_result(request):
    
    uid=str(uuid.uuid1())
    #uid="25cd61d2-3e47-11e8-97ff-d89d67f39fa9"
    
    data_path=str(Path(settings.OUTPUT_BASE_DIR).joinpath(uid))
    sfile_path=str(Path('../').resolve().joinpath('src','snakefiles'))
    msg=""
    
    try:
        test=request.POST['email']
    except:
        msg="Task submitted page is not allowed to be displayed again. Please check your email for status/result link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    # check illegal characters in upload_id
    upload_id = re.sub(r"[\W]", "", request.POST.get('upload_id'))
    if upload_id == '':
        msg="The upload_id is not found."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})

    if (meta_User_Job.objects.filter(upload_id=upload_id).count()>0):
        msg="You have already uploaded the file. Please check your email for status link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})

    

    #get all the parameter from front end here with dictionary type
    parameters={}
    parameters['upload_id']=upload_id
    parameters['dict_urls']={}  # Dictionary for URL download
    if request.POST.get('upload_method') == "from_url":
        parameters['dict_urls'] = {'R1.fastq': request.POST.get('confirmed_url_R1'), 'R2.fastq': request.POST.get('confirmed_url_R2')}
    
    
    parameters['kraken']={}
    parameters['kraken']=str(request.POST['use_kraken'])
        
    parameters['de_novo']={}
    '''
    #quast settings
    if(request.POST['denovo_setting']=='default'):
        parameters['de_novo']['m_value']="300" #this value should equl min contig thresholds
        parameters['de_novo']['contig_thresholds']="300,1000,5000,10000,25000,50000"
    else:
        contig=[300,1000,5000,10000,25000,50000]
        try:
            user_contig=int(request.POST['contig_thresholds'])
        except:
            msg="QUAST minimum contig-thresholds needs to be an integer >=0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(user_contig<0):
            msg="QUAST minimum contig-thresholds needs to be an integer >=0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        if(user_contig>50000):
            new_contig=str(user_contig)
        elif(user_contig<300):
            new_contig=str(user_contig)+",1000,5000,10000,25000,50000"
        else:
            new_contig=str(user_contig)
            for i in range(0,len(contig)):
                if(user_contig<contig[i]):
                    new_contig=new_contig+","+str(contig[i])
        
        parameters['de_novo']['m_value']=new_contig.split(",")[0]
        parameters['de_novo']['contig_thresholds']=new_contig
    '''
    parameters['taxonomic']={}
    if(request.POST['taxo_setting']=='default'):
        parameters['taxonomic']['file_type']='png'        
    else:
        print(request.POST.getlist('file_type'))
        if(request.POST.getlist('file_type')==[]):
            parameters['taxonomic']['file_type']='png'
        else:
            temp=list(request.POST.getlist('file_type'))
            valid_string="png"
            for i in temp:
                valid_string=valid_string+","+i
            parameters['taxonomic']['file_type']=valid_string
    
    parameters['gene_prediction']={}
    if(request.POST['pred_setting']=="default"):
        parameters['gene_prediction']['cdhit_thresh']="0.97"
    else:
        try:
            float_cdhit=float(request.POST['cdhit_thresh'])
        except:
            msg="CD-HIT clustering threshold must be in range:0.7~1.0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if((float_cdhit>1) or (float_cdhit<0.7)):
            msg="CD-HIT clustering threshold must be in range:0.7~1.0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        parameters['gene_prediction']['cdhit_thresh']=str(request.POST['cdhit_thresh'])
        
    parameters['functional']={}
    if(request.POST['function_setting']=="default"):
        parameters['functional']['bowtie_insert_size']="800"
        parameters['functional']['bowtie_mismatch']="3"
    else:
        try:
            int_bowtie_insert=int(request.POST['bowtie_insert_size'])
            int_bowtie_mismatch=int(request.POST['bowtie_mismatch'])
        except:
            msg="Bowtie insert size -X must be integer in range:250~800 and mismatch (-v) must be integer in range 0~35"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if((int_bowtie_insert)>800 or (int_bowtie_insert)<250):
            msg="Bowtie insert size -X must be integer in range:250~800"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if((int_bowtie_mismatch)>35 or (int_bowtie_mismatch)<0):
            msg="Bowtie mismatch (-v) must be integer in range 0~35"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            
        parameters['functional']['bowtie_insert_size']=str(request.POST['bowtie_insert_size'])
        parameters['functional']['bowtie_mismatch']=str(request.POST['bowtie_mismatch'])
        
    parameters['non_annotate']={}
    if(request.POST['non_annotate_setting']=="default"):
        parameters['non_annotate']['hmmer_e_value']="1E-5"
    else:
        try:
            hm_e_value=str(request.POST['hmmer_e_value'])
        except:
            msg="hmmer e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',hm_e_value)):
            parameters['non_annotate']['hmmer_e_value']=hm_e_value
        else:
            msg="hmmer e value pattern not matched"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    print(parameters)
    
    #parse ip  
    
    ip_address=get_real_ip(request)  #make sure this line work in real environment
    if ip_address is not None:
        print("We have a publicly-routable IP address for client")
        submitted_job_number=meta_User_Job.objects.filter(ip=ip_address,total_status__in=["WAITING","RUNNING"]).count()
        
        if(submitted_job_number>2):  #block more than two jobs from single ip address
            msg="Only 2 tasks are allowed to each IP. We cannot accept it since your 2 tasks are still waiting or running on the system."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        try:
            country=reader.get(ip_address)['country']['names']['en']
        except:
            country="NA"        
    else:
        ip_address="NA"
        country="NA"
        print("We don't have an IP address for client or IP is private")
    
    
    mail=request.POST['email']
    times=datetime.datetime.now()
    
    #save and check again uid and ip
    try:
        meta_User_Job.objects.create(user_id=uid,
                                upload_id=upload_id,
                                ip=ip_address,mail=mail,
                                submission_time=times,
                                start_time=times,
                                end_time=times,
                                )
        meta_ip_log.objects.create(ip=ip_address,country=country,submission_time=times,functions="META")
    except:
        #return email not allowed
        msg="Your email address is not a correct one."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})   

        
    task_id=async('metag_pipeline.tasks.run_meta_pipeline',sfile_path=sfile_path,uid=uid,data_path=data_path,parameters=parameters)
    
    job_numbers=meta_User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    user_status_link="/meta/"+uid+"/status"
    
    #send mail with link
    
    
    send_mail('Task Submitted', 'Your Link:'+web_url+"/meta/"+uid+"/status", None,
    [mail], fail_silently=True)
    
    return render(request,'submit_response.html',
                    {'uid':uid,
                     'job_numbers':job_numbers,
                     'user_status_link':user_status_link})
