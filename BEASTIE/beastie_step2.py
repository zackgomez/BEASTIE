#!/usr/bin/env python
#=========================================================================
# 2021 Xue Zou (xue.zou@duke.edu)
#=========================================================================
import sys
import os
import logging

from prepare_model import (
    update_model_input_lambda_phasing,
    significant_genes,
    generate_modelCount,
)
from beastie_step1 import create_output_directory
import run_model_stan_wrapper

def create_file_name(hetSNP_intersect_unique,meta,out,tmp):
    base = os.path.split(hetSNP_intersect_unique)
    base_modelin = os.path.join(tmp,'{0}_modelinput.tsv'.format(os.path.splitext(base[1])[0]))
    base_modelin_error = os.path.join(out,'{0}_modelinput_w_error.tsv'.format(os.path.splitext(base[1])[0]))
    base_meta = os.path.split(meta)
    meta_error = os.path.join(out,'{0}_w_error.tsv'.format(os.path.splitext(base_meta[1])[0]))
    return base_modelin, base_modelin_error,meta_error

def run(hetSNP_intersect_unique,meta,hetSNP_intersect_unique_forlambda_file,hetSNP_intersect_unique_lambdaPredicted_file,prefix,alpha,model,sigma,in_path,out,cutoff,SAVE_INT):
    out,tmp = create_output_directory(in_path,out)
    base_modelin, base_modelin_error,meta_error = create_file_name(hetSNP_intersect_unique,meta,out,tmp)

    logging.info('>>>>>>>>>>')
    logging.info('>>>>>>>>>> Starting step 2.1 : convert data in format for model input')
    generate_modelCount(hetSNP_intersect_unique)

    logging.info('>>>>>>>>>>')
    logging.info('>>>>>>>>>> Starting step 2.2 : predict phasing error')
    cmd="Rscript --vanilla predict_lambda_phasingError.R %s %s %s %s %s %s %s %s %s"%(
        alpha,tmp,prefix,model,hetSNP_intersect_unique,hetSNP_intersect_unique_forlambda_file,hetSNP_intersect_unique_lambdaPredicted_file,meta,meta_error
    )
    os.system(cmd)
    logging.info('.... output file save to {0}'.format(hetSNP_intersect_unique_lambdaPredicted_file))

    logging.info('>>>>>>>>>>')
    logging.info('>>>>>>>>>> Starting step 2.3 : update model input with phasing')
    # print(base_modelin)
    update_model_input_lambda_phasing('pred_error_GIAB',base_modelin,base_modelin_error,meta_error)
    logging.info('.... output file save to {0}'.format(base_modelin_error))

    logging.info('>>>>>>>>>>')
    logging.info('>>>>>>>>>> Starting step 2.4 : run model')
    # add debug msg
    out_path,outname1,outname2 = run_model_stan_wrapper.run(base_modelin_error,sigma,alpha,model,out,hetSNP_intersect_unique_lambdaPredicted_file)

    logging.info('>>>>>>>>>>')
    logging.info('>>>>>>>>>> Starting step 2.5 : generate gene list')
    # add debug msg
    significant_genes(prefix,out,out_path,outname1,outname2,cutoff,hetSNP_intersect_unique_lambdaPredicted_file)

    if SAVE_INT == True:
        os.rmdir(tmp)
