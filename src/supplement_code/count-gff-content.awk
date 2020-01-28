# awk -f count-gff-content.awk input.gff3
{
if($3=="gene") {gN+=1; gL+=($5-$4)} 
else if ($3=="mRNA") {mN+=1; mL+=($5-$4)}
else if ($3=="transcript") {mN+=1; mL+=($5-$4)}
else if ($3=="exon") {eN+=1; eL+=($5-$4)}
else if ($3=="CDS") {cN+=1; cL+=($5-$4)}
}

END {
gM=gL/gN;
mM=mL/mN;
eM=eL/eN;
cM=cL/mN; 
print "Gene:\t\t\t"gN",\tTotal gene length: "gL" bp,\tMean gene length: "gM" bp";
print "mRNA/transcript:\t"mN",\ttotal length: "mL" bp,\tmean length: "mM" bp";
print "exon:\t\t\t"eN",\ttotal length: "eL" bp,\tmean length: "eM" bp";
print " CDS:\t\t\t"cN",\ttotal length: "cL" bp,\tmean length: "cM" bp";
}
