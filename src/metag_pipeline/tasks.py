import subprocess as sp
from pathlib import Path
from os import path, environ, makedirs
import time
import datetime
import pandas as pd
from collections import Counter
import ast
import pickle
import json
from django.core.mail import send_mail
from .models import meta_User_Job,meta_ip_log
from .views import UPLOAD_BASE_PATH
from django.utils.html import mark_safe
from django.conf import settings
import shutil
from pipeline.tasks import copy_snake,run_QC
import re
import gzip
from pipeline.googledrive_downloader import GoogleDriveDownloader
import requests, requests_ftp

web_url=settings.WEB_URL #remember to change this
SNAKEMAKE_BIN = path.join(settings.CONDA_APP_BIN, 'snakemake')
env = environ.copy()
env['PATH'] = settings.CONDA_APP_BIN + ':' + env['PATH']
env['KRAKEN_DB'] = settings.KRAKEN_DB

def failed_tar_result(data_path):
    user_root=data_path.split('/')[1]
    uid=data_path.split('/')[2]
    
    #let check equal True to let pipeline catch the SYSTEM error
    '''
    p=sp.run("cd /"+user_root+";tar zcvf "+data_path+
    "/myjob.tar.gz --exclude=myjob.tar.gz --exclude=raw --exclude=kraken --exclude=.snakemake "+
    "--exclude=domain_mapping --exclude=taxo_abundance --exclude=meta_function --exclude=meta_genepred --exclude=meta_a5 "+
    "--exclude=QC --exclude=taxonomic.tar.gz --exclude=user_pfam_result.tar.gz --exclude=user_eggnong_result.tar.gz --exclude=output_dict "+
    uid,shell=True)
    '''
    p=sp.run("cd /"+user_root+";tar zcvf "+
    uid+".tar.gz --exclude=raw --exclude=kraken/*.fastq --exclude=.snakemake "+
    "--exclude=snake_based_paths --exclude=domain_mapping --exclude=taxo_abundance --exclude=meta_function --exclude=meta_genepred --exclude=meta_a5 --exclude=meta_a5/user.s? "+
    "--exclude=QC --exclude=taxonomic.tar.gz --exclude=user_pfam_result.tar.gz --exclude=user_eggnong_result.tar.gz --exclude=output_dict "+
    uid+";mv "+uid+".tar.gz "+data_path+"/myjob.tar.gz",shell=True)
    
    #make softlink to static and assets
        
    tmp_path=str(Path('../').resolve().joinpath('src','assets'))
    p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
    tmp_path=str(Path('../').resolve().joinpath('src','static'))
    p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
    return 0

def failed_email(data_path):
    uid=data_path.split('/')[2]
    #send mail for failed task TODO:change fail_silently=True 
    user=meta_User_Job.objects.filter(user_id=uid)[0]
    mail=user.mail
    send_mail('Task Failed!', 'Your link for the report:'+web_url+"/meta/"+uid+"/report", None,
    [mail], fail_silently=True)
    return 0

