import torch
import torchvision
from dataset import BinaryDataset
from torch.utils.data import DataLoader

from matplotlib.colors import LinearSegmentedColormap
import colorcet as cc
import matplotlib as mpl
import numpy as np
import torch as t
import matplotlib.pyplot as plt

def show_images(*img_list,binaries=[],titles=[],save_str=False,n_cols=3,axes=False,cmap="viridis",labels=[],dpi=None):
    """Designed to plot torch tensor and numpy arrays in windows robustly"""    
    if dpi:
        mpl.rcParams['figure.dpi'] = dpi    
        img_list = [img for img in img_list]
    if isinstance(img_list[0], list):
        img_list = img_list[0]
    rows=(len(img_list)-1)//n_cols+1    
    columns=np.min([n_cols,len(img_list)])
    fig = plt.figure(figsize=(5*(columns+1),5*(rows+1)))
    fig.tight_layout() 
    grid = plt.GridSpec(rows,columns,figure=fig)
    grid.update(wspace=0.2, hspace=0, left = None, right =None, bottom = None, top = None)
    for i,img in enumerate(img_list):
        if t.is_tensor(img):
            img=t.squeeze(img).detach().cpu().numpy()
        if len(img.shape)>2:
            img=np.moveaxis(img,np.argmin(img.shape),-1)
            if img.shape[-1]>3 or img.shape[-1]==2:
                show_images([img[...,i] for i in range(img.shape[-1])],binaries=binaries,titles=["Channel:"+str(i) for i in range(img.shape[-1])],save_str=save_str,n_cols=n_cols,axes=axes,cmap=cmap)
                continue        
        ax1 = plt.subplot(grid[i])
        if not axes:
            plt.axis('off')
        if i in binaries:
            im=ax1.imshow(img,vmin=0,vmax=1,cmap=cmap,interpolation='nearest')
        if i in labels:
            l=cc.cm.glasbey_bw_minc_20_minl_30_r.colors            
            l[0]=[0,0,0]
            cmap_lab = LinearSegmentedColormap.from_list('my_list', l, N=1000)
            im=ax1.imshow(img,cmap=cmap_lab,interpolation='nearest')
        else:
            im=ax1.imshow(img,cmap=cmap)
        plt.colorbar(im, ax=ax1,fraction=0.046, pad=0.04)
        if len(titles)==len(img_list):
            ax1.set_title(titles[i])
    if not save_str:
        plt.show()
    if save_str:
        plt.savefig(save_str+".png",bbox_inches='tight')
        plt.close()
        return None

def save_checkpoint(state, filename="my_checkpoint.pth.tar"):
    print("Saving checkpoint")
    torch.save(state, filename)

def load_checkpoint(checkpoint, model, optimizer):
    model.load_state_dict(checkpoint["state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    last_epoch = checkpoint['epoch']
    train_loss = checkpoint['train_loss'] 
    val_loss = checkpoint['val_loss']
    print("Loading checkpoint")
    return last_epoch, train_loss, val_loss


def get_loaders(
    train_dir,
    train_maskdir,
    val_dir,
    val_maskdir,
    batch_size,
    train_transform,
    val_transform,
    num_workers=4,
    pin_memory=True,
):
    train_ds = BinaryDataset(
        image_dir=train_dir,
        mask_dir=train_maskdir,
        transform=train_transform,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        shuffle=True,
    )

    val_ds = BinaryDataset(
        image_dir=val_dir,
        mask_dir=val_maskdir,
        transform=val_transform,
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        shuffle=False,
    )

    return train_loader, val_loader

import torch.nn as nn
loss_fn = nn.CrossEntropyLoss()

def evaluation_fn(x, y, model):
    preds = torch.sigmoid(model(x))
    preds = (preds > 0.5).float() # for binary, need to be adapted for multilabel
    intersection = (preds == y).sum()
    pixels_total = torch.numel(preds)
    accuracy = intersection/pixels_total*100
    dice_score = (2 * (preds * y).sum()) / ((preds + y).sum() + 1e-8) # for binary
    return accuracy, dice_score, preds


def check_accuracy(loader, model, device="cuda", show_results=False):
    model.eval()
    val_loss= []
    accuracy = []
    dice_score = []

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            prediction = model(x)
            y = y.type(torch.LongTensor).to(device)
            val_loss.append(loss_fn(prediction,y).item())
            
            # TODO adapt for multiclass
            # evaluation metrics
            #acc, ds, preds = evaluation_fn(x, y, model)
            #accuracy.append(acc)
            #dice_score.append(ds)


        print(f"Val loss: {sum(val_loss)/len(val_loss):.4f}")
        #print(f"Accuracy: {sum(accuracy)/len(accuracy):.2f} | Dice score: {sum(dice_score)/len(dice_score):.2f} | Val loss: {sum(val_loss)/len(val_loss):.4f}")
        if (show_results):
            #show_images(x[0:1],model(x[0:1]),y[0],titles=["Image","Prediction","Threshold","Ground Truth"],n_cols=3)
            show_images(x[0:1],model(x[0:1])[:,1], model(x[0:1])[:,2], model(x[0:1])[:,3], titles=["Image","Prediction C1", "Prediction C2", "Prediction C3"],n_cols=4)
            print(model(x[0:1]).shape)
    model.train()
    return sum(val_loss)/len(val_loss)
    

def save_predictions_as_imgs(
    loader, model, folder="saved_images/", device="cuda"
):
    model.eval()
    for idx, (x, y) in enumerate(loader):
        x = x.to(device=device)
        with torch.no_grad():
            preds = torch.sigmoid(model(x))
            preds = (preds > 0.5).float()
        torchvision.utils.save_image(
            preds, f"{folder}/pred_{idx}.png"
        )
        torchvision.utils.save_image(y.unsqueeze(1), f"{folder}{idx}.png")

    model.train()


