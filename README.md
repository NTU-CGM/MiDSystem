# miDSystem
MiDSystem is a comprehensive online system for de novo assembly and analysis of microbial genomes. It supports both __whole genome assembly__ and __metagenomics analysis__ pipelines in shotgun sequencing data.
## License
MiDSystem is available for academic and nonprofit use for free ([MIT license](LICENSE.md))  
## Hardware Requirements
A multi-core server with at least 128GB RAM is recommended when running the entire pipelines. A typical run for the *de novo* genome assembly of single species will generate about 25 GB of result data.
## Quick Install
1. Create a user accout and clone the code
    1.1. Create a user accout for MiDSystem (e.g., midsystem)  
    1.2. `cd ; git clone https://github.com/NTU-CGM/miDSystem.git`  
2. Install miniconda and add channels  
    2.1. `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh`  
    2.2. `bash Miniconda3-latest-Linux-x86_64.sh`  
    2.3. `conda config --add channels bioconda`  
    2.4. `conda config --add channels conda-forge`  
    2.5. `conda config --add channels r`  
3. Install conda packages (Add marks in any package which is reported conflict.)  
    3.1. `cd bac_denovo`  
    3.2. `conda create -n ngs --file conda_ngs_requirements.txt`  
    3.3. `conda create -n ngs_p2 --file conda_ngs_p2_requirements.txt`  
4. Install MySQL  
    4.1. `sudo yum install mariadb mariadb-devel mariadb-libs mariadb-server cmake` (optional: phpMyAdmin httpd httpd-tools httpd-manual)  
    4.2. `sudo systemctl enable mariadb.service`  
    4.3. `sudo systemctl start mariadb.service`  
    4.4. Setup mariadb configure file  
        4.4.1. `sudo vi /etc/my.cnf`  
        4.4.2. wait_timeout=604800  
        4.4.3. interactive_timeout=604800  
        4.4.4. max_allowed_packet=100M  
    4.5. `sudo mysqladmin -u root password 'YOUR_PASSWORD'` (optional)  
    4.6. Setup PHP configure file  
        4.6.1. `sudo vi /etc/php.ini`  
        4.6.2. L211: short_open_tag = On  
        4.6.3. L384: max_execution_time = 0  
        4.6.4. L394: max_input_time = -1  
        4.6.5. L405: memory_limit = 64G  
        4.6.6. L800: upload_max_filesize = 10G  
    4.7. Set allowed IPs in `/etc/httpd/conf.d/phpMyAdmin.conf` (optional)  
    4.8. `sudo systemctl start httpd.service` (optional)  
    4.9. Import pipeline_bac_species.sql into the database  
5. Install pip packages in ngs and ngs_p2 environments (Add marks in any package which is reported conflict.)  
    5.1. `source activate ngs_p2`  
    5.2. `pip install -r pip_ngs_p2_requirements.txt`  
    5.3. `source deactivate ngs_p2; source activate ngs`  
    5.4. `pip install -r pip_ngs_requirements.txt`  
6. Install dependency  
    6.1. Install other required tools as follows in `/usr/local/NGSTools`  
    EVidenceModeler-1.1.1, interproscan-5.25-64.0, eggnog-mapper, genemark_suite_linux_64, MetaGeneMark_linux_64, Ragout, orthomclSoftware-v2.0.9, GraphlAn, Gblocks_Linux64_0.91b   
    6.2. Run `/usr/local/NGSTools/Ragout/scripts/install-sibelia.py` and install Sibelia in `/usr/local/bin`  
7. Create /data and put required datasets here  
    7.1. `mkdir /data`  
    7.2. Download and uncompress datasets:  bacteria_db, busco_reference, cDNA, kraken_db_hsa_mmu_rno, pfam_31, blast_nr_db  
    7.3. cp -aR bacteria_db busco_reference cDNA kraken_db_hsa_mmu_rno pfam_31 nr /data  
    7.4. Combine partial files and decompress `Bacteria_RefSeq.gi.gz` in `src/supplement_code`  
        7.4.1. `cat Bacteria_RefSeq.gi.gz.part.* >  Bacteria_RefSeq.gi.gz`  
        7.4.2. `gzup -d Bacteria_RefSeq.gi.gz`  