def run_data_preparation(source_path, destination_path, dict_urls,kraken_usage):
    try:
        if not path.exists(destination_path):
            makedirs(destination_path)
        if(kraken_usage=='no'):
            dest_raw_path = str(Path(destination_path).resolve().joinpath('raw'))
        else:
            dest_raw_path = str(Path(destination_path).resolve().joinpath('kraken'))
        
        if not path.exists(dest_raw_path):
            makedirs(dest_raw_path)
        if not path.exists(source_path):
            makedirs(source_path)
        
        if len(dict_urls): # data come from URLs
            for new_file_name, url in dict_urls.items():
                m1 = re.search('google\.com.+id=(.+)\&*', url)
                if m1:
                    # Use GoogleDriveDownloader module
                    id = m1.group(1)
                    response = GoogleDriveDownloader.get_response(id)
                else:
                    # Direct download
                    if not re.match(r'^(http|https|ftp)://', url):
                        url = 'http://'+url
                    requests_ftp.monkeypatch_session()
                    session = requests.Session()
                    response = session.get(url, stream=True)
                
                # Check file existing
                if response.ok == False:
                    return -1
                else:
                    # Get the file name and extension
                    if m1:
                        m2 = re.search('filename="(.+)"', response.headers['Content-Disposition'])
                        file_name = m2.group(1)
                    else:
                        file_name = response.url.split('/')[-1]
                    extension = path.splitext(file_name)[1]
                    
                    # Check file format
                    if new_file_name == 'reference.fa':
                        if not re.search('\.(fasta|fa|fna)+(\.gz)*$', file_name):
                            return -1
                    else:
                        if not re.search('\.f(ast)*q(\.gz)*$', file_name):
                            return -1
                    
                    # Save a downloaded file to disk
                    if extension == '.gz':
                        with open(str(Path(source_path).resolve().joinpath(new_file_name)), "wb") as destination:
                            with gzip.GzipFile(fileobj=response.raw) as source:
                                shutil.copyfileobj(source, destination)
                    else:
                        with open(str(Path(source_path).resolve().joinpath(new_file_name)), "wb") as destination:
                            for chunk in response.iter_content(32768):
                                if chunk:  # filter out keep-alive new chunks
                                    destination.write(chunk)                    
        
        #save files to UID/raw
        #shutil.copy2(str(Path(source_path).resolve()), dest_raw_path)
        shutil.copy2(str(Path(source_path).resolve().joinpath('R1.fastq')), dest_raw_path)
        shutil.copy2(str(Path(source_path).resolve().joinpath('R2.fastq')), dest_raw_path)
        shutil.rmtree(source_path)
        return 0
        
    except Exception as e:
        print(e)
        return -1
    
def run_kraken(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'snake_kraken')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/kraken/classified.fa", data_path+"/raw/R1.fastq",data_path+"/raw/R2.fastq"]  
    
    try:
        for i in range(len(check_file)):
            Path(check_file[i]).resolve()    
        print('Kraken Done')
    except FileNotFoundError:
        print('Kraken Error')
        return -1
    
    return 0    
    
def run_meta_A5(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'meta_a5')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/a5_miseq/user.final.scaffolds.fasta"]
    
    try:
        Path(check_file[0]).resolve()
        print('A5 Done')
    except FileNotFoundError:
        print('A5 Error')
        return -1
    
    return 0

def run_taxo(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'taxo_abundance')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/metaphlan/merged_abundance_table.txt"] 
    
    try:
         
        Path(check_file[0]).resolve()
        print('Taxonomic Done')
    except FileNotFoundError:
        print('Taxonomic Error')
        return -1
    
    return 0

def run_pred(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'meta_genepred')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/metagenemark/user.protein.fasta"] 
    
    try:
         
        Path(check_file[0]).resolve()
        print('Gene Prediction Done')
    except FileNotFoundError:
        print('Gene Prediction Error')
        return -1
    
    return 0    
    
def run_func(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'meta_function')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/eggnog/result_diamond.emapper.annotations"] 
    
    try:
        Path(check_file[0]).resolve()
        print('Funcional Annotation Done')
    except FileNotFoundError:
        print('Functional Annotation Error')
        return -1
    
    return 0

def run_domain(data_path):    
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'domain_mapping')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/cdhit/predicted_gene.modified.txt"] 
    
    try:
        Path(check_file[0]).resolve() 
        print('Domain Mapping Done')
    except FileNotFoundError:
        print('Domain Mapping Error')
        return -1
    
    return 0

