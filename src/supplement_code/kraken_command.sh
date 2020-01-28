kraken --fastq-input --classified-out classified.fa --threads 15 --db ${KRAKEN_DB} --paired R1.fastq R2.fastq 1> /dev/null 2> kraken.summary;
grep -P '^>' classified.fa | sed -r 's/^>(.+)$/\1 /' > exclused_seq_id.txt;
awk '{if(NR%4==1 && match($0, /^@[^ ]+\/[12]$/)) {split($0,a,"/"); $0=a[1]" "substr(a[1],2)"/"a[2];} else if(NR%4==3) {$0="+";} print $0;}' R1.fastq | paste - - - - | grep -v -f exclused_seq_id.txt | tr '\t' '\n' > ../raw/R1.fastq;
awk '{if(NR%4==1 && match($0, /^@[^ ]+\/[12]$/)) {split($0,a,"/"); $0=a[1]" "substr(a[1],2)"/"a[2];} else if(NR%4==3) {$0="+";} print $0;}' R2.fastq | paste - - - - | grep -v -f exclused_seq_id.txt | tr '\t' '\n' > ../raw/R2.fastq;
