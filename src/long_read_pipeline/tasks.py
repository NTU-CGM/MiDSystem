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
from .models import long_User_Job
from pipeline.models import bac_species
from .views import UPLOAD_BASE_PATH
from django.utils.html import mark_safe
from django.conf import settings
import shutil
import MySQLdb
import re
import gzip
from pipeline.googledrive_downloader import GoogleDriveDownloader
import requests, requests_ftp
import sys

web_url=settings.WEB_URL #remember to change this
pep_db=settings.BAC_PROTEIN_DB
cdna_db=settings.BAC_CDNA_DB
SNAKEMAKE_BIN = path.join(settings.CONDA_APP_BIN, 'snakemake')
env = environ.copy()
env['PATH'] = settings.CONDA_APP_BIN + ':' + env['PATH']
env['CONDA_APP_BIN'] = settings.CONDA_APP_BIN
env['NON_CONDA_APP_BIN'] = settings.NON_CONDA_APP_BIN
env['SUPPLEMENT_APP_BIN'] = settings.SUPPLEMENT_APP_BIN

def copy_snake(fromf,tof,data_path,param={}):
    snake_based_paths = path.join(path.dirname(tof), 'snake_based_paths')
    if not path.exists(snake_based_paths):
        with open(snake_based_paths, 'w') as fp:
            for s in dir(settings):
                if '_DB' in s.upper()[-3:]:
                    fp.write("%s = '%s/'\n" % (s.upper(), eval("settings.%s" % s)))
            fp.write("%s = '%s/'\n" % ('CONDA_APP_BIN', settings.CONDA_APP_BIN))
            fp.write("%s = '%s/'\n" % ('NON_CONDA_APP_BIN', settings.NON_CONDA_APP_BIN))
            fp.write("%s = '%s/'\n" % ('SUPPLEMENT_APP_BIN', settings.SUPPLEMENT_APP_BIN))
    
    para_number=len(param)
    k=list(param.keys())
    with open(fromf) as from_file:
        with open(tof,'w') as to_file:
            to_file.write("user_root='"+data_path+"/'\n")
            
            for i in range(0,para_number):
                to_file.write(k[i]+"='"+param[k[i]]+"'\n")
            
            shutil.copyfileobj(from_file, to_file)

def failed_tar_result(data_path):
    user_root=data_path.split('/')[1]
    uid=data_path.split('/')[2]
    
    #let check equal True to let pipeline catch the SYSTEM error
    p=sp.run("cd /"+user_root+";tar zcvf "+
    uid+".tar.gz --exclude=raw --exclude=reference --exclude=.snakemake "+
    "--exclude=snake_based_paths --exclude=long_aug --exclude=aug_interpro --exclude=long_before_ref --exclude=long_gm --exclude=gm_interpro "+
    "--exclude=long_QC --exclude=long_remap --exclude=snake_tree --exclude=tree/orthomcl/orthomcl.config --exclude=output_dict "+
    "--exclude=GO.tar.gz --exclude=blast.tar.gz "+
    uid+";mv "+uid+".tar.gz "+data_path+"/myjob.tar.gz",shell=True)
    
    #make softlink to static and assets
        
    tmp_path=str(Path('../').resolve().joinpath('src','assets'))
    p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
    tmp_path=str(Path('../').resolve().joinpath('src','static'))
    p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
    return 0

def failed_email(data_path):
    #send mail for failed task TODO:change fail_silently=True 
    uid=data_path.split('/')[2]
    user=long_User_Job.objects.filter(user_id=uid)[0]
    mail=user.mail
    send_mail('Task Failed!', 'Your link for the report:'+web_url+"/long_read/"+uid+"/report", None,
    [mail], fail_silently=True)
    return 0
        