def run_meta_parser(data_path):
    try:
        #trimmomatic parser
        file = open(data_path+"/trimmomatic/trimmomatic.log","r")
        temp=file.read()
        ll=temp.split('\n')
        parsing=ll[4]
        output_string=["Input Read Pairs","Both Surviving","Forward Only Surviving","Reverse Only Surviving","Dropped"]
        numbers=[int(s) for s in parsing.split(" ") if s.isdigit()]
        result=[]
        result.append(["status","reads number"])
        for i in range(1,len(numbers)):
            result.append([output_string[i],numbers[i]])
        
        
        #a5 parser
        a5_result_pair=[]
        '''
        df=pd.read_csv(data_path+'/a5_miseq/user.assembly_stats.csv',sep='\t')
        col=list(df.columns)[1:]
        vals=list(df.loc[0].values)[1:]
        a5_result_pair=[]
        for i in range(0,len(col)):
            a5_result_pair.append((col[i],vals[i]))
        '''
        #taxonomic parser
        task_id=data_path.split('/')[2]
        sp.run("cd "+data_path+"/metaphlan;tar zcvf "+data_path+"/taxonomic.tar.gz *",shell=True)
        df=pd.read_csv(data_path+'/metaphlan/merged_abundance_table_species.txt',sep='\t')
        df=df.sort_values(by=[task_id+'_profiled'],ascending=False)
        taxo_output=list(zip(list(df['ID']),list(df[task_id+'_profiled'])))
        taxo_plot=[mark_safe(json.dumps(list(df['ID']))),list(df[task_id+'_profiled'])]
        
        
        
        emapper_table=pd.read_csv(data_path+"/eggnog/result_diamond.emapper.annotations",skiprows=3,skipfooter=3,sep='\t',engine='python')
        
        #gene prediction and cdhit parser
       
        express=pd.read_csv(data_path+'/express/results.xprs',sep='\t')
        express['target_id']=express.target_id.str.split('|').str.get(0)

        ids=list(express['target_id'])
        counts=list(express['tpm'])
        reads={}
        for i in range(len(ids)):
            reads[ids[i]]=counts[i]        
            
        file=pd.read_table(data_path+'/cdhit/genecatalog.clstr',names=['ID','NAME'])
        ids=list(file['ID'])
        names=(file['NAME'])
        cluster_id=list(file[file.ID.str.match('>Cluster')].index)
        cluster_id.append(len(names))
        name_result={}
        abundance={}
        represent={}
        for i in range(len(cluster_id)-1):
            name_result[i]=[]
            abundance[i]=0
            for j in range(cluster_id[i]+1,cluster_id[i+1]):
                n=names[j].split('>')[1].split('|')[0]
                if("*" in names[j]):
                    represent[i]=n 
                name_result[i].append(n)
                abundance[i]+=reads[n]
        
        abund_rank=sorted(abundance, key=abundance.get,reverse=True)
        abundance_table=[] 
        rep_gene_total_abundance={}
        for i in abund_rank:
            rep_gene_total_abundance[represent[i]]=abundance[i]
            abundance_table.append((i,represent[i],len(name_result[i]),round(abundance[i],2))) 

        pd.DataFrame(abundance_table).to_csv(data_path+'/cdhit/gene_catalog_abundance.csv',header=['catalog','represent gene','gene member number','TPM abundance'],index=False)        
        
        annotated_number=len(set(emapper_table['#query_name']))
        
        gene_pred_table=[('Gene Number',len(reads)),
                        ('Catalog Number',len(cluster_id)-1),
                        ('Annotated Gene Catalog Number',annotated_number),
                        ('Catalog Annotated Percentage(%)',round((annotated_number/(len(cluster_id)-1))*100,2))
                        ]
        
        #domain mapping parser
        file=open(data_path+'/pfam/pfam_result.txt')
        temp=file.read()
        temp=temp.split('\n')[3:]
        temp=temp[:len(temp)-11]
        domain_table=[]
        domains=[]
        names=[]
        for i in range(len(temp)):
            t=re.split('\s+',temp[i])
            new_t=t[0:3]
            new_t.append(t[3].split('|')[0])
            new_t.extend(t[4:22])
            new_t.append((' ').join(t[22:]))
            domain_table.append(new_t)  
        
        pfam_table=pd.DataFrame(domain_table,
                                 columns=['domain','domain_accession','tlen','query_name',
                                        'query_accession','qlen','evalue','score','bias',
                                        'number','ndom','cevalue','ievalue','domain_score',
                                        'domain_bias','from_hmm','to_hmm','from_ali','to_ali',
                                       'from_env','to_env','acc','description'
                                       ])        
        
        
        non_dup_pfam=pfam_table.drop_duplicates(subset=['domain','query_name'])
        non_dup_pfam.to_csv(data_path+'/pfam/pfam_parsed.csv',index=False)
        catalog_number={}
        des={}
        access={}
        for i in non_dup_pfam.index:
            dm=non_dup_pfam.loc[i]['domain']
            gene=non_dup_pfam.loc[i]['query_name']
            try:                
                catalog_number[dm]+=1
                des[dm]=non_dup_pfam.loc[i]['description']
                access[dm]=non_dup_pfam.loc[i]['domain_accession']
            except:
                catalog_number[dm]=1
                des[dm]=non_dup_pfam.loc[i]['description']
                access[dm]=non_dup_pfam.loc[i]['domain_accession']
                
        domain_freq_rank=sorted(catalog_number, key=catalog_number.get,reverse=True)
        dm_freq=[]
        dm_des=[]
        for i in range(29,-1,-1):
            dm_freq.append(catalog_number[domain_freq_rank[i]])
            dm_des.append(des[domain_freq_rank[i]])
            
        domain_plot=[mark_safe(json.dumps(domain_freq_rank[29::-1])),dm_freq,mark_safe(json.dumps(dm_des))]        
        out_domain_table=[]
        for i in domain_freq_rank:
            out_domain_table.append((i,access[i],catalog_number[i],des[i]))
            
        pd.DataFrame(out_domain_table).to_csv(data_path+'/pfam/domain_frequency.csv',header=['domain','accession','frequency','description'],index=False)    
        sp.run("cd "+data_path+"/pfam;tar zcvf "+data_path+"/user_pfam_result.tar.gz pfam_* pred_not_annot_seq.fa domain_frequency.csv",shell=True)

        #functional parser
        go_terms=pd.read_csv(data_path+"/eggnog/GO_term_annotation.txt",sep='\t')
        go_type=['molecular_function','biological_process','cellular_component']
        go_type_output=['Molecular Function','Biological Process','Cellular Component']
        go_terms.columns=['Protein_Accession','GO_Category','GO_Accession','GO_Description','GO Level']
        
        
        go_dict=pd.DataFrame(data=go_terms['GO_Description'])
        go_dict.index=list(go_terms['GO_Accession'])
        go_dict.columns=['descp']
        go_dict=go_dict.to_dict()
        
        col_name_temp=list(emapper_table.columns)
        col_name_temp[0]="query_name"
        emapper_table.columns=col_name_temp
        emapper_table['query_name']=emapper_table.query_name.str.split('|').str.get(0)
        names=list(emapper_table['query_name'])
        emapper_abund=[]
        for i in names:
            emapper_abund.append(rep_gene_total_abundance[i])
        
        emapper_table=emapper_table.assign(TPM_Abundance=emapper_abund)
        
        emapper_table.to_csv(data_path+'/eggnog/parsed_eggnog_abundance.csv',index=False)
        
        with open (settings.SUPPLEMENT_APP_BIN+"/mean_baseline", 'rb') as fp:
            mean = pickle.load(fp)
            
        with open (settings.SUPPLEMENT_APP_BIN+"/std_baseline", 'rb') as fp:
            std = pickle.load(fp) 

        with open (settings.SUPPLEMENT_APP_BIN+"/non_na_percentage", 'rb') as fp:
            non_na_percentage = pickle.load(fp) 
        
        go_plot={}
        for g_type in go_type:
            mf=go_terms[go_terms['GO_Category']==g_type]
            go=list(mf['GO_Accession'])
            p_acc=list(mf['Protein_Accession'])
            func_based_go_abund={}
            for i in range(len(go)):
                n=p_acc[i].split('|')[0]
                try:
                    func_based_go_abund[go[i]]+=rep_gene_total_abundance[n]
                except:
                    func_based_go_abund[go[i]]=rep_gene_total_abundance[n]
            
            func_based_go_abund_keys=func_based_go_abund.keys()
            invalid=[]
            z_score={}
            z_for_sort={}
            go_z_out=[]
            for i in func_based_go_abund_keys:
                try:
                    if(std[i]==0):
                        z_score[i]="NA"
                        go_z_out.append((i,go_dict['descp'][i],z_score[i],func_based_go_abund[i],mean[i],std[i],non_na_percentage[i]))
                    else:
                        z_score[i]=(func_based_go_abund[i]-mean[i])/std[i]
                        z_for_sort[i]=abs(z_score[i])
                        go_z_out.append((i,go_dict['descp'][i],z_score[i],func_based_go_abund[i],mean[i],std[i],non_na_percentage[i]))
                except KeyError:
                    z_score[i]="NA" 
                    go_z_out.append((i,go_dict['descp'][i],z_score[i],func_based_go_abund[i],"NA","NA","NA"))
            
            #sort z score with absolute value
            z_key=sorted(z_for_sort, key=z_for_sort.get,reverse=True)
            
            abund_out=[]
            desc_out=[]
            go_key_out=[]
            #get top 10 z score
            top_go_counter=0
            for i in z_key:
                if(top_go_counter>=10):
                    break
                if(non_na_percentage[i]>99):
                    go_key_out.append(i)
                    abund_out.append(z_score[i])
                    desc_out.append(go_dict['descp'][i])
                    top_go_counter=top_go_counter+1
            
            go_key_out.reverse()
            abund_out.reverse()
            desc_out.reverse()
            
            #output csv table: go, description, z, tpm, mean, std,non_nan_percentage
            pd.DataFrame(go_z_out).to_csv(data_path+'/eggnog/'+g_type+'_go_zscore.csv',header=['GO_term','description','z_score','tpm','mean','std','non_NA_percentage'],index=False)
            
            go_plot[g_type]=[mark_safe(json.dumps(go_key_out)),abund_out,mark_safe(json.dumps(desc_out))]
        
        sp.run("cd "+data_path+"/eggnog;tar zcvf "+data_path+"/user_eggnog_result.tar.gz parsed_eggnog_abundance.csv GO_term_annotation.txt *_go_zscore.csv",shell=True)
        
        
        output_dictionary={
                             'result':mark_safe(json.dumps(result)),
                             'a5_result_pair':a5_result_pair,
                             'taxo_output':taxo_output,
                             'taxo_plot':taxo_plot,
                             'gene_pred_table':gene_pred_table,
                             'abundance_table':abundance_table[:200],
                             'domain_plot':domain_plot,
                             'out_domain_table':out_domain_table,
                             'go_plot':go_plot,
        }
        
        with open(data_path+'/output_dict', 'wb') as fp:
            pickle.dump(output_dictionary, fp)
        
        #overview parser
        
        user_root=data_path.split('/')[1]
        uid=data_path.split('/')[2]
        p=sp.run("cd /"+user_root+";tar zcvf "+
        uid+".tar.gz --exclude=raw --exclude=kraken/*.fastq --exclude=.snakemake "+
        "--exclude=snake_based_paths --exclude=domain_mapping --exclude=taxo_abundance --exclude=meta_function --exclude=meta_genepred --exclude=meta_a5 --exclude=meta_a5/user.s? "+
        "--exclude=QC --exclude=taxonomic.tar.gz --exclude=user_pfam_result.tar.gz --exclude=user_eggnong_result.tar.gz --exclude=output_dict "+
        uid+";mv "+uid+".tar.gz "+data_path+"/myjob.tar.gz",shell=True)
        
        
        #make softlink to static and assets
        
        tmp_path=str(Path('../').resolve().joinpath('src','assets'))
        p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
        tmp_path=str(Path('../').resolve().joinpath('src','static'))
        p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
        
    except:
        return -1
    
    return 0
    
    
