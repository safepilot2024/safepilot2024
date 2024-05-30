import os
import sys
import argparse
from subprocess import Popen, PIPE
import signal
import numpy as np
import random
import time
import math
import traceback
import docker
import config
# import constants as c
import carla
import pygame
from driving_quality import *

FRAME_RATE = 30


def get_data(player,sp,attacker,npc,last_time):

    clock = pygame.time.Clock()
    start_time = time.time()
    cont_throttle = []
    cont_brake = []
    cont_steer = []
    steer_angle_list = []
    speed = []
    speed_lim = []
    yaw_list = []
    yaw_rate_list = []
    lat_speed_list = []
    lon_speed_list = []
    min_dist = 99999



    while time.time()-start_time<=last_time:
        #�����������whileѭ���ĵ�һ�� ���ܱ�֤ÿ��ѭ����ʱ���ǹ̶���
        clock.tick(FRAME_RATE)

        # get vehicle's maximum steering angle
        # ���ָ������ĳ��ֵ����ת��Ƕ�
        physics_control = player.get_physics_control()
        max_steer_angle = 0
        for wheel in physics_control.wheels:
            if wheel.max_steer_angle > max_steer_angle:
                max_steer_angle = wheel.max_steer_angle


        #���victim�Ŀ�����Ϣ
        control = player.get_control()
        cont_throttle.append(control.throttle)
        cont_brake.append(control.brake)
        cont_steer.append(control.steer)
        steer_angle = control.steer * max_steer_angle
        steer_angle_list.append(steer_angle)

        #����ٶȵ������Ϣ
        vel = player.get_velocity()
        speed = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
        speed_limit = player.get_speed_limit()
        speed.append(speed)
        speed_lim.append(speed_limit)


        #��ýǶ������Ϣ
        player_transform = player.get_transform()
        player_loc = player_transform.location
        player_rot = player_transform.rotation
        current_yaw = player_rot.yaw
        yaw_list.append(current_yaw)


        #sp����ʼλ��
        yaw = sp.rotation.yaw
        yaw_diff = current_yaw - yaw
        if yaw_diff > 180:
            yaw_diff = 360 - yaw_diff
        elif yaw_diff < -180:
            yaw_diff = 360 + yaw_diff
        yaw_rate = yaw_diff * FRAME_RATE
        yaw_rate_list.append(yaw_rate)
        yaw = current_yaw


        #�����С����
        v = attacker
        dist = player_loc.distance(v.get_location())
        if dist < min_dist:
            min_dist = dist

        w = npc
        dist = player_loc.distance(w.get_location())
        if dist < min_dist:
            min_dist = dist

        #��ú����ٶ�
        player_right_vec = player_rot.get_right_vector()
        lat_speed = abs(vel.x * player_right_vec.x + vel.y * player_right_vec.y)
        lat_speed *= 3.6 # m/s to km/h
        lat_speed_list.append(lat_speed)

        player_fwd_vec = player_rot.get_forward_vector()
        lon_speed = abs(vel.x * player_fwd_vec.x + vel.y * player_fwd_vec.y)
        lon_speed *= 3.6
        lon_speed_list.append(lon_speed)

    return cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist

