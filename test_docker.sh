# test models
python test.py --data data/odessa_docker.yaml --img 640 --batch 1 --conf 0.001 --iou 0.65 --device cpu --weights runs/train/detect/weights/best.pt --name yolov7_tiny_odessa