def run_meta_pipeline(sfile_path,uid,data_path,parameters):
    try:
        user=meta_User_Job.objects.filter(user_id=uid)[0]

        user.total_status="RUNNING"
        user.start_time=datetime.datetime.now()
        user.save(update_fields=['total_status','start_time'])
        
        if not path.exists(data_path):
            makedirs(data_path)
        
        # get lists of tools and databases that are conducted in this task
        selected_col_name = 'meta'
        if(parameters['kraken']=='yes'): selected_col_name += '_kraken'
        
        tmp_df = pd.read_csv(settings.TOOLS_LIST, sep="\t", engine='python')
        tools_df = tmp_df.loc[tmp_df[selected_col_name]==1][tmp_df.columns[:4]]
        tools_df.to_csv(data_path+'/tools_list.tsv', sep="\t", index=False)
        tmp_df = pd.read_csv(settings.DATABASES_LIST, sep="\t", engine='python')
        databases_df = tmp_df.loc[tmp_df[selected_col_name]==1][tmp_df.columns[:3]]
        databases_df.to_csv(data_path+'/databases_list.tsv', sep="\t", index=False)
        
        # get MiDSystem version
        with open(data_path+'/MiDSystem.version', 'w') as fp:
            fp.write(settings.VERSION)
        
        # start data preparation
        user.data_preparation_status="RUNNING"
        user.save(update_fields=['data_preparation_status'])
        
        data_tmp_path = str(Path(UPLOAD_BASE_PATH).resolve().joinpath(parameters['upload_id']))
        data_preparation_stat = run_data_preparation(data_tmp_path, data_path, parameters['dict_urls'],parameters['kraken'])
        if(data_preparation_stat!=0):
            print("pipeline stop at data preparation")
            user.error_log="DATA"
            user.data_preparation_status="FAILED"
            user.quality_check="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','data_preparation_status','quality_check','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.data_preparation_status="SUCCESSFUL"
            user.save(update_fields=['data_preparation_status'])
        
        #start qc
        user.quality_check="RUNNING"
        user.save(update_fields=['quality_check'])
        
        if(parameters['kraken']=='yes'):
            copy_snake(sfile_path+"/snake_kraken",data_path+"/snake_kraken",data_path,0,{})
            makedirs(str(Path(data_path).resolve().joinpath('raw')))
            kraken_status=run_kraken(data_path)
            if(kraken_status!=0):
                print("pipeline stop at KRAKEN")
                failed_tar_result(data_path)                
                user.error_log="QC"
                user.quality_check="FAILED"
                user.total_status="FAILED"
                user.end_time=datetime.datetime.now()
                user.save(update_fields=['error_log','quality_check','total_status','end_time'])
                failed_email(data_path)
                return -1
                
        
        copy_snake(sfile_path+"/QC",data_path+"/QC",data_path,0,{})
        qc_status=run_QC(data_path)
        if(qc_status!=0):
            print("pipeline stop at QC")
            failed_tar_result(data_path)
            user.error_log="QC"
            user.quality_check="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','quality_check','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.quality_check="SUCCESSFUL"
            user.save(update_fields=['quality_check'])
        
        #start a5 assembly
        user.a5_status="RUNNING"
        user.save(update_fields=['a5_status'])
        copy_snake(sfile_path+"/meta_a5",data_path+"/meta_a5",data_path,0,parameters['de_novo'])
        a5_sta=run_meta_A5(data_path)
        if(a5_sta!=0):
            print("pipeline stop at A5!!!!!")
            failed_tar_result(data_path)            
            user.error_log="A5"
            user.a5_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','a5_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.a5_status="SUCCESSFUL"
            user.save(update_fields=['a5_status'])
        
        #start taxonomic abundance
        user.abundance_status="RUNNING"
        user.save(update_fields=['abundance_status'])
        parameters['taxonomic']['additional_commands']=""
        file_type=parameters['taxonomic']['file_type'].split(',')
        for i in file_type:
            if(i!="png"):
                parameters['taxonomic']['additional_commands']+=settings.NON_CONDA_APP_BIN+"/GraphlAn/graphlan/graphlan.py --dpi 300 merged_abundance.xml user_taxo."+i+" --format "+i+" --size=20;"
        copy_snake(sfile_path+"/taxo_abundance",data_path+"/taxo_abundance",data_path,0,parameters['taxonomic'])
        taxo_sta=run_taxo(data_path)
        if(taxo_sta!=0):
            print("pipeline stop at Taxonomic!!!!!")
            failed_tar_result(data_path)            
            user.error_log="ABUND"
            user.abundance_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','abundance_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.abundance_status="SUCCESSFUL"
            user.save(update_fields=['abundance_status'])
        
        
        #start gene prediction and clustering
        user.gene_prediction_status="RUNNING"
        user.save(update_fields=['gene_prediction_status'])
        copy_snake(sfile_path+"/meta_genepred",data_path+"/meta_genepred",data_path,0,parameters['gene_prediction'])
        pred_sta=run_pred(data_path)
        if(pred_sta!=0):
            print("pipeline stop at Gene Prediction and Clustering!!!!!")
            failed_tar_result(data_path)            
            user.error_log="GM"
            user.gene_prediction_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','gene_prediction_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.gene_prediction_status="SUCCESSFUL"
            user.save(update_fields=['gene_prediction_status'])
        
        #start functional annotation and functional abundance
        user.functional_status="RUNNING"
        user.save(update_fields=['functional_status'])
        copy_snake(sfile_path+"/meta_function",data_path+"/meta_function",data_path,0,parameters['functional'])
        func_sta=run_func(data_path)
        if(func_sta!=0):
            print("pipeline stop at Functional Annotation and Abundance!!!!!")
            failed_tar_result(data_path)            
            user.error_log="EGG"
            user.functional_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','functional_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.functional_status="SUCCESSFUL"
            user.save(update_fields=['functional_status'])
        
        #start domain mapping
        user.non_annotate_status="RUNNING"
        user.save(update_fields=['non_annotate_status'])
        copy_snake(sfile_path+"/domain_mapping",data_path+"/domain_mapping",data_path,0,parameters['non_annotate'])
        domain_sta=run_domain(data_path)
        if(domain_sta!=0):
            print("pipeline stop at Domain Mapping!!!!!")
            failed_tar_result(data_path)            
            user.error_log="NONANNO"
            user.non_annotate_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','non_annotate_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.non_annotate_status="SUCCESSFUL"
            user.save(update_fields=['non_annotate_status'])
        
        #start parsing result
        user.parsing_status="RUNNING"
        user.save(update_fields=['parsing_status'])
        parser_stat=run_meta_parser(data_path)
        if(parser_stat!=0):
            print("pipeline stop at Parser!!!!!")
            failed_tar_result(data_path)            
            user.error_log="PARSER"
            user.parsing_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','parsing_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.parsing_status="SUCCESSFUL"
            user.save(update_fields=['parsing_status'])
        
        user.total_status="SUCCESSFUL"
        user.end_time=datetime.datetime.now()
        user.save(update_fields=['total_status','end_time'])
        print("Meta successful!!!!!!!!!")
    
    
    except:
        print("pipeline stop due to system error!!!")
        user.total_status="FAILED"
        user.error_log="SYSTEM"
        user.end_time=datetime.datetime.now()
        user.save(update_fields=['error_log','total_status','end_time'])
        #due to system error: do not tar the result
        failed_email(data_path)
        print("Meta failed....")
        return -1
    
    #send mail for successful task TODO:change fail_silently=True     
    mail=user.mail
    send_mail('Task Successfully Completed!', 'Your Link:'+web_url+"/meta/"+uid+"/report", None,
    [mail], fail_silently=True)
    
    return 0
