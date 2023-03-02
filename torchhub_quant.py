from hubconf import custom
from pytorch_nndct.apis import torch_quantizer
import argparse
import torch

# model = custom(path_or_model='odessa_tiny.pt')  # custom example
# model = custom(path_or_model='runs/train/yolov7_odessa/weights/init.pt') 
# model = create(name='yolov7', pretrained=True, channels=3, classes=2, autoshape=True)  # pretrained example

# Verify inference
import numpy as np
from PIL import Image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

parser = argparse.ArgumentParser()

parser.add_argument(
    '--batch_size',
    default=32,
    type=int,
    help='input data batch size to evaluate model')

parser.add_argument('--quant_mode', 
    default='calib', 
    choices=['float', 'calib', 'test'], 
    help='quantization mode. 0: no quantization, evaluate float model, calib: quantize, test: evaluate quantized model')

parser.add_argument('--target', 
    dest='target',
    default="DPUCZDX8G_ISA1_B4096",
    nargs="?",
    const="",
    help='specify target device')

parser.add_argument('--inspect', 
    dest='inspect',
    action='store_true',
    help='inspect model')

parser.add_argument('--model', 
    default='odessa_tiny.pt',
    type=str,
    help='path_or_model')

parser.add_argument(
    '--config_file',
    default=None,
    help='quantization configuration file')

parser.add_argument('--deploy', 
    dest='deploy',
    action='store_true',
    help='export xmodel for deployment')

parser.add_argument(
    '--subset_len',
    default=None,
    type=int,
    help='subset_len to evaluate model, using the whole validation dataset if it is not set')

args, _ = parser.parse_known_args()

batch_size = args.batch_size
inspect = args.inspect
target = args.target
quant_mode = args.quant_mode
path_or_model = args.model
config_file = args.config_file
deploy = args.deploy
subset_len = args.subset_len

model = custom(path_or_model=path_or_model)

input = torch.randn([batch_size, 3, 224, 224])
if quant_mode == 'float':
    quant_model = model
    if inspect:
      if not target:
          raise RuntimeError("A target should be specified for inspector.")
      import sys
      from pytorch_nndct.apis import Inspector
      # create inspector
      inspector = Inspector(target)  # by name
      # start to inspect
      inspector.inspect(quant_model, (input,), device=device, image_format="svg")
      sys.exit()
      
else:
    ## new api
    ####################################################################################
    quantizer = torch_quantizer(
        quant_mode, model, (input), device=device, quant_config_file=config_file, target=target)

    quant_model = quantizer.quant_model
    #####################################################################################

# handle quantization result
if quant_mode == 'calib':
    quantizer.export_quant_config()
if deploy:
    quantizer.export_torch_script()
    quantizer.export_onnx_model()
    quantizer.export_xmodel(deploy_check=False)


# imgs=[]
# path_train = "/workspace/yolov7/MTV2/MTV2_train_docker.txt"
# file = open(path_train, "r")
# print(f"file name = ", file.name)
# for line in file.readlines():
#     line = line.strip("\n")
#     imgs.append(line)
# file.close()

# results = model(imgs)  # batched inference
# results.print()
# results.save()