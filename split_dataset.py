import argparse
import random


def split_train_test_valid(input_path, output_path, test_len, val_len):
    # read file
    assert input_path is not None, "Input file not found"
    file = open(input_path, "r")
    lines = file.readlines()
    print(len(lines))

    # define the ratios
    # test_len = 10000
    # val_len = 10000
    train_len = len(lines) - test_len - val_len

    # split the dataframe
    test_val_indices = random.sample(range(0, len(lines)), test_len + val_len)
    test_indices = test_val_indices[:test_len]
    val_indices = test_val_indices[test_len:]
    test_indices.sort()
    val_indices.sort()
    # print(test_indices, val_indices)

    # output
    val_out = open(output_path + "MTV2_val.txt", "a")
    for indice in val_indices:
        val_out.write(lines[indice])
    val_out.close()

    test_out = open(output_path + "MTV2_test.txt", "a")
    for indice in test_indices:
        test_out.write(lines[indice])
    test_out.close()

    train_out = open(output_path + "MTV2_train.txt", "a")
    i = -1
    for line in lines:
        i = i + 1
        if i in test_val_indices:
            continue
        train_out.write(line)
    train_out.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="split_dataset.py")
    parser.add_argument("--file", type=str, default="MTV2/MTV2_all.txt", help="List file of all images")
    parser.add_argument("--output_path", type=str, default="MTV2/", help="Path of the output files")
    parser.add_argument("--test_len", type=int, default=10000, help="Number of images for test")
    parser.add_argument("--val_len", type=int, default=10000, help="Number of images for val")
    opt = parser.parse_args()
    print(opt)

    split_train_test_valid(opt.file, opt.output_path, opt.test_len, opt.val_len)
