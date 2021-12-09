
""" Offline data generation for the OXFORD dataset."""


import os
from absl import app
from absl import flags
from absl import logging
import numpy as np
import cv2
import os, glob
import argparse
# run time
import timeit
# time format
import time


SEQ_LENGTH = 3
# WIDTH = 416
WIDTH = 640
# HEIGHT = 128
HEIGHT = 192
STEPSIZE = 1
CROP_AREA = [0, 360, 1280, 730]
DIR = '/media/RAIDONE/radice/datasets/oxford'


def parse_args():
    parser = argparse.ArgumentParser(description='Data generator for depth-and-motion-learning')
    parser.add_argument('--folder', type=str,
                        help='folder containing files',
                        required=True)
    return parser.parse_args()


def run_all(args):
    folder = args.folder
    path = os.path.join(DIR, folder)

    # rename input files with leading zeros
    # left_folder = os.path.join(input_path, 'processed/stereo/left')
    # print('-> Left folder', left_folder)
    # right_folder = os.path.join(input_path, 'processed/stereo/right')
    # print('-> Right folder', right_folder)
    #
    # for file in os.listdir(left_folder):
    #     num = file.split('.')[0]
    #     num = num.zfill(10)
    #     new_filename = num + '.jpg'
    #     os.rename(os.path.join(left_folder, file), os.path.join(left_folder, new_filename))
    #
    # for file in os.listdir(right_folder):
    #     num = file.split('.')[0]
    #     num = num.zfill(10)
    #     new_filename = num + '.jpg'
    #     os.rename(os.path.join(right_folder, file), os.path.join(right_folder, new_filename))

    # start processing
    print('-> Processing', path)
    save_path = os.path.join(DIR, folder, 'struct2depth_640x192')
    print('-> Save path', save_path)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    if not os.path.exists(os.path.join(save_path, 'left')):
        os.mkdir(os.path.join(save_path, 'left'))
    # if not os.path.exists(os.path.join(save_path, 'right')):
    #     os.mkdir(os.path.join(save_path, 'right'))

    # oxford calib matrix
    fx = 983.044006
    fy = 983.044006
    cx = 643.646973
    cy = 493.378998

    crop_height = CROP_AREA[3] - CROP_AREA[1]
    crop_ci = CROP_AREA[3] - (crop_height / 2)
    crop_cy  = cy + float(crop_height - 1) / 2 - crop_ci

    # calib_camera = np.array([[fx, 0.0, cx],
    #                           [0.0, fy, crop_cy],
    #                           [0.0, 0.0, 1.0]])

    # for subfolder in ['stereo/left', 'stereo/right']:
    for subfolder in ['stereo/left']:

        start_partial = timeit.default_timer()
        current_seg = start_partial

        ct = 0
        files_path = os.path.join(path, subfolder)
        files = glob.glob(files_path + '/*.png')
        files = [file for file in files if not 'disp' in file and not 'flip' in file and not 'seg' in file]
        files = sorted(files)

        for i in range(SEQ_LENGTH, len(files)+1, STEPSIZE):
            imgnum = str(ct).zfill(10)

            big_img = np.zeros(shape=(HEIGHT, WIDTH*SEQ_LENGTH, 3))
            big_seg_img = np.zeros(shape=(HEIGHT, WIDTH*SEQ_LENGTH, 3))
            wct = 0

            for j in range(i-SEQ_LENGTH, i):  # Collect frames for this sample.
                img = cv2.imread(files[j])
                if subfolder == 'stereo/left':
                    seg_path = os.path.join(path, 'rcnn-masks', 'left',
                                            os.path.basename(files[j]).replace('.png', '-fseg.png'))
                # else:
                #     seg_path = os.path.join(path, 'masks', 'right',
                #                             os.path.basename(files[j]).replace('.png', '-fseg.png'))

                segimg = cv2.imread(seg_path)

                ORIGINAL_HEIGHT, ORIGINAL_WIDTH, _ = img.shape

                img = img[CROP_AREA[1]:CROP_AREA[3], :, :]

                zoom_x = WIDTH / ORIGINAL_WIDTH
                zoom_y = HEIGHT / ORIGINAL_HEIGHT

                # Adjust intrinsics.
                # calib_current = calib_camera.copy()
                # calib_current[0, 0] *= zoom_x
                # calib_current[0, 2] *= zoom_x
                # calib_current[1, 1] *= zoom_y
                # calib_current[1, 2] *= zoom_y

                current_fx = fx * zoom_x
                current_fy = fy * zoom_y
                current_cx = cx * zoom_x
                current_cy = crop_cy * zoom_y
                calib_current = np.array([[current_fx, 0.0, current_cx],
                                         [0.0, current_fy, current_cy],
                                         [0.0, 0.0, 1.0]])

                calib_representation = ','.join([str(c) for c in calib_current.flatten()])
                img = cv2.resize(img, (WIDTH, HEIGHT))
                segimg = cv2.resize(segimg, (WIDTH, HEIGHT))
                big_img[:,wct*WIDTH:(wct+1)*WIDTH] = img
                big_seg_img[:,wct*WIDTH:(wct+1)*WIDTH] = segimg
                wct+=1

            if subfolder == 'stereo/left':
                big_img_path = os.path.join(save_path, 'left', '{}.{}'.format(imgnum, 'png'))
                txt_path = os.path.join(save_path, 'left', '{}{}.{}'.format(imgnum, '_cam', 'txt'))
                big_seg_img_path = os.path.join(save_path, 'left', '{}{}.{}'.format(imgnum, '-fseg', 'png'))
            else:
                big_img_path = os.path.join(save_path, 'right', '{}.{}'.format(imgnum, 'png'))
                txt_path = os.path.join(save_path, 'right', '{}{}.{}'.format(imgnum, '_cam', 'txt'))
                big_seg_img_path = os.path.join(save_path, 'right', '{}{}.{}'.format(imgnum, '-fseg', 'png'))

            cv2.imwrite(big_img_path, big_img)
            cv2.imwrite(big_seg_img_path, big_seg_img)
            f = open(txt_path, 'w')
            f.write(calib_representation)
            f.close()

            if ct%1000==0 and ct!=0:
                print('->', ct, 'Done')
                stop_seg = timeit.default_timer()
                seg_run_time = int(stop_seg - current_seg)
                print('-> Segment run time:', time.strftime('%H:%M:%S', time.gmtime(seg_run_time)))
                current_seg += seg_run_time

            ct+=1

        stop_partial = timeit.default_timer()
        partial_run_time = int(stop_partial - start_partial)
        print('-> Partial run time:', time.strftime('%H:%M:%S', time.gmtime(partial_run_time)))

    print('-> DONE')


def main(args):
    run_all(args)


if __name__ == '__main__':
    # start timer
    start = timeit.default_timer()

    args = parse_args()
    app.run(main(args))

    # stop timer
    stop = timeit.default_timer()

    # total run time
    total_run_time = int(stop - start)
    print('-> Total run time:', time.strftime('%H:%M:%S', time.gmtime(total_run_time)))