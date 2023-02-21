# quantize model using test.py
# inspect
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 32 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/train/detect/weights/best.pt --name yolov7_tiny_odessa --inspect --quant_mode float
# calib
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/train/detect/weights/best.pt --name yolov7_tiny_odessa --quant_mode calib
# test
# python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/train/detect/weights/best.pt --name yolov7_tiny_odessa --quant_mode test
# python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/train/detect/weights/best.pt --name yolov7_tiny_odessa --quant_mode test --deploy