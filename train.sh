# train models
python train.py --workers 8 --device cpu --batch-size 32 --data data/odessa.yaml --img 640 640 --cfg cfg/training/yolov7-tiny_odessa.yaml --weights '' --name yolov7_tiny_odessa --hyp data/hyp.scratch.tiny_odessa.yaml --epochs 10
