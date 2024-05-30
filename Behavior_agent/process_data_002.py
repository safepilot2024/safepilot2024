from driving_quality import *

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