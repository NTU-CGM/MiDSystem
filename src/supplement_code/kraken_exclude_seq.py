import argparse
import sys
from os import path, makedirs
import gzip

if __name__ == "__main__":
    usage = "%(prog)s <-c classified.fa -I raw_R1.fastq(.gz) -O filtered_R1.fastq(.gz)> [-i raw_R2.fastq(.gz) -o filtered_R2.fastq(.gz)]"
    parser = argparse.ArgumentParser(usage=usage, description='Take classified.fa created by Kraken with the --classified-out option to filter out reads.')
    parser.add_argument('-c', '--classified', required=True, action='store', default=None, help='Path of classified.fa created by Kraken. This is required. [Default: None]')
    parser.add_argument('-I', '--input_R1', required=True, action='store', default=None, help='Path of raw R1. [Default: None]')
    parser.add_argument('-i', '--input_R2', action='store', default=None, help='Path of raw R2. [Default: None]')
    parser.add_argument('-O', '--output_R1', required=True, action='store', default=None, help='Path of filtered R1. This is required. [Default: None]')
    parser.add_argument('-o', '--output_R2', action='store', default=None, help='Path of filtered R2. [Default: None]')
    
    ## Show help without providing any options
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    pargs = parser.parse_args()
    
    ## Check input_R2 & output_R2
    if (pargs.input_R2 is not None) and (pargs.output_R2 is None):
        sys.exit("The -o/--output_R2 option should be given.\n")
    if (pargs.input_R2 is None) and (pargs.output_R2 is not None):
        sys.exit("The -i/--input_R2 option should be given.\n")
    
    ## Read classified.fa
    exclused_seq_id_dict = {}
    with open(pargs.classified, 'r') as fp:
        for line in fp:
            if line.startswith('>'):
                line = line.strip()
                exclused_seq_id_dict[line[1:]] = 1
    
    ## Process input_R1 & output_R1
    if path.splitext(path.basename(pargs.input_R1))[1] == '.gz':
        raw_R1_fp = gzip.open(pargs.input_R1, 'rt')
    else:
        raw_R1_fp = open(pargs.input_R1, 'r')
    
    output_R1_dir = '/'.join(pargs.output_R1.split('/')[:-1])
    if not path.exists(output_R1_dir):
        makedirs(output_R1_dir)
    if path.splitext(path.basename(pargs.output_R1))[1] == '.gz':
        filtered_R1_fp = gzip.open(pargs.output_R1, 'wt')
    else:
        filtered_R1_fp = open(pargs.output_R1, 'w')
    
    input_output_fp_pair = [(raw_R1_fp, filtered_R1_fp)]
    
    ## Process input_R2 & output_R2
    if (pargs.input_R2 is not None):
        if path.splitext(path.basename(pargs.input_R2))[1] == '.gz':
            raw_R2_fp = gzip.open(pargs.input_R2, 'rt')
        else:
            raw_R2_fp = open(pargs.input_R2, 'r')
        
        output_R2_dir = '/'.join(pargs.output_R2.split('/')[:-1])
        if not path.exists(output_R2_dir):
            makedirs(output_R2_dir)
        if path.splitext(path.basename(pargs.output_R2))[1] == '.gz':
            filtered_R2_fp = gzip.open(pargs.output_R2, 'wt')
        else:
            filtered_R2_fp = open(pargs.output_R2, 'w')
        
        input_output_fp_pair.append((raw_R2_fp, filtered_R2_fp))
    
    for raw_fp, filtered_fp in input_output_fp_pair:
        line_counter = 0
        skip_line = False
        for line in raw_fp:
            line_counter += 1
            if line_counter%4 == 1:
                try:
                    exclused_seq_id_dict[line[1:].split(' ')[0]]
                    skip_line = True
                except:
                    skip_line = False
            
            if not skip_line:
                filtered_fp.write(line)
        
        raw_fp.close()
        filtered_fp.close()