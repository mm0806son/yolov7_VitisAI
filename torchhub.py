from  hubconf import custom
model = custom(path_or_model='odessa.pt')  # custom example
# model = create(name='yolov7', pretrained=True, channels=3, classes=80, autoshape=True)  # pretrained example

# Verify inference
import numpy as np
from PIL import Image


imgs=[]
path_train = "/workspace/yolov7/MTV2/MTV2_train_docker.txt"
file = open(path_train, "r")
print(f"file name = ", file.name)
for line in file.readlines():
    line = line.strip("\n")
    imgs.append(line)
file.close()

results = model(imgs)  # batched inference
results.print()
results.save()