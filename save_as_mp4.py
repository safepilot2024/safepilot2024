import pygame
import os
import carla
import time
from acero_main import *
import acero_main

import os
import time
import subprocess
from glob import glob
import re

# 自定义排序函数，按文件名中的数字部分排序
def numerical_sort(value):
    parts = re.split(r'(\d+)', value)
    parts[1::2] = map(int, parts[1::2])
    return parts

# 图片转视频的函数
def pictures_to_video(FRAME_RATE, mission_number):
    file_time = time.strftime("%m-%d-%H-%M", time.localtime())

    video_folders = ['/home/test/drivefuzz_log/video_behavior_agent/' + mission_number + "/"]
    video_types = ["front", "top"]
    video_files = []

    for video_type in video_types:
        vid_filename = f"{video_folders[0]}{file_time}-{video_type}.mp4"
        video_files.append(vid_filename)

        if os.path.exists(vid_filename):
            os.remove(vid_filename)

        # 获取并按数字部分排序图片文件名
        image_files = sorted(glob(f"/home/test/drivefuzz_log/picture/{video_type}-*.jpg"), key=numerical_sort)

        # 将图片文件名写入临时文件列表
        list_filename = f"/home/test/drivefuzz_log/picture/{video_type}_list.txt"
        with open(list_filename, 'w') as list_file:
            for image_file in image_files:
                list_file.write(f"file '{image_file}'\n")

        # 使用ffmpeg合并视频
        cmd_ffmpeg = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-r", str(FRAME_RATE),
            "-i", list_filename,
            "-vcodec", "libx264",
            vid_filename
        ]

        subprocess.run(cmd_ffmpeg, stderr=subprocess.DEVNULL)
        print(f"Saving {video_type} camera video (done)")

        # 删除临时文件列表
        os.remove(list_filename)

        # 删除图像文件
        for image_file in image_files:
            os.remove(image_file)

    # 根据 ATTACK_SUCCESS 判断是否保留视频
    if not acero_main.ATTACK_SUCCESS:
        for vid_filename in video_files:
            if os.path.exists(vid_filename):
                os.remove(vid_filename)
                print(f"Removed {vid_filename} due to attack failure.")

    if acero_main.WRONGD:
        for vid_filename in video_files:
            if os.path.exists(vid_filename):
                os.remove(vid_filename)
                print(f"Removed {vid_filename} due to attacker wrong direction.")

    if acero_main.ATTACK_COLLISION_OBJECT:
        for vid_filename in video_files:
            if os.path.exists(vid_filename):
                os.remove(vid_filename)
                print(f"Removed {vid_filename} due to attacker collision.")


def save_picture(world, player,last_time,mission_number):

    sensors = []
    # 获取蓝图库中的RGB相机
    blueprint_library = world.get_blueprint_library()
    rgb_camera_bp = blueprint_library.find("sensor.camera.rgb")

    # 设置相机属性
    # rgb_camera_bp.set_attribute("image_size_x", "3840")
    # rgb_camera_bp.set_attribute("image_size_y", "2160")

    rgb_camera_bp.set_attribute("image_size_x", "1920")
    rgb_camera_bp.set_attribute("image_size_y", "1080")

    rgb_camera_bp.set_attribute("fov", "105")

    rgb_camera_bp.set_attribute("sensor_tick", "0.1")  # 每秒30帧

    # # 前置相机位置
    # camera_tf = carla.Transform(carla.Location(z=1.8))
    # camera_front = world.spawn_actor(
    #         rgb_camera_bp,
    #         camera_tf,
    #         attach_to=player,
    #         attachment_type=carla.AttachmentType.Rigid
    # )
    # camera_front.listen(lambda image: _on_front_camera_capture(image))
    # sensors.append(camera_front)

    # 顶置相机位置
    camera_tf = carla.Transform(
        carla.Location(z=50.0),
        carla.Rotation(pitch=-90.0)
    )
    camera_top = world.spawn_actor(
            rgb_camera_bp,
            camera_tf,
            attach_to=player,
            attachment_type=carla.AttachmentType.Rigid
    )
    camera_top.listen(lambda image: _on_top_camera_capture(image))
    sensors.append(camera_top)

    print("begin to save picture")
    
    # 设置定时器，时间到后销毁传感器
    time.sleep(last_time)
    for sensor in sensors:
        sensor.stop()
        sensor.destroy()
    print("Sensors are cleaned up after recording for {} seconds.".format(last_time))
    print("begin to save video")
    pictures_to_video(20,mission_number)


#��¼ͼƬ�ļ��ĺ���
def _on_front_camera_capture(image):
    image.save_to_disk(f"/home/test/drivefuzz_log/picture/front-{image.frame}.jpg")

def _on_top_camera_capture(image):
    image.save_to_disk(f"/home/test/drivefuzz_log/picture/top-{image.frame}.jpg")


