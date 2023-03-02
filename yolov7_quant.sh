# inspect model yolov7_tiny
# python torchhub_quant.py --quant_mode float --inspect --model runs/train/detect/weights/best.pt

# quantifize model yolov7_tiny
python yolov7_quant.py --quant_mode calib --model runs/train/detect/weights/best.pt

# deploy model yolov7_tiny
python yolov7_quant.py --quant_mode test --model runs/train/detect/weights/best.pt
python yolov7_quant.py --quant_mode test --model runs/train/detect/weights/best.pt --subset_len 1 --batch_size=1 --deploy