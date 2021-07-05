# awk -f count-gff-content.awk input.gff3
BEGIN {FS="\t"}

{
if($3=="gene") {gN+=1; gL+=($5-$4)} 
else if ($3=="mRNA") {mN+=1; mL+=($5-$4)}
else if ($3=="transcript") {mN+=1; mL+=($5-$4)}
else if ($3=="exon") {eN+=1; eL+=($5-$4)}
else if ($3=="CDS") {cN+=1; cL+=($5-$4)}
}

END {
gN!=0 ? gM=gL/gN : gM=0;
mN!=0 ? mM=mL/mN : mM=0;
eN!=0 ? eM=eL/eN : eM=0;
mN!=0 ? cM=cL/mN : cM=0;
print "Gene:\t\t\t"gN",\tTotal gene length: "gL" bp,\tMean gene length: "gM" bp";
print "mRNA/transcript:\t"mN",\ttotal length: "mL" bp,\tmean length: "mM" bp";
print "exon:\t\t\t"eN",\ttotal length: "eL" bp,\tmean length: "eM" bp";
print " CDS:\t\t\t"cN",\ttotal length: "cL" bp,\tmean length: "cM" bp";
}
