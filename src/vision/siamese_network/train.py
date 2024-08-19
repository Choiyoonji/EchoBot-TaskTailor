import os
import argparse

import cv2
import numpy as np
from tqdm import tqdm

import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from model import SiameseNetwork
from dataset import Dataset

if __name__ == "__main__":
    train_path = "/home/choiyj/catkin_ws/src/soomac/src/vision/a/dataset/train"
    val_path = "/home/choiyj/catkin_ws/src/soomac/src/vision/a/dataset/val"
    out_path = "/home/choiyj/catkin_ws/src/soomac/src/vision"
    backbone = "resnet18"
    learning_rate = 1e-4
    epochs = 1000
    save_after = 2

    os.makedirs(out_path, exist_ok=True)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    train_dataset   = Dataset(train_path, shuffle_pairs=True, augment=True)
    val_dataset     = Dataset(val_path, shuffle_pairs=False, augment=False)
    
    train_dataloader = DataLoader(train_dataset, batch_size=8, drop_last=True)
    val_dataloader   = DataLoader(val_dataset, batch_size=8)

    model = SiameseNetwork(backbone=backbone)
    model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = torch.nn.BCELoss()

    writer = SummaryWriter(os.path.join(out_path, "summary"))

    best_val = 10000000000

    for epoch in range(epochs):
        print("[{} / {}]".format(epoch, epochs))
        model.train()

        losses = []
        correct = 0
        total = 0

        for (img1, img2), y, (class1, class2) in train_dataloader:
            img1, img2, y = map(lambda x: x.to(device), [img1, img2, y])

            prob = model(img1, img2)
            loss = criterion(prob, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            losses.append(loss.item())
            correct += torch.count_nonzero(y == (prob > 0.5)).item()
            total += len(y)

        writer.add_scalar('train_loss', sum(losses)/len(losses), epoch)
        writer.add_scalar('train_acc', correct / total, epoch)

        print("\tTraining: Loss={:.2f}\t Accuracy={:.2f}\t".format(sum(losses)/len(losses), correct / total))

        model.eval()

        losses = []
        correct = 0
        total = 0

        for (img1, img2), y, (class1, class2) in val_dataloader:
            img1, img2, y = map(lambda x: x.to(device), [img1, img2, y])

            prob = model(img1, img2)
            loss = criterion(prob, y)

            losses.append(loss.item())
            correct += torch.count_nonzero(y == (prob > 0.5)).item()
            total += len(y)

        val_loss = sum(losses)/max(1, len(losses))
        writer.add_scalar('val_loss', val_loss, epoch)
        writer.add_scalar('val_acc', correct / total, epoch)

        print("\tValidation: Loss={:.2f}\t Accuracy={:.2f}\t".format(val_loss, correct / total))

        if val_loss < best_val:
            best_val = val_loss
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "backbone": backbone,
                    "optimizer_state_dict": optimizer.state_dict()
                },
                os.path.join(out_path, "best.pth")
            )            

        if (epoch + 1) % save_after == 0:
            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "backbone": backbone,
                    "optimizer_state_dict": optimizer.state_dict()
                },
                os.path.join(out_path, "epoch_{}.pth".format(epoch + 1))
            )