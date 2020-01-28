from django.shortcuts import render,render_to_response
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET
from django.template import RequestContext
from django.utils.html import mark_safe
from django.core.mail import send_mail
from django.conf import settings
from .models import User_Job,ip_log,bac_species
from metag_pipeline.models import meta_User_Job
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
from tempfile import gettempdir

reader = geolite2.reader()
web_url=settings.WEB_URL
# Create your views here.
error_map={
"DATA":"Data Preparation",
"QC":"Quality Control",
"A5":"De Novo Assembly",
"RAG":"Reference-Guided Assembly",
"AUG":"Prediction",
"GM":"Prediction",
"GO":"Functional Annotation",
"TREE":"Phylogenetic Tree",
"PARSER":"Parsing Result",
"SYSTEM":"System Error"
}
UPLOAD_BASE_PATH = gettempdir()
DATA = settings.OUTPUT_BASE_DIR

def data_upload(request):
    if request.method == 'POST':
        upload_id = re.sub(r"[\W]", "", request.POST.get('upload_id'))
        if upload_id == '':
            return render(request,'not_allow.html',{'msg':'No upload id.'})
        upload_path = str(Path(UPLOAD_BASE_PATH).resolve().joinpath(upload_id))
        if 'uploadfile_type1' in request.POST:
            new_file_name = request.POST.get('uploadfile_type1')+'.fastq'
        elif 'uploadfile_type2' in request.POST:
            new_file_name = request.POST.get('uploadfile_type2')+'.fastq'
        else:
            new_file_name = 'reference.fa'
        
        try:
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            upload_raw_file = upload_path+'/'+new_file_name
            
            file = request.FILES['myfile']
            if file.name.endswith('.gz'):
                with open(upload_raw_file, 'wb+') as destination:
                    with gzip.GzipFile(fileobj=file) as source:
                        shutil.copyfileobj(source, destination)     
            else:
                with open(upload_raw_file, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
            file.close()
        except:
            return render(request,'not_allow.html',{'msg':'System Error.'})
        
        return HttpResponse(json.dumps(request.POST))

def delete_upload(request):
    if request.method == 'POST':
        upload_id = re.sub(r"[\W]", "", request.POST.get('upload_id'))
        if upload_id == '':
            return render(request,'not_allow.html',{'msg':'No upload id.'})
        upload_path = str(Path(UPLOAD_BASE_PATH).resolve().joinpath(upload_id))
        if 'uploadfile_type1' in request.POST:
            new_file_name = request.POST.get('uploadfile_type1')+'.fastq'
        elif 'uploadfile_type2' in request.POST:
            new_file_name = request.POST.get('uploadfile_type2')+'.fastq'
        else:
            new_file_name = 'reference.fa'
        
        upload_raw_file = upload_path+'/'+new_file_name
        try:
            if os.path.exists(upload_raw_file):
                os.remove(upload_raw_file)
        except:
            return render(request,'not_allow.html',{'msg':'System Error.'})
        
        return HttpResponse(json.dumps(request.POST))

def confirm_urls(request):
    if request.method == 'POST':
        confirm_result = {'R1': False, 'R2':False, 'Rf': False, 'R1_err':'', 'R2_err':'', 'Rf_err':''}
        for key, val in request.POST.items():
            is_status_ok = False
            is_format_ok = False
            
            if key[:3] == 'url': # e.g., key = url_R1
                m1 = re.search('google\.com.+id=(.+)\&*', val)
                if m1:
                    # use GoogleDriveDownloader module
                    id = m1.group(1)
                    response = GoogleDriveDownloader.get_response(id)
                else:
                    # direct download
                    if not re.match(r'^(http|https|ftp)://', val):
                        val = 'http://'+val
                    requests_ftp.monkeypatch_session()
                    session = requests.Session()
                    response = session.get(val, stream=True)
                    
                # Check file existing
                is_status_ok = response.ok
                if is_status_ok == False:
                    confirm_result[key[-2:]+'_err'] = 'File Not Found'
                else:
                    # Check file format
                    if m1:
                        m2 = re.search('filename="(.+)"', response.headers['Content-Disposition'])
                        file_name = m2.group(1)
                    else:
                        file_name = response.url.split('/')[-1]
                    
                    if key[-2:] == 'Rf':
                        if re.search('\.(fasta|fa|fna)+(\.gz)*$', file_name):
                            is_format_ok = True
                        else:
                            is_format_ok = False
                            confirm_result[key[-2:]+'_err'] = 'Unkown File Format'
                    else: #R1/R2
                        if re.search('\.f(ast)*q(\.gz)*$', file_name):
                            is_format_ok = True
                        else:
                            is_format_ok = False
                            confirm_result[key[-2:]+'_err'] = 'Unkown File Format'
                        
                confirm_result[key[-2:]] = is_status_ok and is_format_ok

        return HttpResponse(json.dumps(confirm_result))

def test(request,task_id):
    status_dict={'test':'This is test.'}
    #return HttpResponse(json.dumps(status_dict))
    return render_to_response('test.html',locals())
    
def home(request):
    print("IP Address for debug-toolbar: " + request.META['REMOTE_ADDR'])
    job_numbers=User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    meta_job_number=meta_User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    return render_to_response('home.html',locals())

def help(request):
    status_dict={'test':'This is test.'}
    #return HttpResponse(json.dumps(status_dict))
    return render_to_response('help.html',locals())    
    
def report(request,task_id="not_passed"):
    
    summary={}
    if(list(User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    task=User_Job.objects.filter(user_id=task_id)[0]
    
    #overview page
    overview={}
    overview['submit_time']=task.submission_time
    overview['start_time']=task.start_time
    overview['end_time']=task.end_time
    
    
    success=1
    total_file=1
    REF=1
    TREE=1
    if(task.ragout_status=="SKIPPED"):
        REF=0
    if(task.tree_status=="SKIPPED"):
        TREE=0
    print(task.tree_status)
    if(task.total_status=="FAILED"):
        success=0
        failed_step=error_map[task.error_log]
        if(task.error_log=="SYSTEM"):
            try:
                Path(DATA+'/'+task_id+'/myjob.tar.gz').resolve()
            except:
                total_file=0
        return render(request,'show_report.html',
                    {
                     'task_id':task_id,
                     'REF':REF,
                     'success':success,
                     'failed_step':failed_step,
                     'overview':overview,
                     'total_file':total_file,
                    })
    elif(task.total_status=="WAITING" or task.total_status=="RUNNING"):
        return render(request,'status.html',{})
    

    basic_dic={'REF':REF,
               'TREE':TREE,
               'success':success,
               'task_id':task_id,
               'overview':overview,
               'total_file':total_file,
              }
    with open(DATA+'/'+task_id+'/output_dict', 'rb') as fp:
        out_dic=pickle.load(fp)
    
    out_dic.update(basic_dic)
    
    return render(request,'show_report.html',out_dic)    

    
def reference_guided(request):
    #a='<option value="wow" data-section="JavaScript/Synomy">Java</option>'
    #with open (str(Path('../').resolve().joinpath('src','select')), 'rb') as fp:
    #    real = pickle.load(fp)
    real={}
    return render(request,'reference_guided.html',{'real':real})

def status(request,task_id="not_passed"):
        
    status_dict={}
    if(list(User_Job.objects.filter(user_id=task_id))==[]):
        print("I am in status")
        return render(request,'no_id_match.html',{'task_id':task_id})
    
    return render(request,'status.html',status_dict)

def retrieve(request,task_id="not_passed"):
        
    if(list(User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    else:
        myjob=User_Job.objects.get(user_id=task_id)
        status_dict={}
        status_dict['total_status']=myjob.total_status
        status_dict['data_preparation_status']=myjob.data_preparation_status
        status_dict['quality_check']=myjob.quality_check
        status_dict['a5_status']=myjob.a5_status
        status_dict['ragout_status']=myjob.ragout_status
        status_dict['gene_prediction_status']=myjob.gene_prediction_status
        status_dict['go_status']=myjob.go_status
        status_dict['tree_status']=myjob.tree_status
        status_dict['parsing_status']=myjob.parsing_status
        status_dict['task_id']=task_id
        
        #print(json.dumps(status_dict))
    
    return HttpResponse(json.dumps(status_dict))

def get_tree(request):
    treedict={}
    with open (str(Path('../').resolve().joinpath('src','tree_select_options.pickle')), 'rb') as fp:
        treedict['tree_content'] = pickle.load(fp)
    
    #print("I am in get_tree!!!!")
    return HttpResponse(json.dumps(treedict))
    
def ref_report(request,task_id="not_passed"):
    return render_to_response('home.html',locals())
    
def non_ref_report(request,task_id="not_passed"):
    return render_to_response('home.html',locals())
    
def ref_result(request):
    #return render_to_response('home.html',locals())
    #uid="8e6c9a42-6a6a-11e8-8d82-d89d67f39fa9"
    uid=str(uuid.uuid1())
    #uid="ab88ccb2-9ed8-11e7-91c5-d89d67f39fa9"   
    data_path=str(Path(settings.OUTPUT_BASE_DIR).joinpath(uid))
    sfile_path=str(Path('../').resolve().joinpath('src','snakefiles'))   
    msg=""
    
    try:
        test=request.POST['email']
        print(test)
    except:
        msg="Task submitted page is not allowed to be displayed again. Please check your email for status/result link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    # check illegal characters in upload_id
    upload_id = re.sub(r"[\W]", "", request.POST.get('upload_id'))
    if upload_id == '':
        msg="The upload_id is not found."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    print(upload_id)
    
    if (User_Job.objects.filter(upload_id=upload_id).count()>0):
        msg="You have already uploaded the file. Please check your email for status link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    #check tree species number
    if(len(list(request.POST.getlist('tree_select')))>10):
        msg="Only ten species are allowed on phylogenetic tree drawing section."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    #get all the parameter from front end here with dictionary type
    
    parameters={}
    parameters['upload_id']=upload_id
    
    parameters['dict_urls']={}  # Dictionary for URL download
    if request.POST.get('upload_method') == "from_url":
        parameters['dict_urls'] = {'R1.fastq': request.POST.get('confirmed_url_R1'), 'R2.fastq': request.POST.get('confirmed_url_R2'), 'reference.fa': request.POST.get('confirmed_url_Rf')}
    
    parameters['de_novo']={}
    if(request.POST['denovo_setting']=='default'):
        parameters['de_novo']['m_value']="300" #this value should equl min contig thresholds
        parameters['de_novo']['contig_thresholds']="300,1000,5000,10000,25000,50000"
        parameters['de_novo']['a5_busco_species']='E_coli_K12'
        parameters['de_novo']['a5_e_value']='1e-03'
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
        try:
            e_value=str(request.POST['a5_e_value'])
        except:
            msg="BUSCO e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['de_novo']['a5_e_value']=e_value
        else:
            msg="BUSCO e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            
        parameters['de_novo']['m_value']=new_contig.split(",")[0]
        parameters['de_novo']['contig_thresholds']=new_contig
        parameters['de_novo']['a5_busco_species']=request.POST['a5_busco_species']
        
    
    parameters['ref']={}
    if(request.POST['ref_setting']=='default'):
        parameters['ref']['refine']=' --refine'
        parameters['ref']['ref_m_value']="1000"   #this value should equl min contig thresholds
        parameters['ref']['ref_contig_thresholds']="1000,5000,10000,25000,50000"
        parameters['ref']['ref_busco_species']='E_coli_K12'
        parameters['ref']['ref_e_value']='1e-03'
        parameters['ref']['no_unal']=' --no-unal'   # Yes contains "--no-unal" in command
    else:
        contig=[1000,5000,10000,25000,50000]
        
        try:
            user_contig=int(request.POST['ref_contig_thresholds'])
        except:
            msg="QUAST minimum contig-thresholds needs to be an integer >=0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(user_contig<0):
            msg="QUAST minimum contig-thresholds needs to be an integer >=0"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            
        if(user_contig>50000):
            new_contig=str(user_contig)
        elif(user_contig<1000):
            new_contig=str(user_contig)+",5000,10000,25000,50000"
        else:
            new_contig=str(user_contig)
            for i in range(0,len(contig)):
                if(user_contig<contig[i]):
                    new_contig=new_contig+","+str(contig[i])
        parameters['ref']['ref_m_value']=new_contig.split(",")[0]
        parameters['ref']['ref_contig_thresholds']=new_contig
        parameters['ref']['ref_busco_species']=request.POST['ref_busco_species']
        
        try:
            e_value=str(request.POST['ref_e_value'])
        except:
            msg="BUSCO e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['ref']['ref_e_value']=e_value
        else:
            msg="BUSCO e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        if(request.POST['no_unal']=="Yes"):
            parameters['ref']['no_unal']=' --no-unal'
        else:
            parameters['ref']['no_unal']=''
        
        if(request.POST['refine']=="Yes"):
            parameters['ref']['refine']=' --refine'
        else:
            parameters['ref']['refine']=''
    
    parameters['gene_prediction']={}
    if(request.POST['gene_pred']=="GeneMark"):
        pred_flag=0  #run genemark
    else:
        pred_flag=1  #run augustus
        if(request.POST['aug_setting']=="default"):
            parameters['gene_prediction']['aug_species']='E_coli_K12'
            parameters['gene_prediction']['aug_strand']='both'
        else:
            parameters['gene_prediction']['aug_species']=str(request.POST['aug_species'])
            parameters['gene_prediction']['aug_strand']=request.POST['aug_strand']
        #deal homology protein later
    
    parameters['gene_assm']={}
    if(request.POST['pred_assm_setting']=='default'):
        parameters['gene_assm']['pred_assm_busco_species']='E_coli_K12'
        parameters['gene_assm']['pred_assm_e_value']='1e-03'
        parameters['gene_assm']['blast_e_value']='1E-5'
        
    else:
        try:
            e_value=str(request.POST['pred_assm_e_value'])
        except:
            msg="BUSCO e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['pred_assm_e_value']=e_value
        else:
            msg="BUSCO e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
        try:
            e_value=str(request.POST['blast_e_value'])
        except:
            msg="BLAST e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['blast_e_value']=e_value
        else:
            msg="BLAST e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
        parameters['gene_assm']['pred_assm_busco_species']=str(request.POST['pred_assm_busco_species'])
        #parameters['gene_assm']['pred_assm_e_value']=request.POST['pred_assm_e_value']
        #parameters['gene_assm']['blast_e_value']=str(request.POST['blast_e_value'])
        
    parameters['go']={}
    if(request.POST['go_setting']=='default'):
        parameters['go']['file_type']='tsv'        
    else:
        print(request.POST.getlist('file_type'))
        if(request.POST.getlist('file_type')==[]):
            parameters['go']['file_type']='tsv'
        else:
            temp=list(request.POST.getlist('file_type'))
            valid_string="tsv"
            for i in temp:
                valid_string=valid_string+","+i
            parameters['go']['file_type']=valid_string
    
    parameters['tree']={}
    if(request.POST['tree']=='no_tree'):
        parameters['tree']['yesno']='no'      
    else:
        if(len(list(request.POST.getlist('tree_select')))==0):
            parameters['tree']['yesno']='no'
        else:
            try:
                if( not re.match('^[A-Za-z0-9_]{1,10}$',request.POST['tree_sample_name'])):
                    msg="Tree sample name pattern invalid."
                    return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            except:
                msg="Please input your tree sample name."
                return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            
            
            parameters['tree']['yesno']='yes'
            parameters['tree']['species']=list(request.POST.getlist('tree_select'))
            parameters['tree']['name']=str(request.POST['tree_sample_name'])
        
    #print(parameters['tree']['species'])
    #print(parameters)
    
    #save uid into model  
    ip_address=get_real_ip(request)  #make sure this line work in real environment
    if ip_address is not None:
        print("We have a publicly-routable IP address for client")
        submitted_job_number=User_Job.objects.filter(ip=ip_address,total_status__in=["WAITING","RUNNING"]).count()
        
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
    print(mail)
    try:
        User_Job.objects.create(user_id=uid,
                                upload_id=upload_id,
                                ip=ip_address,mail=mail,
                                submission_time=times,
                                start_time=times,
                                end_time=times,
                                ragout_status="WAITING"
                                )
        ip_log.objects.create(ip=ip_address,country=country,submission_time=times,functions="REF")
        
        if(parameters['tree']['yesno']=='yes'):
            User_Job.objects.filter(user_id=uid).update(tree_status="WAITING")
    except:
        #return email not allowed
        msg="Your email address is not a correct one."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})   
    
    
    task_id=async('pipeline.tasks.run_pipeline',sfile_path=sfile_path,data_path=data_path,aug_flag=pred_flag,param=parameters)
    
    job_numbers=User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    user_status_link="/"+uid+"/status"
    
    #send mail with link
    
    send_mail('Task Submitted', 'Your Link:'+web_url+"/"+uid+"/status", None,
    [mail], fail_silently=True)
    
    return render(request,'submit_response.html',
                    {'uid':uid,
                     'job_numbers':job_numbers,
                     'user_status_link':user_status_link})


def non_ref(request):
    real={}
    return render(request,'non_ref.html',{'real':real})
    
def non_ref_result(request):
    
    #uid="341b2f62-68fe-11e8-95dc-d89d67f39fa9"
    uid=str(uuid.uuid1())
    #uid="f0e2636a-eb11-11e7-9213-d89d67f39fa9"
    data_path=str(Path(settings.OUTPUT_BASE_DIR).joinpath(uid))
    sfile_path=str(Path('../').resolve().joinpath('src','snakefiles'))
    msg=""
    #print("I am in non_ref_result again!!!")
    try:
        test=request.POST['email']
        #print(test)
    except:
        msg="Task submitted page is not allowed to be displayed again. Please check your email for status/result link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    # check illegal characters in upload_id
    upload_id = re.sub(r"[\W]", "", request.POST.get('upload_id'))
    if upload_id == '':
        msg="The upload_id is not found."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    if (User_Job.objects.filter(upload_id=upload_id).count()>0):
        msg="You have already submitted the job. Please check your email for status link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    #check tree species number
    if(len(list(request.POST.getlist('tree_select')))>10):
        msg="Only ten species are allowed on phylogenetic tree drawing section."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    


    #get front end parameter
    parameters={}
    parameters['upload_id']=upload_id
    
    parameters['dict_urls']={}  # Dictionary for URL download
    if request.POST.get('upload_method') == "from_url":
        parameters['dict_urls'] = {'R1.fastq': request.POST.get('confirmed_url_R1'), 'R2.fastq': request.POST.get('confirmed_url_R2')}

    parameters['de_novo']={}
    if(request.POST['denovo_setting']=='default'):
        parameters['de_novo']['m_value']="300" #this value should equl min contig thresholds
        parameters['de_novo']['contig_thresholds']="300,1000,5000,10000,25000,50000"
        parameters['de_novo']['a5_busco_species']='E_coli_K12'
        parameters['de_novo']['a5_e_value']='1e-03'
        parameters['de_novo']['no_unal']=' --no-unal'   # Yes contains "--no-unal" in command
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
        
        try:
            e_value=str(request.POST['a5_e_value'])
        except:
            msg="BUSCO e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['de_novo']['a5_e_value']=e_value
        else:
            msg="BUSCO e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        parameters['de_novo']['m_value']=new_contig.split(",")[0]
        parameters['de_novo']['contig_thresholds']=new_contig
        parameters['de_novo']['a5_busco_species']=request.POST['a5_busco_species']

        if(request.POST['no_unal']=="Yes"):
            parameters['de_novo']['no_unal']=' --no-unal'
        else:
            parameters['de_novo']['no_unal']=''
        
    parameters['gene_prediction']={}
    if(request.POST['gene_pred']=="GeneMark"):
        pred_flag=0  #run genemark
    else:
        pred_flag=1  #run augustus
        if(request.POST['aug_setting']=="default"):
            parameters['gene_prediction']['aug_species']='E_coli_K12'
            parameters['gene_prediction']['aug_strand']='both'
        else:
            parameters['gene_prediction']['aug_species']=str(request.POST['aug_species'])
            parameters['gene_prediction']['aug_strand']=request.POST['aug_strand']
        #deal homology protein later
    
    parameters['gene_assm']={}
    if(request.POST['pred_assm_setting']=='default'):
        parameters['gene_assm']['pred_assm_busco_species']='E_coli_K12'
        parameters['gene_assm']['pred_assm_e_value']='1e-03'
        parameters['gene_assm']['blast_e_value']='1E-5'
        
    else:
        try:
            e_value=str(request.POST['pred_assm_e_value'])
        except:
            msg="BUSCO e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['pred_assm_e_value']=e_value
        else:
            msg="BUSCO e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
        try:
            e_value=str(request.POST['blast_e_value'])
        except:
            msg="BLAST e value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['blast_e_value']=e_value
        else:
            msg="BLAST e value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        parameters['gene_assm']['pred_assm_busco_species']=str(request.POST['pred_assm_busco_species'])
        #parameters['gene_assm']['pred_assm_e_value']=request.POST['pred_assm_e_value']
        #parameters['gene_assm']['blast_e_value']=str(request.POST['blast_e_value'])
        
    parameters['go']={}
    if(request.POST['go_setting']=='default'):
        parameters['go']['file_type']='tsv'        
    else:
        print("file type:",request.POST.getlist('file_type'))
        if(request.POST.getlist('file_type')==[]):
            parameters['go']['file_type']='tsv'
        else:
            temp=list(request.POST.getlist('file_type'))
            valid_string="tsv"
            for i in temp:
                valid_string=valid_string+","+i
            parameters['go']['file_type']=valid_string
    
    parameters['tree']={}
    if(request.POST['tree']=='no_tree'):
        parameters['tree']['yesno']='no'      
    else:
        if(len(list(request.POST.getlist('tree_select')))==0):
            parameters['tree']['yesno']='no'
        else:
            try:
                if( not re.match('^[A-Za-z0-9_]{1,10}$',request.POST['tree_sample_name'])):
                    msg="Tree sample name pattern invalid."
                    return render(request,'not_allow.html',{'uid':uid,'msg':msg})
            except:
                msg="Please input your tree sample name."
                return render(request,'not_allow.html',{'uid':uid,'msg':msg})
                
            #User_Job.objects.filter(user_id=uid).update(tree_status="WAITING")
            parameters['tree']['yesno']='yes'
            parameters['tree']['species']=list(request.POST.getlist('tree_select'))
            parameters['tree']['name']=str(request.POST['tree_sample_name'])
    
    #save uid into model    
    ip_address=get_real_ip(request)  #make sure this line work in real environment
    if ip_address is not None:
        print("We have a publicly-routable IP address for client")
        submitted_job_number=User_Job.objects.filter(ip=ip_address,total_status__in=["WAITING","RUNNING"]).count()
        
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
    try:
        User_Job.objects.create(user_id=uid,
                                upload_id=upload_id,
                                ip=ip_address,mail=mail,
                                submission_time=times,
                                start_time=times,
                                end_time=times,
                                ragout_status="SKIPPED"
                                )
                                
        ip_log.objects.create(ip=ip_address,country=country,submission_time=times,functions="NON-REF")   

        if(parameters['tree']['yesno']=='yes'):
            User_Job.objects.filter(user_id=uid).update(tree_status="WAITING")
    except:
        #return email not allowed
        msg="Your email address is not a correct one."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})   #check this by front-end in the future
    
    #run task
    task_id=async('pipeline.tasks.run_non_ref_pipeline',sfile_path=sfile_path,data_path=data_path,aug_flag=pred_flag,param=parameters)
    
    job_numbers=User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    user_status_link="/"+uid+"/status"
    
    #send mail with link

    send_mail('Task Submitted', 'Your Link:'+web_url+"/"+uid+"/status", None,
    [mail], fail_silently=True)
    
    return render(request,'submit_response.html',
                    {'uid':uid,
                     'job_numbers':job_numbers,
                     'user_status_link':user_status_link})
