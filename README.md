# yolov7_VitisAI
This is the implementation of YOLOv7 on Vitis AI (KV260).

See [here](https://github.com/mm0806son/yolov7_VitisAI/blob/main/Implement_of_Yolov7_on_Vitis_AI_KV260.pdf) for the overall tutorial.

## Branches

- `main`: train a new yolov7 model on PC
- `quantize`: inspect, quantize and compile a model in docker environment
- `execute_v2`: launch the model with compiled xmodel file on edge device (PetaLinux on KV260)
