"""
@Name           :select_images.py
@Description    :According to the txt file, copy images to a separate folder to be scp to remote.
@Time           :2023/03/14 13:49:56
@Author         :Zijie NING
@Version        :1.0
"""

import argparse
import os
import shutil


def check_folder(folder_path):
    os.path.abspath(folder_path)
    if os.path.isdir(folder_path):
        print(f"Folder: ", folder_path)
    else:
        os.makedirs(folder_path)
        print(f"Create folder: ", folder_path)
    return folder_path


def select_images(input, output, dataset):
    # check_folder(output)
    assert input is not None, "Input file not found"
    file = open(input, "r")
    lines = file.readlines()
    for line in lines:
        line = line.replace("\n", "").replace("\r", "")
        output_path = os.path.abspath(output) + line[len(os.path.abspath(dataset)) :]
        check_folder(os.path.dirname(output_path))
        shutil.copyfile(line, output_path)
        shutil.copyfile(line[:-3] + "txt", output_path[:-3] + "txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="split_dataset.py")
    parser.add_argument("--file", type=str, default="../MTV2/MTV2_test.txt", help="List file of images")
    parser.add_argument("--output", type=str, default="../MTV2_test", help="Path of the output folder")
    parser.add_argument("--dataset", type=str, default="../MTV2", help="Path of the dataset folder")
    opt = parser.parse_args()
    print(opt)

    select_images(opt.file, opt.output, opt.dataset)