def run_data_preparation(source_path, destination_path, dict_urls):
    try:
        if not path.exists(destination_path):
            makedirs(destination_path)
        dest_raw_path = str(Path(destination_path).resolve().joinpath('raw'))
        if not path.exists(dest_raw_path):
            makedirs(dest_raw_path)
        if not path.exists(source_path):
            makedirs(source_path)
        
        if len(dict_urls): # data come from URLs
            # Process download one by one
            for new_file_name, url in dict_urls.items():
                # m1 = re.search('google\.com.+id=(.+)\&*', url) ## Retired
                m1 = re.search('google\.com\/file\/d\/(.+)\/', url)
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
        shutil.copy2(str(Path(source_path).resolve().joinpath('long.fastq')), dest_raw_path)
        if path.exists(str(Path(source_path).resolve().joinpath('R1.fastq'))):
            shutil.copy2(str(Path(source_path).resolve().joinpath('R1.fastq')), dest_raw_path)
        if path.exists(str(Path(source_path).resolve().joinpath('R2.fastq'))):
            shutil.copy2(str(Path(source_path).resolve().joinpath('R2.fastq')), dest_raw_path)
        shutil.rmtree(source_path)
        return 0
        
    except Exception as e:
        print(e)
        return -1

def run_QC(data_path, hybrid_flag):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'long_QC')
        ], env=env, check=True)
    except:
        return -1
    
    check_file = [data_path+"/longqc/long_trimmed.fastq", 
                  data_path+"/longqc/web_summary.html"]
    
    if hybrid_flag == 1:
        check_file.extend([data_path+"/fastqc/R1_fastqc.html",
                           data_path+"/fastqc/R2_fastqc.html",
                           data_path+"/multiqc/multiqc_report.html",
                           data_path+"/trimmomatic/R1.trimmed.fastq",
                           data_path+"/trimmomatic/R2.trimmed.fastq",
                           data_path+"/trimmomatic/fastqc/R1.trimmed_fastqc.html",
                           data_path+"/trimmomatic/fastqc/R2.trimmed_fastqc.html",
                           data_path+"/trimmomatic/multiqc/multiqc_report.html"])
    
    try:
        for i in range(len(check_file)):
            Path(check_file[i]).resolve()
        print('QC Done')
    except FileNotFoundError:
        print('QC Error')
        return -1
    
    return 0

def run_assembly(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'long_before_ref')
        ], env=env, check=True)
    except:
        return -1
        
    check_file=[data_path+"/unicycler/assembly.fasta",
                data_path+"/quast/contig/report.pdf",
                data_path+"/busco/contig/run_unicycler/short_summary_unicycler.txt"]
    
    try:
        for i in range(len(check_file)): 
            Path(check_file[i]).resolve()
        print('Unicycler Done')
    except FileNotFoundError:
        print('Unicycler Error')
        return -1
    
    return 0

def run_remap(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'long_remap')
        ], env=env, check=True)
    except:
        return -1
    
    check_file=[data_path+"/bowtie2/contig/remapping.bam"]
    
    try:
        Path(check_file[0]).resolve()
        print('Bowtie Done')
    except FileNotFoundError:
        print('Bowtie Error')
        return -1
    
    return 0

def run_aug(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'long_aug')
        ], env=env, check=True)
    except:
        return -1
    
    check_file=[data_path+"/augustus/protein_seq.fasta",
                data_path+"/busco/protein/run_aug_protein/short_summary_aug_protein.txt",
                data_path+"/blast/spe_blastp.txt"]  
    
    try:
        for i in range(len(check_file)):
            Path(check_file[i]).resolve()
        print('Augustus Done')
    except FileNotFoundError:
        print('Augustus Error')
        return -1
    
    return 0
    
def run_gm(data_path):
    try:
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'long_gm'),
        ], env=env, check=True)
    except:
        return -1
    
    check_file=[data_path+"/genemark/protein_combined.fasta",
                data_path+"/busco/protein/run_gm_protein/short_summary_gm_protein.txt",
                data_path+"/blast/spe_blastp.txt"] 
    
    try:
        for i in range(len(check_file)):
            Path(check_file[i]).resolve()
        print('GenemarkS Done')
    except FileNotFoundError:
        print('GenemarkS Error')
        return -1
    
    return 0

def run_interpro(data_path, aug_flag):
    try:
        if(aug_flag==0):
            p = sp.run([
                SNAKEMAKE_BIN,
                '-s', path.join(data_path, 'gm_interpro')
            ], env=env, check=True)
        else:
            p = sp.run([
                SNAKEMAKE_BIN,
                '-s', path.join(data_path, 'aug_interpro')
            ], env=env, check=True)
    except:
        return -1
    
    check_file=[data_path+"/interproscan/interproscan_gene.tsv"]  
    
    try:
        Path(check_file[0]).resolve()
        print('Interproscan Done')
    except FileNotFoundError:
        print('Interproscan Error')
        return -1
    
    return 0

