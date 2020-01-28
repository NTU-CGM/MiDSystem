#!/usr/bin/env python
"""
Parsing GO Accession from a table file produced by InterProScan and mapping to GOSlim.
(c) Chien-Yueh Lee 2018 / MIT Licence
kinomoto[AT]sakura[DOT]idv[DOT]tw
"""

from __future__ import print_function
from os import path
import sys
import pandas as pd
from goatools.obo_parser import GODag
from goatools.mapslim import mapslim
from joblib import Parallel, delayed




import optparse
p = optparse.OptionParser("%prog [options] <eggnog_diamond_file> <go_obo_file>")
p.add_option("-o", "--out", dest="output_filename", help="Directory to store " "the output file [default: GO_term_annotation.txt]", action="store", type="string", default="GO_term_annotation.txt")
p.add_option("-g", "--goslim", dest="goslim_obo_file", action="store",
             help="The .obo file for the most current GO Slim terms "
             "[default: Null]", type="string", default=None)
p.add_option("-O", "--goslim_out", dest="goslim_output_filename", action="store", help="Directory to store the output file [default: " "GOSlim_annotation.txt]", type="string", default="GOSlim_annotation.txt")
p.add_option("-t", "--goslim_type", dest="goslim_type", action="store", type="string", default="direct", help="One of `direct` or `all`. Defines "
             "whether the output should contain all GOSlim terms (all "
             "ancestors) or only direct GOSlim terms (only direct "
             "ancestors) [default: direct]")
p.add_option("-s", "--sort", dest="is_sort", action="store_true", default=False, help="Sort the output table [default: False]")
opts, args = p.parse_args()

# check for correct number of arguments
if len(args) != 2:
    p.print_help()
    sys.exit(1)

interpro_file = args[0]
assert path.exists(interpro_file), "file %s not found!" % interpro_file

obo_file = args[1]
assert path.exists(obo_file), "file %s not found!" % obo_file

# check that --goslim is set
USE_SLIM = False
if (opts.goslim_obo_file is not None):
    assert path.exists(opts.goslim_obo_file), "file %s not found!" % opts.goslim_obo_file
    USE_SLIM = True

# check that slim_out is either "direct" or "all" and set according flag
if opts.goslim_type.lower() == "direct":
    ONLY_DIRECT = True
elif opts.goslim_type.lower() == "all":
    ONLY_DIRECT = False
else:
    p.print_help()
    sys.exit(1)

# load InterProScan_tsv_file 
interpro_table = pd.read_csv(interpro_file, sep='\t',skiprows=3,skipfooter=3,engine='python')

#interpro_go = interpro_table[['#query_name', 'GO_terms']]
all_protein=list(interpro_table['#query_name'])
gos=list(interpro_table['GO_terms'])
# load obo files
go = GODag(obo_file, load_obsolete=True)
output_hd = ['Protein Accession', 'GO Category', 'GO Accession', 'GO Description', 'GO Level']
output_table = pd.DataFrame(columns=output_hd)

def tmp_func(pro):
    all_go_accs_in_a_protein = set()
    go_accs = gos[pro]
    output_hd = ['Protein Accession', 'GO Category', 'GO Accession', 'GO Description', 'GO Level']
    output_table = pd.DataFrame(columns=output_hd)
    if not pd.isnull(go_accs):
        all_go_accs_in_a_protein = go_accs.split(',')
    #print(pro)
    if len(all_go_accs_in_a_protein) > 0:
        for go_term in all_go_accs_in_a_protein:
            if go_term not in go:
                continue
                
            query_term = go.query_term(go_term)
            output_table = output_table.append(pd.DataFrame({'Protein Accession': [all_protein[pro]], 'GO Category': [query_term.namespace], 'GO Accession': [go_term], 'GO Description': [query_term.name], 'GO Level':[query_term.level]}), ignore_index=True)
    return(output_table)
#len(all_protein)
# start to annotate
results=Parallel(n_jobs=15)(delayed(tmp_func)(pro) for pro in range(len(all_protein)))
output_hd = ['Protein Accession', 'GO Category', 'GO Accession', 'GO Description', 'GO Level']
output_table = pd.DataFrame(columns=output_hd)
output_table=output_table.append(pd.concat(results))
    
# write the output
if opts.is_sort:
    output_table[output_hd].sort_values(by=['Protein Accession', 'GO Category', 'GO Level']).to_csv(opts.output_filename, sep="\t", index=False)
    if USE_SLIM:
        output_slim_table[output_slim_hd].sort_values(by=['Protein Accession', 'GO Category', 'GOSlim Level']).to_csv(opts.goslim_output_filename, sep="\t", index=False)
else:
    output_table[output_hd].to_csv(opts.output_filename, sep="\t", index=False)
    if USE_SLIM:
        output_slim_table[output_slim_hd].to_csv(opts.goslim_output_filename, sep="\t", index=False)