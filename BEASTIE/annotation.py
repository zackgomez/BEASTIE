#!/usr/bin/env python
#=========================================================================
# 2021 Xue Zou (xue.zou@duke.edu)
#=========================================================================
import os
import subprocess
import pandas as pd
import logging

def annotateAF(ancestry,hetSNP,out_AF,ref_dir):
    AF_file = os.path.join(ref_dir,"AF_1_22_trimmed2.csv")
    if not os.path.isfile(out_AF):
        logging.info('..... start reading 1000 Genome AF annotation file')
        AF=pd.read_csv(AF_file, header=0, sep=',', engine='c', na_filter=False)
        logging.info('..... finish reading 1000 Genome AF annotation file')
        data=pd.read_csv(hetSNP,sep="\t",header=0,index_col=False)
        if ancestry == "EUR":
            AF=AF[['chr','pos','rsid','EUR_AF']]
            AF=AF.rename(columns={'EUR_AF': 'AF'})
        elif ancestry == "AFR":
            AF=AF[['chr','pos','rsid','AFR_AF']]
            AF=AF.rename(columns={'AFR_AF': 'AF'})
        elif ancestry == "EAS":
            AF=AF[['chr','pos','rsid','EAS_AF']]  
            AF=AF.rename(columns={'EAS_AF': 'AF'})
        elif ancestry == "AMR":
            AF=AF[['chr','pos','rsid','AMR_AF']]
            AF=AF.rename(columns={'AMR_AF': 'AF'})  
        elif ancestry == "SAS":
            AF=AF[['chr','pos','rsid','SAS_AF']]  
            AF=AF.rename(columns={'SAS_AF': 'AF'})
        data_AF=pd.merge(data,AF,on=['chr','pos'],how='left')
        data_AF=data_AF.drop_duplicates()
        data_AF.to_csv(out_AF,sep='\t')
        logging.info('..... finish annotating AF for SNPs, file save at {0}'.format(out_AF))
    else:
        logging.info('..... skip annotating AF for SNPs, file already saved at {0}'.format(out_AF)) 

def annotateLD(prefix,ancestry,hetSNP_intersect_unique,out,LD_token,chr_start,chr_end,meta,r_path):
    if not os.path.isfile(meta):
        cmdname = os.path.join(r_path, 'annotate_LD_new.r');
        cmd="Rscript --vanilla %s %s %s %s %s %s %d %d %s"%(cmdname, prefix,ancestry,hetSNP_intersect_unique,out,LD_token,int(chr_start),int(chr_end),meta)
        output_file = stdout=open(os.path.join(prefix, out, 'rlog.stdout'), 'w')
        subprocess.call(cmd, shell=True, stdout=output_file, stderr=output_file)
        logging.info('..... finish annotating LD for SNP pairs, file save at {0}'.format(meta))
    else:
        logging.info('..... skip annotating LD for SNP pairs, file already saved at {0}'.format(meta))