def run_tree(data_path,taxid,aug_flag,sample_name):
    try:
        uid=data_path.split('/')[-1]
        uid=uid.replace("-","_")
        print("start print uid")
        print(uid)
        print("read config")
        sfile_path=str(Path('../').resolve().joinpath('src','config'))
        file = open(sfile_path+"/password.txt","r")
        temp=file.read()
        print("start db")
        db = MySQLdb.connect("localhost",temp.split('\n')[0], temp.split('\n')[1]) #hide this for production
        cursor = db.cursor()
        print("db connect")
        sql='DROP DATABASE IF EXISTS `'+uid+'`'
        cursor.execute(sql)
        print("db dropped")
        sql = 'CREATE DATABASE `'+uid+'`'
        cursor.execute(sql)   
        print("db created")
        
        #get the filename,tax_id,rename
        bac=bac_species.objects.filter(tax_id__in=taxid)
        meta_bac=[]
        print("start copy cdna")
        #(short_filename,file_name,cdna_filename)
        #ls |grep "Shigella_boydii_cdc_3083_94."|xargs gzip -cd > test1111.fa
        for b in bac:
            #processing peptide file
            p=sp.run('mkdir -p '+data_path+'/tree/cdna', shell=True, check=True)
            fname=sp.run('ls '+pep_db+'/'+str(b.collection)+' |grep -P "^'+str(b.file_name)+'\."', shell=True, check=True, stdout=sp.PIPE).stdout.decode('utf-8')
            fname=fname.split('\n')[0]
            p=sp.run('gunzip -c '+pep_db+'/'+str(b.collection)+'/'+fname+' > '+data_path+'/tree/'+fname[:-3], shell=True, check=True)
            
            #processing cdna file
            cdna=sp.run('ls '+cdna_db+' |grep -P "^'+str(b.file_name)+'\."', shell=True, check=True ,stdout=sp.PIPE).stdout.decode('utf-8')
            cdna=cdna.split('\n')[0]
            p=sp.run('gunzip -c '+cdna_db+'/'+cdna+' > '+data_path+'/tree/cdna/'+cdna[:-3], shell=True, check=True)
            meta_bac.append((str(b.s_name)[0:3]+'_'+str(b.tax_id),fname[:-3],cdna[:-3]))
        #print(meta_bac)
        
        #TODO: block invalid sample_name
        if(aug_flag==0):
            p=sp.run('cp '+data_path+'/genemark/protein_combined.fasta'+' '+data_path+'/tree/', shell=True, check=True)
            p=sp.run('cp '+data_path+'/genemark/cdna_seq.fasta'+' '+data_path+'/tree/cdna', shell=True, check=True)
            meta_bac.append((sample_name,'protein_combined.fasta','cdna_seq.fasta'))
        else:
            p=sp.run('cp '+data_path+'/augustus/protein_seq.fasta'+' '+data_path+'/tree/', shell=True, check=True)
            p=sp.run('cp '+data_path+'/augustus/cdna_seq.fasta'+' '+data_path+'/tree/cdna', shell=True, check=True)
            meta_bac.append((sample_name,'protein_seq.fasta','cdna_seq.fasta'))

        #write orhotmcl config file here
        
        with open(sfile_path+'/orthomcl.config') as from_file:
            with open(data_path+'/tree/orthomcl.config','w') as to_file:
                to_file.write("dbConnectString=dbi:mysql:"+uid+"\n")
                shutil.copyfileobj(from_file, to_file)      
        
        #call snakemake here

        with open(str(Path('../').resolve().joinpath('src','snakefiles'))+'/snake_tree') as from_file:
            with open(data_path+'/snake_tree','w') as to_file:
                to_file.write("user_root='"+data_path+"/'\n")
                to_file.write("bac_meta="+str(meta_bac)+"\n")
                shutil.copyfileobj(from_file, to_file)
        
        p = sp.run([
            SNAKEMAKE_BIN,
            '-s', path.join(data_path, 'snake_tree')
        ], env=env)
        
        
        sql='DROP DATABASE `'+uid+'`'
        cursor.execute(sql)
        db.close()
    
    except:
        return -1
    
    check_file=[data_path+"/tree/raxml/mytree.png"]
    
    try:
        Path(check_file[0]).resolve()
        print('Tree Done')
    except FileNotFoundError:
        print('Tree Error')
        return -1
    
    return 0

