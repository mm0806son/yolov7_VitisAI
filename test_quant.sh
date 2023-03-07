# quantize model using test.py
# inspect
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 32 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/nodetect.pt --name yolov7_tiny_odessa --inspect --quant_mode float --output_dir quantize_result/nodetect
# calib
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/nodetect.pt --name yolov7_tiny_odessa --quant_mode calib  --output_dir quantize_result/nodetect
# test
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/nodetect.pt --name yolov7_tiny_odessa --quant_mode test --output_dir quantize_result/nodetect
python test_quant.py --data data/odessa_docker.yaml --img 640 --batch-size 1 --conf-thres 0.001 --iou 0.65 --device cpu --weights runs/nodetect.pt --name yolov7_tiny_odessa --quant_mode test --deploy --output_dir quantize_result/nodetect