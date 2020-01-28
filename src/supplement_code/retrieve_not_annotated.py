#cd cdhit
#less genecatalog|grep "gene" > predicted_gene.txt
#sed -r 's/\s+>scaffold_[0-9]+//' predicted_gene.txt > predicted_gene.modified.txt; 

import pandas as pd
df=pd.read_csv("../eggnog/result_diamond.emapper.annotations",skiprows=3,skipfooter=3,sep='\t',engine='python')
predicted=pd.read_csv('../cdhit/predicted_gene.modified.txt',names=['name'])
pred_gene=list(predicted['name'])
modi_pred_gene=[]
for i in pred_gene:
    modi_pred_gene.append(i[1:])
    
annotated=list(df['#query_name'])
pd.DataFrame(list(set(modi_pred_gene)-set(annotated))).to_csv('predicted_not_annoated.txt',header=False,index=False)

#seqtk subseq genecatalog predicted_not_annoated.txt > pred_not_annot_seq.fa
#hmmscan --cpu 30 -E 1E-5 --noali --domtblout pfam_result.txt /data/pfam_31/Pfam-A.hmm pred_not_annot_seq.fa 1> /dev/null 2> pfam.log
