import argparse
import json
import os
from pathlib import Path
import threading
from threading import Thread
import time
import sys

import numpy as np
import torch
import torch.nn as nn
import yaml
from tqdm import tqdm
import copy
import cv2
from ctypes import *
from typing import List
import xir
import vart

from models.experimental import attempt_load
from utils.datasets import create_dataloader
from utils.general import (
    check_dataset,
    check_file,
    check_img_size,
    check_requirements,
    box_iou,
    non_max_suppression,
    scale_coords,
    xyxy2xywh,
    xywh2xyxy,
    set_logging,
    increment_path,
    colorstr,
)
from utils.metrics import ap_per_class, ConfusionMatrix
from utils.plots import plot_images, output_to_target, plot_study_txt
from utils.torch_utils import select_device, time_synchronized, TracedModel

import wandb


def get_child_subgraph_dpu(graph: "Graph") -> List["Subgraph"]:
    assert graph is not None, "'graph' should not be None."
    root_subgraph = graph.get_root_subgraph()
    assert root_subgraph is not None, "Failed to get root subgraph of input Graph object."
    if root_subgraph.is_leaf:
        return []
    child_subgraphs = root_subgraph.toposort_child_subgraph()
    assert child_subgraphs is not None and len(child_subgraphs) > 0
    return [cs for cs in child_subgraphs if cs.has_attr("device") and cs.get_attr("device").upper() == "DPU"]


def runDPU(dpu, img):
    """get tensor"""
    # TODO Multi-thread
    inputTensors = dpu.get_input_tensors()
    outputTensors = dpu.get_output_tensors()
    input_ndim = tuple(inputTensors[0].dims)
    output_ndim_0 = tuple(outputTensors[0].dims)
    output_ndim_1 = tuple(outputTensors[1].dims)
    output_ndim_2 = tuple(outputTensors[2].dims)

    start = 0
    batchSize = input_ndim[0]
    n_of_images = len(img)
    count = 0

    outputData = [
        np.empty(output_ndim_0, dtype=np.float32, order="C"),
        np.empty(output_ndim_1, dtype=np.float32, order="C"),
        np.empty(output_ndim_2, dtype=np.float32, order="C"),
    ]

    while count < n_of_images:
        if count + batchSize <= n_of_images:
            runSize = batchSize
        else:
            runSize = n_of_images - count

        """prepare batch input/output """
        inputData = []
        inputData = [np.empty(input_ndim, dtype=np.int8, order="C")]

        """init input image to input buffer """
        # ? imageRun defined but never used?
        for j in range(runSize):
            imageRun = inputData[0]
            imageRun[j, ...] = img[(count + j) % n_of_images].reshape(input_ndim[1:])
        """run """
        job_id = dpu.execute_async(inputData, outputData)
        dpu.wait(job_id)

        # output scaling
        # output_fixpos = outputTensors[0].get_attr("fix_point")
        # output_scale = 1 / (2**output_fixpos)
        outputData[0] = torch.from_numpy(outputData[0] / (2 ** outputTensors[0].get_attr("fix_point"))).permute(
            0, 3, 1, 2
        )
        outputData[1] = torch.from_numpy(outputData[1] / (2 ** outputTensors[1].get_attr("fix_point"))).permute(
            0, 3, 1, 2
        )
        outputData[2] = torch.from_numpy(outputData[2] / (2 ** outputTensors[2].get_attr("fix_point"))).permute(
            0, 3, 1, 2
        )

        return outputData


def forward_detect(model_detect, x):
    m = model_detect.model[0]
    x = m(x)  # run
    return x


