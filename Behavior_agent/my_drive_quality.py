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


def get_data(player,yaw,attacker,npc,last_time,cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist_list):

    clock = pygame.time.Clock()
    start_time = time.time()
    # cont_throttle = []
    # cont_brake = []
    # cont_steer = []
    # steer_angle_list = []
    # speed = []
    # speed_lim = []
    # yaw_list = []
    # yaw_rate_list = []
    # lat_speed_list = []
    # lon_speed_list = []
    min_dist = 99999



    while time.time()-start_time<=last_time:
        #把这玩意放在while循环的第一行 就能保证每次循环的时间是固定的
        clock.tick(FRAME_RATE*2)

        # get vehicle's maximum steering angle
        # 获得指定对象的车轮的最大转向角度
        physics_control = player.get_physics_control()
        max_steer_angle = 0
        for wheel in physics_control.wheels:
            if wheel.max_steer_angle > max_steer_angle:
                max_steer_angle = wheel.max_steer_angle


        #获得victim的控制信息
        control = player.get_control()
        cont_throttle.append(control.throttle)
        cont_brake.append(control.brake)
        cont_steer.append(control.steer)
        steer_angle = control.steer * max_steer_angle
        steer_angle_list.append(steer_angle)

        #获得速度的相关信息
        vel = player.get_velocity()
        speed_temp = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
        speed_limit = player.get_speed_limit()
        speed.append(speed_temp)
        speed_lim.append(speed_limit)


        #获得角度相关信息
        player_transform = player.get_transform()
        player_loc = player_transform.location
        player_rot = player_transform.rotation
        current_yaw = player_rot.yaw
        yaw_list.append(current_yaw)


        #sp是起始位置
        # yaw = sp.rotation.yaw
        yaw_diff = current_yaw - yaw
        if yaw_diff > 180:
            yaw_diff = 360 - yaw_diff
        elif yaw_diff < -180:
            yaw_diff = 360 + yaw_diff
        yaw_rate = yaw_diff * FRAME_RATE
        yaw_rate_list.append(yaw_rate)
        yaw = current_yaw


        #获得最小距离
        v = attacker
        dist = player_loc.distance(v.get_location())
        if dist < min_dist:
            min_dist = dist

        w = npc
        dist = player_loc.distance(w.get_location())
        if dist < min_dist:
            min_dist = dist

        #获得横向速度
        player_right_vec = player_rot.get_right_vector()
        lat_speed = abs(vel.x * player_right_vec.x + vel.y * player_right_vec.y)
        lat_speed *= 3.6 # m/s to km/h
        lat_speed_list.append(lat_speed)

        player_fwd_vec = player_rot.get_forward_vector()
        lon_speed = abs(vel.x * player_fwd_vec.x + vel.y * player_fwd_vec.y)
        lon_speed *= 3.6
        lon_speed_list.append(lon_speed)
        min_dist_list.append(min_dist)

    return cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist

def process_data(cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist):
    # Attributes
    speed_list = np.array(speed)
    acc_list = np.diff(speed_list)

    Vx_list = np.array(lon_speed_list)
    Vy_list = np.array(lat_speed_list)
    SWA_list = np.array(steer_angle_list)

    # filter & process attributes
    Vx_light = get_vx_light(Vx_list)
    Ay_list = get_ay_list(Vy_list)
    Ay_diff_list = get_ay_diff_list(Ay_list)
    Ay_heavy = get_ay_heavy(Ay_list)
    SWA_diff_list = get_swa_diff_list(Vy_list)
    SWA_heavy_list = get_swa_heavy(SWA_list)
    Ay_gain = get_ay_gain(SWA_heavy_list, Ay_heavy)
    Ay_peak = get_ay_peak(Ay_gain)
    frac_drop = get_frac_drop(Ay_gain, Ay_peak)
    abs_yr = get_abs_yr(yaw_rate_list)

    deductions = 0

    # avoid infinitesimal md
    if int(min_dist) > 100:
        md = 0
    else:
        md = (1 / int(min_dist))

    ha = int(check_hard_acc(acc_list))
    hb = int(check_hard_braking(acc_list))
    ht = int(check_hard_turn(Vy_list, SWA_list))

    deductions += ha + hb + ht + md

    # check oversteer and understeer
    os_thres = 4
    us_thres = 4
    num_oversteer = 0
    num_understeer = 0
    for fid in range(len(Vy_list) - 2):
        SWA_diff = SWA_diff_list[fid]
        Ay_diff = Ay_diff_list[fid]
        yr = abs_yr[fid]

        Vx = Vx_light[fid]
        SWA2 = SWA_heavy_list[fid]
        fd = frac_drop[fid]
        os_level = get_oversteer_level(SWA_diff, Ay_diff, yr)
        us_level = get_understeer_level(fd)

        # TODO: add unstable event detection (section 3.5.1)

        if os_level >= os_thres:
            if Vx > 5 and Ay_diff > 0.1:
                num_oversteer += 1
                # print("OS @%d %.2f (SWA %.4f Ay %.4f AVz %.4f Vx %.4f)" %(
                    # fid, os_level, SWA_diff, Ay_diff, yr, Vx))
        if us_level >= us_thres:
            if Vx > 5 and SWA2 > 10:
                num_understeer += 1
                # print("US @%d %.2f (SA %.4f FD %.4f Vx %.4f)" %(
                    # fid, us_level, sa2, fd, Vx))



    ovs = int(num_oversteer)
    uds = int(num_understeer)
    deductions += ovs + uds

    print("ha:",ha)
    print("hb:",hb)
    print("ht:",ht)
    print("md:",md)
    print("ovs:",ovs)
    print("uds:",uds)
    print("score = ",deductions)
    return deductions