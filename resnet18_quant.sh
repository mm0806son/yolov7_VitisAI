# inspect model resnet18
echo "inspect model resnet18"
python resnet18_quant.py --quant_mode float --inspect

# calib model resnet18
echo "calib model resnet18"
python resnet18_quant.py --quant_mode calib

# deploy model resnet18
echo "test model resnet18"
python resnet18_quant.py --quant_mode test
echo "deploy model resnet18"
python resnet18_quant.py --quant_mode test --subset_len 1 --batch_size=1 --deploy
