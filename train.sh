# train models
python train.py --workers 20 --device 0 --batch-size 64 --data data/odessa.yaml --img 640 640 --cfg cfg/training/yolov7-tiny_odessa.yaml --weights '' --name yolov7_tiny_odessa --hyp data/hyp.scratch.tiny_odessa.yaml --epochs 300 --project Yolov7_VitisAI