8. Make tables and users in a database  
    8.1. `mysql -h localhost -u root -p`  
    8.2. CREATE DATABASE `djangodb`;  
    8.3. CREATE USER '[USER_ID]'@'localhost' IDENTIFIED BY '[PASSWORD]';  
    8.4. GRANT ALL PRIVILEGES ON `djangodb`.* TO '[USER_ID]'@'localhost';  
    8.5. GRANT ALL ON *.* TO 'orthomcl'@'localhost' IDENTIFIED BY 'orthoMCL' WITH GRANT OPTION;  
    8.6. `cd ~/bac_denovo/src; source activate ngs; python manage.py migrate`  
9. Run development server  
    9.1. `nohup python manage.py runserver 172.16.0.176:8000 > nohup_ruserver.out &`  
    9.2. `nohup python manage.py qcluster > nohup_qcluster.out &`  
10. Deploy a production server (Optional)  
    10.1. Install Nginx  
        10.1.1. `sudo yum install nginx`  
        10.1.2. Tmpfiles.d configuration  
        10.1.3. `sudo echo 'd /run/MiDSystem 0775 midsystem nginx' > /etc/tmpfiles.d/MiDSystem.conf`  
        10.1.4. Reboot and see if the folder /run/MiDSystem exists  
        10.1.5. Create a new configuration file in /etc/nginx/conf.d/MiDSystem.conf with following contents (root permission required):  
        
```
# Upstream Django setting; the socket nginx connects to
upstream MiDSystem-django {
    server unix:///run/MiDSystem/django.sock;
}

server {
    listen      8000;
    # listen      443 default ssl;

    server_name midsystem.cgm.ntu.edu.tw;
    charset     utf-8;

    client_max_body_size 20G;  # max upload size
    keepalive_timeout 1440;

    location /static {
        alias /home/midsystem/bac_denovo/src/assets;
    }
    
    location  /robots.txt {
        alias  /home/midsystem/bac_denovo/src/assets/robots.txt;
    }

    # Finally, send all non-media requests to the Django server.
    location / {
        uwsgi_pass  MiDSystem-django;
        uwsgi_read_timeout 1200;
        include     /etc/nginx/uwsgi_params;
    }
}
```

        10.1.6. `sudo systemctl enable nginx.service; sudo systemctl start nginx.service`  

    10.2. Install uWSGI module  
        10.2.1. `pip install uwsgi` (under the ngs virtualenv)  
        10.2.2. `sudo mkdir /etc/uwsgi`  
        10.2.3. Create the uWSGI setting file in /etc/uwsgi/MiDSystem.ini with following contents (root permission required):  

```
[uwsgi]
chdir        = /home/midsystem/bac_denovo/src
# Django's wsgi file
module       = bac_denovo.wsgi:application
env          = DJANGO_SETTINGS_MODULE=bac_denovo.settings.production
# the virtualenv (full path)
virtualenv   = /home/midsystem/miniconda3/envs/ngs

# process-related settings
# master
master       = true
# maximum number of worker processes
processes    = 2
# the socket (use the full path to be safe
socket       = /run/MiDSystem/django.sock
# ... with appropriate permissions - may be needed
chmod-socket = 664
uid          = midsystem
gid          = nginx
# clear environment on exit
vacuum       = true
```

    10.3. Django settings  
        10.3.1. Add Django settings module while sourcing the environment  
        10.3.2. `echo 'export DJANGO_SETTINGS_MODULE="bac_denovo.settings.production"' > ~/miniconda3/envs/ngs/etc/conda/activate.d/django_env_var.sh`  
        10.3.3. `echo 'unset DJANGO_SETTINGS_MODULE' > ~/miniconda3/envs/ngs/etc/conda/deactivate.d/django_env_var.sh`  
        10.3.4. Create a Django superuser  
        10.3.5. `cd ~/bac_denovo/src; python manage.py createsuperuser`  

    10.4. Make MiDSystem as a systemd service  
        10.4.1. Under `/usr/lib/systemd/system` create `MiDSystem.service` with following contains (root permission required):  

```
[Unit]
Description=MiDSystem uWSGI (Django)
After=syslog.target
Wants=nginx.service

[Service]
Environment="PATH=/home/midsystem/miniconda3/envs/ngs/bin:$PATH"
ExecStart=/home/midsystem/miniconda3/envs/ngs/bin/uwsgi --ini /etc/uwsgi/MiDSystem.ini
RuntimeDirectory=MiDSystem
Restart=always
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all

[Install]
WantedBy=multi-user.target
```

        10.4.2. `sudo systemctl enable MiDSystem.service; sudo systemctl start MiDSystem.service`  