def run_parser(data_path, HYBRID, TREE):  
    try:
        #trimmomatic parser
        trimmomatic_result=[]
        trimmomatic_result.append(["status","reads number"])
        if HYBRID:
            file = open(data_path+"/trimmomatic/trimmomatic.log", "r")
            temp=file.read()
            ll=temp.split('\n')
            parsing=ll[4]
            output_string=["Input Read Pairs","Both Surviving","Forward Only Surviving","Reverse Only Surviving","Dropped"]
            numbers=[int(s) for s in parsing.split(" ") if s.isdigit()]
            for i in range(1,len(numbers)):
                trimmomatic_result.append([output_string[i],numbers[i]])
            
            file.close()
        
        #busco contig parser
        file = open(data_path+"/busco/contig/run_unicycler/short_summary_unicycler.txt", "r")
        temp=file.read()
        ll=temp.split('\n\t')
        new_ll=[]
        for i in ll[1:]:
            new_ll.append(i.split('\t')[0])
        out_string=['Complete(C)','Fragmented(F)','Missing(M)']
        out_number=[new_ll[1],new_ll[4],new_ll[5]]
        busco_contig_result=[]
        busco_contig_result.append(["BUSCOs","number"])
        for i in range(0,len(out_number)):
            busco_contig_result.append([out_string[i],int(out_number[i])])

        busco_contig_n=new_ll[6]
        busco_contig_single=int(new_ll[2])/int(new_ll[1])
        busco_contig_duplicate=int(new_ll[3])/int(new_ll[1])
        file.close()
        
        #bowtie ref parser
        bowtie_total_reads=0
        alignment_rate=0
        bowtie_result=[]
        if HYBRID:
            file = open(data_path+'/bowtie2/contig/bowtie2.log')
            temp=file.read()
            data=temp.split('\n')
            numbers=[]
            for parsing in data:
                numbers=numbers+[int(s) for s in parsing.split(" ") if s.isdigit()]

            status=['total reads',
                    'paried, aligned concordantly exactly 1 time',
                    'paried, aligned concordantly >1 times',
                    'paired, aligned discordantly 1 time',
                    'aligned 0 times',
                    'aligned 1 times',
                    'aligned >1 times'
                   
                   ]
            reads_number=[numbers[1]*2,numbers[4]*2,numbers[6]*2,numbers[9]*2,numbers[14],numbers[16],numbers[18]]
            bowtie_total_reads=numbers[0]*2
            alignment_rate=data[-2]
            bowtie_result.append(["Status","Reads Number"])
            for i in range(1,len(reads_number)):
                bowtie_result.append([status[i],reads_number[i]])
            
            file.close()
        
        #gene prediction parser and file reader for busco prediction
        try:
            #genemark
            Path(data_path+'/genemark/gms.log').resolve()
            predicted_tool="GeneMarkS"
            cdna_path="genemark/cdna_seq.fasta"
            gff_path="genemark/assembly.gff"
            protein_path="genemark/protein_combined.fasta"
            p=str(sp.check_output('awk -f '+str(Path('../').resolve().joinpath('src','supplement_code'))+'/count-gff-content.awk '+data_path+'/genemark/EVM.gff|head -n1',shell=True))
            file = open(data_path+"/busco/protein/run_gm_protein/short_summary_gm_protein.txt","r")
        except:
            #augustus
            predicted_tool="Augustus"
            cdna_path="augustus/cdna_seq.fasta"
            gff_path="augustus/augustus.gff"
            protein_path="augustus/protein_seq.fasta"
            p=str(sp.check_output('awk -f '+str(Path('../').resolve().joinpath('src','supplement_code'))+'/count-gff-content.awk '+data_path+'/augustus/EVM.gff|head -n1',shell=True))
            file = open(data_path+"/busco/protein/run_aug_protein/short_summary_aug_protein.txt","r")

        gene_stat=p.replace('\\t','').replace('\\n','').replace("b'","").replace("'","").split(",")
        gene_pred_table=[]
        for i in gene_stat:
            temp=i.split(":")
            gene_pred_table.append((temp[0],temp[1]))
        
        #busco prediction parser (this part can be summmarzied to function!!!)
        temp=file.read()
        ll=temp.split('\n\t')
        new_ll=[]
        for i in ll[1:]:
            new_ll.append(i.split('\t')[0])
        out_string=['Complete(C)','Fragmented(F)','Missing(M)']
        out_number=[new_ll[1],new_ll[4],new_ll[5]]
        busco_pred_result=[]
        busco_pred_result.append(["BUSCOs","number"])
        for i in range(0,len(out_number)):
            busco_pred_result.append([out_string[i],int(out_number[i])])

        busco_pred_n=new_ll[6]
        busco_pred_single=int(new_ll[2])/int(new_ll[1])
        busco_pred_duplicate=int(new_ll[3])/int(new_ll[1])
        file.close()
        
        #blast parser
        #http://www.metagenomics.wiki/tools/blast/blastn-output-format-6
        #command:outfmt '6 std qcovs staxids'
        df=pd.read_csv(data_path+'/blast/spe_blastp.txt',sep='\t',
                        names=['gene','protein','identical_match','alignment_length','mismatch',
                               'gap','qstart','qend','sstart','send','evalue','bit_score','coverage','tax_id'])
        blast_gene_number=len(set(df['gene']))

        ids = df["gene"]
        gene_multi_prot_loc=df[ids.isin(ids[ids.duplicated()])]
        gene_multi_prot_loc.to_csv(data_path+'/blast/one_gene_multi_protein_loc.csv')
        number_gene_multi_prot_loc=len(set(gene_multi_prot_loc['gene']))

        ids = df["protein"]
        multi_gene_prot_loc=df[ids.isin(ids[ids.duplicated()])]
        multi_gene_prot_loc.to_csv(data_path+'/blast/multi_gene_one_protein.csv')
        number_multi_gene_prot_loc=len(set(multi_gene_prot_loc['protein']))

        p=sp.run('cd '+data_path+'/;tar zcvf blast.tar.gz ./blast/', shell=True)

        df2=df.drop_duplicates('gene')
        coverage=[]
        cov_range=[95, 90, 80, 70, 60, 50]
        for i in cov_range:
            coverage.append(len(df2.loc[df2['coverage']>=i]))
        coverage_perc=[round(i*100/blast_gene_number,4) for i in coverage]
        blast_table=list(zip(['Predicted Gene Number','Blasted Gene Number',
         'One gene maps to multiple locations on an identical protein','Multiple genes mapped to the identical NR protein'],
        [gene_pred_table[0][1],blast_gene_number,number_gene_multi_prot_loc,number_multi_gene_prot_loc]))

        #kegg parser
        kegg=pd.read_csv(data_path+'/interproscan/KEGG_parsed.txt',sep='\t',names=['Gene','Entry','Pathway_Name'])
        gene=list(kegg['Gene'])
        entry=list(kegg['Entry'])
        pname=list(kegg['Pathway_Name'])
        kegg_output=[]
        for i in range(len(gene)):
            kegg_output.append((gene[i].split('|')[0],entry[i],pname[i]))

        #go term parser
        goterm=pd.read_csv(data_path+'/interproscan/GO_term_annotation.txt',sep='\t')
        goslim=pd.read_csv(data_path+'/interproscan/GOSlim_annotation.txt',sep='\t')
        meta_goslim=pd.read_csv(data_path+'/interproscan/GOSlim_meta_annotation.txt',sep='\t')
        if(len(goterm)<5000):
            big_flag=0
        else:
            big_flag=1


        go_output=[]
        go_type=['molecular_function','biological_process','cellular_component']
        go_type_output=['Molecular Function','Biological Process','Cellular Component']
        go_plot={}
        for t in range(len(go_type)):
            mole_goterm=goterm[goterm['GO Category']==go_type[t]]
            goacc=list(mole_goterm['GO Accession'])
            godes=list(mole_goterm['GO Description'])
            gene=list(mole_goterm['Protein Accession'])
            level=list(mole_goterm['GO Level'])
            
            most_com=list(reversed(Counter(goacc).most_common(10)))
            go_plot_access=[]
            go_plot_number=[]
            go_plot_descrip=[]
            for i in range(len(most_com)):
                go_plot_access.append(most_com[i][0])
                go_plot_number.append(most_com[i][1])
                go_plot_descrip.append(mole_goterm[mole_goterm['GO Accession']==most_com[i][0]]['GO Description'].iloc[0])
            
            go_plot[go_type[t]]=[mark_safe(json.dumps(go_plot_access)),go_plot_number,mark_safe(json.dumps(go_plot_descrip))]
            
            
            mole_go_output=[]
            for i in range(len(gene)):
                mole_go_output.append((goacc[i],godes[i],gene[i].split('|')[0],level[i]))
                
            go_output.append((go_type[t],go_type_output[t],mole_go_output))
            df2=pd.DataFrame(mole_go_output,columns=['GO Accession','GO Description','Protein_Accession','GO Level'])
            df2=df2.sort_values(by=['Protein_Accession'])
            df2.to_csv(data_path+'/interproscan/'+go_type[t]+'.csv',index=False)

        goslim_output=[]
        for t in range(len(go_type)):
            mole_goterm=goslim[goslim['GO Category']==go_type[t]]
            goacc=list(mole_goterm['GOSlim Accession'])
            godes=list(mole_goterm['GOSlim Description'])
            gene=list(mole_goterm['Protein Accession'])
            level=list(mole_goterm['GOSlim Level'])
            mole_go_output=[]
            for i in range(len(gene)):
                mole_go_output.append((goacc[i],godes[i],gene[i].split('|')[0],level[i]))
                
            goslim_output.append((go_type[t],go_type_output[t],mole_go_output))
            df2=pd.DataFrame(mole_go_output,columns=['GO Accession','GO Description','Protein_Accession','GO Level'])
            df2=df2.sort_values(by=['Protein_Accession'])
            df2.to_csv(data_path+'/interproscan/goslim_'+go_type[t]+'.csv',index=False)

        for t in range(len(go_type)):
            mole_goterm=meta_goslim[meta_goslim['GO Category']==go_type[t]]
            goacc=list(mole_goterm['GOSlim Accession'])
            godes=list(mole_goterm['GOSlim Description'])
            gene=list(mole_goterm['Protein Accession'])
            level=list(mole_goterm['GOSlim Level'])
            mole_go_output=[]
            for i in range(len(gene)):
                mole_go_output.append((goacc[i],godes[i],gene[i].split('|')[0],level[i]))
                
            df2=pd.DataFrame(mole_go_output,columns=['GO Accession','GO Description','Protein_Accession','GO Level'])
            df2=df2.sort_values(by=['Protein_Accession'])
            df2.to_csv(data_path+'/interproscan/meta_goslim_'+go_type[t]+'.csv',index=False)


        p=sp.run('cd '+data_path+'/;tar zcvf GO.tar.gz ./interproscan/*.csv', shell=True)

        #tree parser
        species_table=[]
        if TREE:
            file = open(data_path+"/snake_tree","r")
            temp=file.read()
            ll=temp.split('\n')
            bac_meta=list(ast.literal_eval(ll[1].split('=')[1].replace('[','').replace(']','')))#bac_meta has the information
            for i in range(0,len(bac_meta)-1):
                bac_s=bac_species.objects.get(tax_id=bac_meta[i][0].split('_')[-1])
                species_table.append((bac_s.s_name,bac_s.tax_id))
            
            file.close()
        
        # collect results
        output_dictionary={
                         'trimmomatic_result':mark_safe(json.dumps(trimmomatic_result)),
                         'busco_contig_n':busco_contig_n,
                         'busco_contig_single':busco_contig_single,
                         'busco_contig_duplicate':busco_contig_duplicate,
                         'busco_contig_result':mark_safe(json.dumps(busco_contig_result)),
                         'bowtie_total_reads':bowtie_total_reads,
                         'bowtie_result_table':bowtie_result,
                         'bowtie_result':mark_safe(json.dumps(bowtie_result)),
                         'alignment_rate':alignment_rate,
                         'cdna_path':cdna_path,
                         'protein_path':protein_path,
                         'gff_path':gff_path,
                         'gene_pred_table':gene_pred_table,
                         'predicted_tool':predicted_tool,
                         'busco_pred_n':busco_pred_n,
                         'busco_pred_single':busco_pred_single,
                         'busco_pred_duplicate':busco_pred_duplicate,
                         'busco_pred_result':mark_safe(json.dumps(busco_pred_result)),
                         'species_table':species_table,
                         'coverage':coverage,
                         'coverage_perc':coverage_perc,
                         'blast_table':blast_table,
                         'kegg_output':kegg_output,
                         'go_output':go_output,
                         'big_flag':big_flag,
                         'goslim_output':goslim_output,
                         'go_plot':go_plot,
                         }
        with open(data_path+'/output_dict', 'wb') as fp:
            pickle.dump(output_dictionary, fp)
        
        #overview parser
        user_root=data_path.split('/')[1]
        uid=data_path.split('/')[2]
        p=sp.run("cd /"+user_root+";tar zcvf "+
        uid+".tar.gz --exclude=raw --exclude=reference --exclude=.snakemake "+
        "--exclude=snake_based_paths --exclude=long_aug --exclude=aug_interpro --exclude=long_before_ref --exclude=long_gm --exclude=gm_interpro "+
        "--exclude=long_QC --exclude=long_remap --exclude=snake_tree --exclude=tree/orthomcl/orthomcl.config --exclude=output_dict "+
        "--exclude=GO.tar.gz --exclude=blast.tar.gz "+
        uid+";mv "+uid+".tar.gz "+data_path+"/myjob.tar.gz",shell=True)

        
        #make softlink to static and assets
        
        tmp_path=str(Path('../').resolve().joinpath('src','assets'))
        p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
        tmp_path=str(Path('../').resolve().joinpath('src','static'))
        p=sp.run('ln -s '+data_path+'/ '+tmp_path+'/',shell=True)
        
    except:
        print(sys.exc_info())
        return -1
    
    return 0
    
    
