# train models
python train.py --workers 20 --device 0 --batch-size 32 --data data/odessa.yaml --img 640 640 --cfg cfg/training/yolov7-tiny_odessa.yaml --weights '' --name yolov7_tiny_IDetect_rect --hyp data/hyp.scratch.tiny_odessa.yaml --epochs 50 --project Yolov7_VitisAI
