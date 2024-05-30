def candidate_command_generation(counter, guide):
    # Define range sets for two cars
    directions = [(0.1, 0.4), (-0.1, 0.1), (-0.4, -0.1)]
    thros = [(-1/3, 1/3), (1/3, 1), (-1, -1/3)]

    # Define range of directions and throttle based on the guide
    dir_range = range(0, 2) if guide[0] > 0 else range(1, 3)
    thro_range = range(1, 3) if guide[1] > 0 else range(0, 2)

    # Generate initial population
    population_size = 10
    population = []
    for _ in range(population_size):
        command = []
        for i in dir_range:
            for j in thro_range:
                dir_sample = random.uniform(directions[i][0], directions[i][1])
                thro_sample = random.uniform(thros[j][0], thros[j][1])
                command.append((thro_sample, dir_sample))
        population.append(command)

    # Evaluate fitness for each candidate command
    fitness_scores = [evaluate_fitness(cmd) for cmd in population]

    # Select top candidates based on fitness scores
    num_selected = 5
    selected_indices = np.argsort(fitness_scores)[:num_selected]
    selected_population = [population[i] for i in selected_indices]

    # Shuffle and return selected population
    random.shuffle(selected_population)
    return selected_population




def command_generation(counter, guide, history_commands, world, attacker, victim, npc, map, spectator, agent, weather, victim_pos, attacker_pos, original_attack_vehicle_model, original_victim_vehicle_model, npc_vheicle_model, npc_vehicle_pos):
    candidate_attacker_commands = candidate_command_generation(counter, guide)
    command_robustness = []
    rewind_details = []
    global REWIND

    for command in candidate_attacker_commands:
        print("\033[93m<<<<<Command:", command, ">>>>>\033[0m")
        attacker, victim, agent, npc = rewind_scene(world, weather, attacker, victim, npc, agent, history_commands, spectator, victim_pos, attacker_pos, original_attack_vehicle_model, original_victim_vehicle_model, npc_vheicle_model, npc_vehicle_pos)
        rewind_flag = exec_command(attacker, agent, victim, spectator, command, world)

        if not rewind_flag:
            command_robustness.append(robustness_calculation(victim, npc, map, TTC=True))
        if ATTACK_SUCCESS:
            return command, attacker, victim, npc, rewind_details
        if REWIND:
            rewind_details.append("round: " + str(len(history_commands)) + "\n Reason: attacker break the law!")
            REWIND = False
        else:
            rewind_details.append("round: " + str(len(history_commands)) + "\n Reason: violate physical constraints")

    if not command_robustness:
        return candidate_attacker_commands[0], attacker, victim, rewind_details

    min_robustness_index = command_robustness.index(min(command_robustness))
    return candidate_attacker_commands[min_robustness_index], attacker, victim, agent, rewind_details, npc


def trajectory_generation(world, attacker, victim, npc, spectator, agent, weather, victim_pos, attacker_pos, original_attack_vehicle_model, original_victim_vehicle_model, npc_vheicle_model, npc_vehicle_pos):
    trajectory = [get_state(attacker)]
    vic_traj, att_traj = [get_state(victim)], [get_state(attacker)]
    attack_commands = []
    rewinding_details = []
    counter = 0
    guide = (1, -1)
    global ATTACK_SUCCESS, COLLISION_OBJECT

    while not ATTACK_SUCCESS and counter < 5:
        print("\033[92m>>>>This is counter {}\033[0m".format(counter))
        command, attacker, victim, agent, rewind_details, npc = command_generation(counter, guide, attack_commands, world, attacker, victim, npc, map, spectator, agent, weather, victim_pos, attacker_pos, original_attack_vehicle_model, original_victim_vehicle_model, npc_vheicle_model, npc_vehicle_pos)
        rewinding_details.append(rewind_details)

        print(">>>Exec commands with lowest robustness:", command)
        exec_command(attacker, agent, victim, spectator, command, world)
        trajectory.append(get_state(attacker))
        attack_commands.append(command)

        if counter > 0:
            guide = [trajectory[counter][0] - trajectory[counter - 1][0], trajectory[counter][1] - trajectory[counter - 1][1]]

        print("\033[92m>>>>Finish counter {}\033[0m".format(counter))
        counter += 1
        time.sleep(1)

    print(trajectory)
