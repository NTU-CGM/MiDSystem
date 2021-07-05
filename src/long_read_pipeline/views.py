from django.shortcuts import render, render_to_response
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET
from django.template import RequestContext
from django.utils.html import mark_safe
from django.core.mail import send_mail
from django.conf import settings
from .models import long_User_Job, long_ip_log
import uuid
import os
import shutil
import json
import pickle
from pathlib import Path
from ipware.ip import get_real_ip
from django_q.tasks import async, result, async_chain, Chain
import datetime
from geolite2 import geolite2
import re
from tempfile import gettempdir
import pandas as pd

reader = geolite2.reader()
web_url=settings.WEB_URL
error_map={
"DATA":"Data Preparation",
"QC":"Quality Control",
"ASSEMBLY":"De Novo Assembly",
"REMAP":"Short-read Re-mapping",
"AUG":"Gene Prediction",
"GM":"Gene Prediction",
"GO":"Functional Annotation",
"TREE":"Phylogenetic Tree",
"PARSER":"Parsing Result",
"SYSTEM":"System Error"
}
UPLOAD_BASE_PATH = gettempdir()
DATA = settings.OUTPUT_BASE_DIR


# Create your views here.
def long_read_home(request):
    return render(request,'long_read_home.html',{})
    

def long_read_retrieve(request, task_id="not_passed"):
    if(list(long_User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    else:
        myjob=long_User_Job.objects.get(user_id=task_id)
        status_dict={}
        status_dict['total_status']=myjob.total_status
        status_dict['data_preparation_status']=myjob.data_preparation_status
        status_dict['quality_check']=myjob.quality_check
        status_dict['assembly_status']=myjob.assembly_status
        status_dict['remap_status']=myjob.remap_status
        status_dict['gene_prediction_status']=myjob.gene_prediction_status
        status_dict['go_status']=myjob.go_status
        status_dict['tree_status']=myjob.tree_status
        status_dict['parsing_status']=myjob.parsing_status
        status_dict['task_id']=task_id
        
        #print(json.dumps(status_dict))
    
    return HttpResponse(json.dumps(status_dict))


def long_read_status(request, task_id="not_passed"):
    if(list(long_User_Job.objects.filter(user_id=task_id))==[]):
        print("User ID not found in status")
        return render(request,'no_id_match.html',{'task_id':task_id})
    
    return render(request,'long_read_status.html',{})


def long_read_result(request):
    uid=str(uuid.uuid1())
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
    
    if (long_User_Job.objects.filter(upload_id=upload_id).count()>0):
        msg="You have already uploaded the file. Please check your email for status link."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    #check tree species number
    if(len(list(request.POST.getlist('tree_select')))>10):
        msg="Only ten species are allowed on phylogenetic tree drawing section."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    #get all the parameter from front end here with dictionary type
    
    parameters={}
    parameters['upload_id']=upload_id
    
    parameters['qc']={}
    ## longqc_platform
    if request.POST['rad_long_read_platform'] in ['pb-rs2','pb-sequel','pb-hifi','ont-ligation','ont-rapid','ont-1dsq']:
        parameters['qc']['longqc_platform']=request.POST['rad_long_read_platform']
    else:
        msg='Invalid value. The long-read platform/library must be "pb-rs2", "pb-sequel", "pb-hifi", "ont-ligation", "ont-rapid", or "ont-1dsq".'
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    ## use hybrid
    str_use_hybrid = str(request.POST['use_hybrid'])
    if str_use_hybrid in ['0', '1']:
        parameters['qc']['HYBRID']=str_use_hybrid
    else:
        msg='Invalid value. The value of use hybrid must be "0" or "1".'
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    parameters['dict_urls']={}  # Dictionary for URL download
    if request.POST.get('upload_method') == "from_url":
        if str_use_hybrid == '1':
            parameters['dict_urls'] = {'R1.fastq': request.POST.get('confirmed_url_R1'), 'R2.fastq': request.POST.get('confirmed_url_R2'), 'long.fastq': request.POST.get('confirmed_url_long')}
        else:
            parameters['dict_urls'] = {'long.fastq': request.POST.get('confirmed_url_long')}
    
    parameters['de_novo']={}
    parameters['de_novo']['HYBRID']=parameters['qc']['HYBRID']
    parameters['remap']={}
    parameters['remap']['HYBRID']=parameters['qc']['HYBRID']
    
    if(request.POST['denovo_setting']=='default'):
        parameters['de_novo']['unicycler_mode']='normal'
        parameters['de_novo']['m_value']='300' #this value should equl min contig thresholds
        parameters['de_novo']['contig_thresholds']='300,1000,5000,10000,25000,50000'
        parameters['de_novo']['busco_species']='E_coli_K12'
        parameters['de_novo']['e_value']='1e-03'
        parameters['remap']['no_unal']=' --no-unal'   # Yes contains "--no-unal" in command        
    else:
        ## unicycler_mode
        if request.POST['unicycler_mode'] in ['conservative', 'normal', 'bold']:
            parameters['de_novo']['unicycler_mode']=request.POST['unicycler_mode']
        else:
            msg='Invalid value. The Unicycler mode must be "conservative", "normal", or "bold".'
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        ## m_value & contig_thresholds
        contig=[300,1000,5000,10000,25000,50000]
        try:
            user_contig=int(request.POST['contig_thresholds'])
        except:
            msg="QUAST minimum contig-thresholds needs to be an integer"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(user_contig<0):
            msg="QUAST minimum contig-thresholds needs to be greater than or equal to 0"
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
        
        ## e_value
        try:
            e_value=str(request.POST['e_value'])
        except:
            msg="BUSCO e-value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['de_novo']['e_value']=e_value
        else:
            msg="BUSCO e-value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        
        ## busco_species
        parameters['de_novo']['busco_species']=request.POST['busco_species']
        
        ## Bowtie2 no_unal
        if(request.POST['no_unal']=="Yes"):
            parameters['remap']['no_unal']=' --no-unal'
        else:
            parameters['remap']['no_unal']=''
    
    
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
            msg="BUSCO e-value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['pred_assm_e_value']=e_value
        else:
            msg="BUSCO e-value pattern not matched."
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
        try:
            e_value=str(request.POST['blast_e_value'])
        except:
            msg="BLAST e-value cannot be empty"
            return render(request,'not_allow.html',{'uid':uid,'msg':msg})
        if(re.match('[+\-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?',e_value)):
            parameters['gene_assm']['blast_e_value']=e_value
        else:
            msg="BLAST e-value pattern not matched."
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
    print(parameters)
    
    #save uid into model  
    ip_address=get_real_ip(request)  #make sure this line work in real environment
    if ip_address is not None:
        print("We have a publicly-routable IP address for client")
        submitted_job_number=long_User_Job.objects.filter(ip=ip_address,total_status__in=["WAITING","RUNNING"]).count()
        
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
    
    if str_use_hybrid == '1':
        remap_status = 'WAITING'
        assembly_fn = 'HYBRID'
    else:
        remap_status = 'SKIPPED'
        assembly_fn = 'LONG'
    
    if(parameters['tree']['yesno']=='yes'):
        tree_status = 'WAITING'
    else:
        tree_status = 'SKIPPED'
    
    try:
        long_User_Job.objects.create(user_id=uid,
                                upload_id=upload_id,
                                ip=ip_address,
                                mail=mail,
                                submission_time=times,
                                start_time=times,
                                end_time=times,
                                remap_status=remap_status,
                                tree_status=tree_status)
        long_ip_log.objects.create(ip=ip_address,country=country,submission_time=times,functions=assembly_fn)
        
        # if(parameters['tree']['yesno']=='yes'):
            # long_User_Job.objects.filter(user_id=uid).update(tree_status="WAITING")
    except:
        msg="Error: writing to the database. Please contact the administrator."
        return render(request,'not_allow.html',{'uid':uid,'msg':msg})
    
    
    task_id=async('long_read_pipeline.tasks.run_long_read_pipeline', sfile_path=sfile_path, data_path=data_path, aug_flag=pred_flag, param=parameters)
    
    job_numbers=long_User_Job.objects.filter(total_status__in=['WAITING','RUNNING']).count()
    user_status_link="/long_read/"+uid+"/status"
    
    #send mail with link
    
    send_mail('Task Submitted', 'Your Link:'+web_url+"/long_read/"+uid+"/status", None,
    [mail], fail_silently=True)
    
    return render(request,'submit_response.html',
                    {'uid':uid,
                     'job_numbers':job_numbers,
                     'user_status_link':user_status_link})
    

def long_read_report(request, task_id="not_passed"):
    summary={}
    if(list(long_User_Job.objects.filter(user_id=task_id))==[]):
        return render(request,'no_id_match.html',{'task_id':task_id})
    task=long_User_Job.objects.filter(user_id=task_id)[0]
    
    #overview page
    overview={}
    overview['submit_time']=task.submission_time
    overview['start_time']=task.start_time
    overview['end_time']=task.end_time
    
    success=1
    total_file=1
    HYBRID=1
    TREE=1
    if(task.remap_status=="SKIPPED"):
        HYBRID=0
    if(task.tree_status=="SKIPPED"):
        TREE=0
    
    # read the MiDSystem version number
    with open(DATA+'/'+task_id+'/MiDSystem.version') as fp:
        version = fp.read().strip()
    
    if(task.total_status=="FAILED"):
        success=0
        failed_step=error_map[task.error_log]
        if(task.error_log=="SYSTEM"):
            try:
                Path(DATA+'/'+task_id+'/myjob.tar.gz').resolve()
            except:
                total_file=0
        return render(request,'long_read_report.html',
                    {
                     'task_id':task_id,
                     'HYBRID':HYBRID,
                     'success':success,
                     'failed_step':failed_step,
                     'overview':overview,
                     'total_file':total_file,
                     'version':version,
                    })
    elif(task.total_status=="WAITING" or task.total_status=="RUNNING"):
        return render(request,'long_read_status.html',{})
    
    # get system info tables
    tools_df = pd.read_csv(DATA+'/'+task_id+'/tools_list.tsv', sep="\t", engine='python')
    tools_list = tools_df[tools_df.columns[:4]].values.tolist()
    
    databases_df = pd.read_csv(DATA+'/'+task_id+'/databases_list.tsv', sep="\t", engine='python')
    databases_list = databases_df[databases_df.columns[:3]].values.tolist()

    basic_dic={'HYBRID':HYBRID,
               'TREE':TREE,
               'success':success,
               'task_id':task_id,
               'overview':overview,
               'total_file':total_file,
               'version':version,
               'tools_list':tools_list,
               'databases_list':databases_list,
              }
    with open(DATA+'/'+task_id+'/output_dict', 'rb') as fp:
        out_dic=pickle.load(fp)
    
    out_dic.update(basic_dic)
    
    return render(request,'long_read_report.html',out_dic)    