def test(
    data,
    weights=None,
    batch_size=32,
    imgsz=640,
    conf_thres=0.001,
    iou_thres=0.6,  # for NMS
    single_cls=False,
    model=None,
    dataloader=None,
    save_dir=Path(""),  # for saving images
    save_txt=False,  # for auto-labelling
    save_hybrid=False,  # for hybrid auto-labelling
    save_conf=False,  # save auto-label confidences
    plots=False,
    wandb_logger=None,
    compute_loss=None,
    v5_metric=False,
    threads=1,
    xmodel="quantize_result/compiled/yolov7.xmodel",
):
    # Initialize/load model and set device
    set_logging()
    device = select_device(opt.device, batch_size=batch_size)

    # Directories
    save_dir, save_name = increment_path(opt.project, opt.name, exist_ok=opt.exist_ok)  # increment run
    save_dir = Path(save_dir)
    (save_dir / "labels" if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    wandb.init(project=opt.project, name=save_name, notes=opt.notes)

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    gs = max(int(model.stride.max()), 32)  # grid size (max stride)
    imgsz = check_img_size(imgsz, s=gs)  # check img_size

    model_detect = copy.deepcopy(model)
    model_detect.model = nn.Sequential(model.model[-1])
    model_detect.eval()

    if isinstance(data, str):
        with open(data) as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
    check_dataset(data)  # check
    nc = 1 if single_cls else int(data["nc"])  # number of classes
    iouv = torch.linspace(0.5, 0.95, 10).to(device)  # iou vector for mAP@0.5:0.95
    niou = iouv.numel()

    # Logging
    log_imgs = 0
    if wandb_logger and wandb_logger.wandb:
        log_imgs = min(wandb_logger.log_imgs, 100)
    # Dataloader
    task = opt.task if opt.task in ("train", "val", "test") else "val"  # path to train/val/test images

    g = xir.Graph.deserialize(xmodel)
    subgraphs = get_child_subgraph_dpu(g)
    dpu_runner = vart.Runner.create_runner(subgraphs[0], "run")

    # 读取量化后模型对输入的定点数数据的小数点位置，得出在浮点数转定点数时需要乘的系数input_scale
    input_fixpos = dpu_runner.get_input_tensors()[0].get_attr("fix_point")
    input_scale = 2**input_fixpos

    dataloader = create_dataloader(
        data[task],
        imgsz,
        batch_size,
        gs,
        opt,
        pad=0.5,
        rect=True,
        prefix=colorstr(f"{task}: "),
        input_scale=input_scale,
    )[0]

    seen = 0
    confusion_matrix = ConfusionMatrix(nc=nc)
    # names = {k: v for k, v in enumerate(quant_model.names if hasattr(quant_model, "names") else quant_model.module.names)} # find names from model
    names = {0: "Boat", 1: "Human"}
    s = ("%20s" + "%12s" * 6) % ("Class", "Images", "Labels", "P", "R", "mAP@.5", "mAP@.5:.95")
    p, r, f1, mp, mr, map50, map, t0, t1 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    loss = torch.zeros(3, device=device)
    jdict, stats, ap, ap_class, wandb_images = [], [], [], [], []
    for batch_i, (img, targets, paths, shapes) in enumerate(tqdm(dataloader, desc=s)):
        out_q = [None] * batch_size
        img = img.to(device, non_blocking=True)
        img = img.float()
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        targets = targets.to(device)
        nb, _, height, width = img.shape  # batch size, channels, height, width

        with torch.no_grad():
            # Run model
            t = time_synchronized()

            # out_q = [None] * nb

            # time1 = time.time()
            out = runDPU(dpu_runner, img)
            # time2 = time.time()
            # timetotal = time2 - time1
            # fps = float(nb / timetotal)
            # print("Throughput=%.2f fps, total frames = %.0f, time=%.4f seconds" % (fps, nb, timetotal))

            out, train_out = forward_detect(model_detect, out)

            t0 += time_synchronized() - t

            # Compute loss
            if compute_loss:
                loss += compute_loss([x.float() for x in train_out], targets)[1][:3]  # box, obj, cls

            # Run NMS
            targets[:, 2:] *= torch.Tensor([width, height, width, height]).to(device)  # to pixels
            lb = [targets[targets[:, 0] == i, 1:] for i in range(nb)] if save_hybrid else []  # for autolabelling
            t = time_synchronized()
            out = non_max_suppression(out, conf_thres=conf_thres, iou_thres=iou_thres, labels=lb, multi_label=True)
            t1 += time_synchronized() - t
        # """
        # Statistics per image
        for si, pred in enumerate(out):
            labels = targets[targets[:, 0] == si, 1:]
            nl = len(labels)
            tcls = labels[:, 0].tolist() if nl else []  # target class
            path = Path(paths[si])
            seen += 1

            if len(pred) == 0:
                if nl:
                    stats.append((torch.zeros(0, niou, dtype=torch.bool), torch.Tensor(), torch.Tensor(), tcls))
                continue

            # Predictions
            predn = pred.clone()
            scale_coords(img[si].shape[1:], predn[:, :4], shapes[si][0], shapes[si][1])  # native-space pred

            # Append to text file
            if save_txt:
                gn = torch.tensor(shapes[si][0])[[1, 0, 1, 0]]  # normalization gain whwh
                for *xyxy, conf, cls in predn.tolist():
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                    line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                    with open(save_dir / "labels" / (path.stem + ".txt"), "a") as f:
                        f.write(("%g " * len(line)).rstrip() % line + "\n")

            # W&B logging - Media Panel Plots
            if len(wandb_images) < log_imgs and wandb_logger.current_epoch > 0:  # Check for test operation
                if wandb_logger.current_epoch % wandb_logger.bbox_interval == 0:
                    box_data = [
                        {
                            "position": {"minX": xyxy[0], "minY": xyxy[1], "maxX": xyxy[2], "maxY": xyxy[3]},
                            "class_id": int(cls),
                            "box_caption": "%s %.3f" % (names[cls], conf),
                            "scores": {"class_score": conf},
                            "domain": "pixel",
                        }
                        for *xyxy, conf, cls in pred.tolist()
                    ]
                    boxes = {"predictions": {"box_data": box_data, "class_labels": names}}  # inference-space
                    wandb_images.append(wandb_logger.wandb.Image(img[si], boxes=boxes, caption=path.name))
            wandb_logger.log_training_progress(predn, path, names) if wandb_logger and wandb_logger.wandb_run else None

            # Assign all predictions as incorrect
            correct = torch.zeros(pred.shape[0], niou, dtype=torch.bool, device=device)
            if nl:
                detected = []  # target indices
                tcls_tensor = labels[:, 0]

                # target boxes
                tbox = xywh2xyxy(labels[:, 1:5])
                scale_coords(img[si].shape[1:], tbox, shapes[si][0], shapes[si][1])  # native-space labels
                if plots:
                    confusion_matrix.process_batch(predn, torch.cat((labels[:, 0:1], tbox), 1))

                # Per target class
                for cls in torch.unique(tcls_tensor):
                    ti = (cls == tcls_tensor).nonzero(as_tuple=False).view(-1)  # prediction indices
                    pi = (cls == pred[:, 5]).nonzero(as_tuple=False).view(-1)  # target indices

                    # Search for detections
                    if pi.shape[0]:
                        # Prediction to target ious
                        ious, i = box_iou(predn[pi, :4], tbox[ti]).max(1)  # best ious, indices

                        # Append detections
                        detected_set = set()
                        for j in (ious > iouv[0]).nonzero(as_tuple=False):
                            d = ti[i[j]]  # detected target
                            if d.item() not in detected_set:
                                detected_set.add(d.item())
                                detected.append(d)
                                correct[pi[j]] = ious[j] > iouv  # iou_thres is 1xn
                                if len(detected) == nl:  # all targets already located in image
                                    break

            # Append statistics (correct, conf, pcls, tcls)
            stats.append((correct.cpu(), pred[:, 4].cpu(), pred[:, 5].cpu(), tcls))

        # Plot images
        if plots and batch_i < 3:
            f = save_dir / f"test_batch{batch_i}_labels.jpg"  # labels
            Thread(target=plot_images, args=(img, targets, paths, f, names), daemon=True).start()
            f = save_dir / f"test_batch{batch_i}_pred.jpg"  # predictions
            Thread(target=plot_images, args=(img, output_to_target(out), paths, f, names), daemon=True).start()

    # Compute statistics
    stats = [np.concatenate(x, 0) for x in zip(*stats)]  # to numpy
    if len(stats) and stats[0].any():
        p, r, ap, f1, ap_class = ap_per_class(*stats, plot=plots, v5_metric=v5_metric, save_dir=save_dir, names=names)
        ap50, ap = ap[:, 0], ap.mean(1)  # AP@0.5, AP@0.5:0.95
        mp, mr, map50, map = p.mean(), r.mean(), ap50.mean(), ap.mean()
        nt = np.bincount(stats[3].astype(np.int64), minlength=nc)  # number of targets per class
    else:
        nt = torch.zeros(1)

    # Print results
    pf = "%20s" + "%12i" * 2 + "%12.3g" * 4  # print format
    print(pf % ("all", seen, nt.sum(), mp, mr, map50, map))

    # Print results per class
    # if (verbose or (nc < 50 and not training)) and nc > 1 and len(stats):
    for i, c in enumerate(ap_class):
        print(pf % (names[c], seen, nt[c], p[i], r[i], ap50[i], ap[i]))

    # Print speeds
    t = tuple(x / seen * 1e3 for x in (t0, t1, t0 + t1)) + (imgsz, imgsz, batch_size)  # tuple
    # if not training:
    print("Speed: %.1f/%.1f/%.1f ms inference/NMS/total per %gx%g image at batch-size %g" % t)

    # Plots
    if plots:
        confusion_matrix.plot(save_dir=save_dir, names=list(names.values()))
        if wandb_logger and wandb_logger.wandb:
            val_batches = [wandb_logger.wandb.Image(str(f), caption=f.name) for f in sorted(save_dir.glob("test*.jpg"))]
            wandb_logger.log({"Validation": val_batches})
    if wandb_images:
        wandb_logger.log({"Bounding Box Debugger/Images": wandb_images})

    # Return results
    s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ""
    print(f"Results saved to {save_dir}{s}")
    maps = np.zeros(nc) + map
    for i, c in enumerate(ap_class):
        maps[c] = ap[i]
    # """

    # return (mp, mr, map50, map, *(loss.cpu() / len(dataloader)).tolist()), maps, t
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="test.py")
    parser.add_argument("--weights", nargs="+", type=str, default="yolov7.pt", help="model.pt path(s)")
    parser.add_argument("--data", type=str, default="data/coco.yaml", help="*.data path")
    parser.add_argument("--batch-size", type=int, default=32, help="size of each image batch")
    parser.add_argument("--img-size", type=int, default=640, help="inference size (pixels)")
    parser.add_argument("--conf-thres", type=float, default=0.001, help="object confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.65, help="IOU threshold for NMS")
    parser.add_argument("--task", default="val", help="train, val, test, speed or study")
    parser.add_argument("--device", default="", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument("--single-cls", action="store_true", help="treat as single-class dataset")
    parser.add_argument("--save-txt", action="store_true", help="save results to *.txt")
    parser.add_argument("--save-hybrid", action="store_true", help="save label+prediction hybrid results to *.txt")
    parser.add_argument("--save-conf", action="store_true", help="save confidences in --save-txt labels")
    parser.add_argument("--project", default="runs/test", help="save to project/name")
    parser.add_argument("--name", default="exp", help="save to project/name")
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment")
    parser.add_argument("--notes", type=str, default=None, help="notes of this run for wandb")

    parser.add_argument(
        "--target", dest="target", default="DPUCZDX8G_ISA1_B4096", nargs="?", const="", help="specify target device"
    )

    parser.add_argument("--config_file", default=None, help="quantization configuration file")
    parser.add_argument("--threads", type=int, default=1, help="Number of threads. Default is 1")
    parser.add_argument("--xmodel", type=str, default="quantize_result/compiled/yolov7.xmodel", help="Path of xmodel.")

    opt = parser.parse_args()
    opt.data = check_file(opt.data)  # check file
    print(opt)
    # check_requirements()

    test(
        opt.data,
        opt.weights,
        opt.batch_size,
        opt.img_size,
        opt.conf_thres,
        opt.iou_thres,
        opt.single_cls,
        save_txt=opt.save_txt | opt.save_hybrid,
        save_hybrid=opt.save_hybrid,
        save_conf=opt.save_conf,
        threads=opt.threads,
        xmodel=opt.xmodel,
    )