def run_long_read_pipeline(sfile_path, data_path, aug_flag, param):    
    try:
        uid=data_path.split('/')[-1]
        user=long_User_Job.objects.filter(user_id=uid)[0]
        user.total_status="RUNNING"
        user.start_time=datetime.datetime.now()
        user.save(update_fields=['total_status','start_time'])
        
        if(user.remap_status!="SKIPPED"):
            HYBRID=1
        else:
            HYBRID=0
        
        if(user.tree_status!="SKIPPED"):
            TREE=1
        else:
            TREE=0
        
        if not path.exists(data_path):
            makedirs(data_path)
        
        # get lists of tools and databases that are conducted in this task
        if HYBRID:
            selected_col_name = 'hybrid'
        else:
            selected_col_name = 'long'
        
        if aug_flag:
            selected_col_name += '_aug'
        else:
            selected_col_name += '_gm'
        
        if TREE: selected_col_name += '_tree'
        
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
        
        data_tmp_path = str(Path(UPLOAD_BASE_PATH).resolve().joinpath(param['upload_id']))
        data_preparation_stat = run_data_preparation(data_tmp_path, data_path, param['dict_urls'])
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
        copy_snake(sfile_path+"/long_QC",data_path+"/long_QC",data_path,param['qc'])
        
        qc_status=run_QC(data_path, int(param['qc']['HYBRID']))
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
        
        #start Unicycler for de novo assembly
        user.assembly_status="RUNNING"
        user.save(update_fields=['assembly_status'])
        
        copy_snake(sfile_path+"/long_before_ref",data_path+"/long_before_ref",data_path,param['de_novo'])
        assembly_status=run_assembly(data_path)
        if(assembly_status!=0):
            print("pipeline stop at Unicycler!!!!!")
            failed_tar_result(data_path)
            user.error_log="ASSEMBLY"
            user.assembly_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','assembly_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.assembly_status="SUCCESSFUL"
            user.save(update_fields=['assembly_status'])
        
        #start Bowtie2 for short-read re-mapping
        if param['remap']['HYBRID'] == '1':
            user.remap_status="RUNNING"
            user.save(update_fields=['remap_status'])
            
            copy_snake(sfile_path+"/long_remap",data_path+"/long_remap",data_path,param['remap'])
            remap_status=run_remap(data_path)
            if(remap_status!=0):
                print("pipeline stop at Bowtie2!!!!!")
                failed_tar_result(data_path)
                user.error_log="REMAP"
                user.remap_status="FAILED"
                user.total_status="FAILED"
                user.end_time=datetime.datetime.now()
                user.save(update_fields=['error_log','remap_status','total_status','end_time'])
                failed_email(data_path)
                return -1
            else:
                user.remap_status="SUCCESSFUL"
                user.save(update_fields=['remap_status'])
        
        #1:run augustus, 0: run genemark
        user.gene_prediction_status="RUNNING"
        user.save(update_fields=['gene_prediction_status'])
        if(aug_flag):
            aug_param=dict(list(param['gene_prediction'].items()) + list(param['gene_assm'].items()))
            copy_snake(sfile_path+"/long_aug",data_path+"/long_aug",data_path,aug_param)
            gene_prediction_status=run_aug(data_path)
        else:
            copy_snake(sfile_path+"/long_gm",data_path+"/long_gm",data_path,param['gene_assm'])
            gene_prediction_status=run_gm(data_path)
        
        if(gene_prediction_status!=0):
            print("pipeline stop at Prediction!!!!!")
            if(aug_flag):
                user.error_log="AUG"
            else:
                user.error_log="GM"
            failed_tar_result(data_path)    
            user.gene_prediction_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','gene_prediction_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.gene_prediction_status="SUCCESSFUL"
            user.save(update_fields=['gene_prediction_status'])
        
        #run interproscan for GO term
        user.go_status="RUNNING"
        user.save(update_fields=['go_status'])
        if(aug_flag):
            copy_snake(sfile_path+"/aug_interpro",data_path+"/aug_interpro",data_path,param['go'])
        else:
            copy_snake(sfile_path+"/gm_interpro",data_path+"/gm_interpro",data_path,param['go'])
        
        go_stat=run_interpro(data_path,aug_flag)
        if(go_stat!=0):
            print("pipeline stop at GO term!!!!!")
            failed_tar_result(data_path)            
            user.error_log="GO"
            user.go_status="FAILED"
            user.total_status="FAILED"
            user.end_time=datetime.datetime.now()
            user.save(update_fields=['error_log','go_status','total_status','end_time'])
            failed_email(data_path)
            return -1
        else:
            user.go_status="SUCCESSFUL"
            user.save(update_fields=['go_status'])
        
        if(param['tree']['yesno']=="yes"):
            user.tree_status="RUNNING"
            user.save(update_fields=['tree_status'])
            tree_stat=run_tree(data_path,param['tree']['species'],aug_flag,param['tree']['name'])
            if(tree_stat!=0):
                print("pipeline stop at Tree!!!!!")
                failed_tar_result(data_path)
                user.error_log="TREE"
                user.tree_status="FAILED"
                user.total_status="FAILED"
                user.end_time=datetime.datetime.now()
                user.save(update_fields=['error_log','tree_status','total_status','end_time'])
                failed_email(data_path)
                return -1
            else:
                user.tree_status="SUCCESSFUL"
                user.save(update_fields=['tree_status'])
        
        #run parser
        user.parsing_status="RUNNING"
        user.save(update_fields=['parsing_status'])
        
        parser_stat=run_parser(data_path, HYBRID, TREE)
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
        if HYBRID:
            print("Hybrid assembly successful!!!!!!!!!")
        else:
            print("Long-read assembly successful!!!!!!!!!")
    except:
        print(sys.exc_info())
        user.total_status="FAILED"
        user.error_log="SYSTEM"
        user.end_time=datetime.datetime.now()
        user.save(update_fields=['error_log','total_status','end_time'])
        #due to system error: do not tar the result
        failed_email(data_path)
        if HYBRID:
            print("Hybrid assembly failed....")
        else:
            print("Long-read assembly failed....")
        
        return -1
    
    #send mail for successful task TODO:change fail_silently=True     
    mail=user.mail
    send_mail('Task Successfully Completed!', 'Your Link:'+web_url+"/long_read/"+uid+"/report", None,
    [mail], fail_silently=True)
    
    return 0
