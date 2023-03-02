# train models yolov7_tiny
python train.py --workers 8 --device cpu --batch-size 32 --data data/odessa_docker.yaml --img 640 640 --cfg cfg/training/yolov7-tiny_odessa.yaml --weights '' --name yolov7_tiny_odessa_nodetect --hyp data/hyp.scratch.tiny_odessa.yaml --epochs 10
# train models yolo
# python train.py --workers 8 --device 0 --batch-size 16 --data data/odessa.yaml --img 640 640 --cfg cfg/training/yolov7_odessa.yaml --weights '' --name yolov7_odessa --hyp data/hyp.scratch.custom.yaml
