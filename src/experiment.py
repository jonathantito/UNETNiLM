from __future__ import print_function, division
import warnings
warnings.filterwarnings("ignore")
import os
import torch
import numpy as np
from net.model_pl import NILMnet
from net.utils import DictLogger
from pathlib import Path
import pytorch_lightning as pl
from net.utils import get_latest_checkpoint
from utils.utils import set_seed, get_device
import sys
from argparse import ArgumentParser
set_seed(seed=7777)
device =  get_device()


class NILMExperiment(object):

    def __init__(self, params):
        """
        Parameters to be specified for the model
        """
        self.MODEL_NAME = params.get('model_name',"CNNModel")
        self.logs_path =params.get('log_path',"../logs/")
        self.checkpoint_path =params.get('checkpoint_path',"../checkpoints/")
        self.results_path = params.get('results_path',"../results/")
        self.chunk_wise_training = params.get('chunk_wise_training',False)
        self.sequence_length = params.get('sequence_length',99)
        self.n_epochs = params.get('n_epochs', 10 )
        self.batch_size = params.get('batch_size',128)
        self.dropout = params.get('dropout', 0.1)
        self.params = params
        
        #create files
        logs = Path(self.logs_path )
        checkpoints = Path(self.checkpoint_path)
        results = Path(self.results_path)
        logs.mkdir(parents=True, exist_ok=True)
        checkpoints.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        results.mkdir(parents=True, exist_ok=True)
        
     

    def fit(self):
        file_name = f"{self.MODEL_NAME}_{self.params['exp_name']}"
        self.saved_model_path   = f"{self.checkpoint_path}/{file_name}_checkpoint.pt"
        self.arch = file_name
        checkpoint_callback = pl.callbacks.ModelCheckpoint(filepath=self.checkpoint_path, monitor='val_F1', mode="max", save_top_k=1)
        early_stopping = pl.callbacks.EarlyStopping(monitor='val_F1', min_delta=1e-4, patience=20, mode="max")
        logger = DictLogger(self.logs_path, name=self.MODEL_NAME, version=self.params['exp_name'])
        trainer = pl.Trainer(
                    logger = logger,
                    gradient_clip_val=self.params['clip_value'],
                    checkpoint_callback=checkpoint_callback,
                    max_epochs=self.params['n_epochs'],
                    gpus=-1 if torch.cuda.is_available() else None,
                    #early_stop_callback=early_stopping,
                    resume_from_checkpoint=get_latest_checkpoint(self.checkpoint_path)
                     )
        
        hparams = NILMnet.add_model_specific_args()
        
        hparams = vars(hparams.parse_args())
        hparams.update(self.params)
        model = NILMnet(hparams)
        print(f"fit model for { file_name}")
        trainer.fit(model)
        model = model.eval()
        results = trainer.test(model)
        if self.params['mc']:
            results_path = f"{self.results_path}{self.params['exp_name']}_uncertainity"
        else:
            results_path = f"{self.results_path}{self.params['exp_name']}"    
        np.save(results_path+"results.npy", results)
           
            


def run_experiments(model_name="CNN1D", denoise=True,
                     batch_size = 128, epochs = 100,
                    sequence_length =99, sample = None, 
                    dropout = 0.1, data = "ukdale", 
                    out_size = 5, quantiles=[0.5], n_model_samples=50, mc=False):        
    exp_name = f"{data}_{model_name}_quantiles" if len(quantiles)>1 else f"{data}_{model_name}"
    params = {'n_epochs':epochs,'batch_size':batch_size,
                'sequence_length':sequence_length,
                'model_name':model_name,
                'dropout':dropout,
                'exp_name':exp_name,
                'clip_value':10,
                'sample':sample,
                'n_model_samples':n_model_samples,
                'out_size':out_size,
                'data_path':"../data/",
                'data':data,
                'quantiles':quantiles,
                "denoise":denoise,
                "mc":mc,
                "checkpoint_path" :f"../checkpoints/{exp_name}"
                }
    exp = NILMExperiment(params)
    exp.fit()

if __name__ == "__main__": 
    for data in ["ukdale"]:
        for model_name in ["CNN1D"]:
            for mc in [False, True]:
                run_experiments(model_name=model_name, 
                                data = data, 
                                sample=None, 
                                epochs=50, 
                                mc=mc, quantiles=[0.5]) 
            #fit quantiles      
            run_experiments(model_name=model_name, 
                                data = data, 
                                sample=None, 
                                epochs=50, 
                                mc=None,
                                quantiles=[0.1, 0.5, 0.9])               
            
    
    
