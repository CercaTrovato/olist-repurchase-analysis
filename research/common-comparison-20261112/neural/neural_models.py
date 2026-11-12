"""Frozen mean/column-gate/AE models, matching the preceding representation experiment."""
import hashlib
import random
import time
import numpy as np
import torch
from torch import nn

def seed_all(value):
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)

class Model(nn.Module):
    def __init__(self,dims,kind='mean',decoder=False):
        super().__init__()
        if kind not in ['mean','column-gate','AE']: raise ValueError(kind)
        self.dims=list(dims)
        self.kind=kind
        self.enc=nn.ModuleList([nn.Linear(d,16) for d in dims])
        self.head=nn.Linear(16,1)
        if kind=='column-gate':
            self.gate_a=nn.Parameter(torch.zeros(sum(dims)))
            self.gate_b=nn.Parameter(torch.zeros(sum(dims)))
        self.dec=nn.ModuleList([nn.Linear(16,d) for d in dims]) if decoder else None

    def encode(self,x,return_views=False):
        if self.kind=='column-gate': x=x*torch.sigmoid(self.gate_a*x+self.gate_b)
        views=torch.stack([torch.relu(layer(part)) for layer,part in zip(self.enc,torch.split(x,self.dims,dim=1))],dim=1)
        weights=torch.full((len(x),len(self.dims)),1/len(self.dims),device=x.device)
        latent=(views*weights.unsqueeze(-1)).sum(1)
        return (latent,views,weights) if return_views else latent

    def forward(self,x): return self.head(self.encode(x)).squeeze(1)

def shared_initialization_hash(model):
    digest=hashlib.sha256()
    for name,value in model.state_dict().items():
        if name.startswith(('enc.','head.')):
            digest.update(name.encode('ascii'))
            digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()

def infer(model,x,batch=2048):
    model.eval()
    with torch.no_grad():
        result=torch.cat([model(chunk) for chunk in x.split(batch)]).cpu().numpy().astype(np.float64)
    if not np.isfinite(result).all(): raise FloatingPointError('Nonfinite model logits')
    return result

def supervised(model,x,y,epochs=50,seed=2026):
    model.train()
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=.001)
    generator=torch.Generator().manual_seed(seed)
    history=[]
    order_hash=hashlib.sha256()
    started=time.perf_counter()
    for epoch in range(epochs):
        total=0.
        order=torch.randperm(len(x),generator=generator)
        order_hash.update(order.numpy().tobytes())
        for indices in order.split(512):
            optimizer.zero_grad(set_to_none=True)
            logits=model(x[indices])
            loss=nn.functional.binary_cross_entropy_with_logits(logits,y[indices])
            if not torch.isfinite(loss): raise FloatingPointError('Nonfinite supervised BCE')
            loss.backward()
            optimizer.step()
            total+=float(loss.detach())*len(indices)
        history.append(dict(epoch=epoch+1,online_mean_BCE=total/len(x),updates=int(np.ceil(len(x)/512)),clients=len(x)))
    return history,time.perf_counter()-started,order_hash.hexdigest()

def reconstruction_loss(model,q):
    _,views,_=model.encode(q,True)
    target=torch.split(q,model.dims,dim=1)
    return sum(nn.functional.mse_loss(dec(views[:,i]),part) for i,(dec,part) in enumerate(zip(model.dec,target)))/len(model.dims)

def final_reconstruction(model,x):
    model.eval()
    total=0.
    with torch.no_grad():
        for q in x.split(256): total+=float(reconstruction_loss(model,q))*len(q)
    return total/len(x)

def pretrain_AE(model,x,epochs=20,seed=2026):
    generator=torch.Generator().manual_seed(seed+901)
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    history=[]
    order_hash=hashlib.sha256()
    initial=final_reconstruction(model,x)
    started=time.perf_counter()
    for epoch in range(epochs):
        model.train()
        total=0.
        order=torch.randperm(len(x),generator=generator)
        order_hash.update(order.numpy().tobytes())
        for indices in order.split(256):
            q=x[indices]
            optimizer.zero_grad(set_to_none=True)
            loss=reconstruction_loss(model,q)
            if not torch.isfinite(loss): raise FloatingPointError('Nonfinite AE reconstruction MSE')
            loss.backward()
            optimizer.step()
            total+=float(loss.detach())*len(indices)
        history.append(dict(epoch=epoch+1,online_view_mean_MSE=total/len(x),updates=int(np.ceil(len(x)/256)),clients=len(x)))
    seconds=time.perf_counter()-started
    final=final_reconstruction(model,x)
    return history,seconds,order_hash.hexdigest(),initial,final
