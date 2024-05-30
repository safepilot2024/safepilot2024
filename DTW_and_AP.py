#这个代码最终聚类结果可视化为轨迹

import os
import json
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from sklearn.cluster import AffinityPropagation
import numpy as np
import matplotlib.pyplot as plt


# 载入所有json文件
def load_json_files(directory):
    all_trajectories = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename), 'r') as file:
                data = json.load(file)
                attacker_locations = data.get('attacker_location', [])
                # 去除重复项
                filtered_locations = [list(x) for i, x in enumerate(attacker_locations) if i == 0 or x != attacker_locations[i - 1]]
                all_trajectories.append(filtered_locations)
    return all_trajectories

# 计算DTW距离矩阵
def compute_dtw_matrix(trajectories):
    n = len(trajectories)
    dtw_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            distance, _ = fastdtw(trajectories[i], trajectories[j], dist=euclidean)
            dtw_matrix[i, j] = dtw_matrix[j, i] = distance
    return dtw_matrix

# 进行AP聚类
def perform_ap_clustering(dtw_matrix):
    clustering = AffinityPropagation(affinity='precomputed')
    labels = clustering.fit_predict(-dtw_matrix)  # 使用负距离因为AP算法是寻找最大相似度
    return labels

# 可视化聚类结果
def visualize_clusters(trajectories, labels):
    plt.figure(figsize=(10, 6))
    colors = plt.cm.rainbow(np.linspace(0, 1, len(set(labels))))
    for traj, label in zip(trajectories, labels):
        traj = np.array(traj)
        plt.plot(traj[:, 0], traj[:, 1], marker='o', color=colors[label])
    plt.title('Clustered Trajectories')
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.show()

# 主函数
def main():
    directory = '/home/test/文档/CarlaData010/M001/log/success'
    trajectories = load_json_files(directory)
    if trajectories:
        dtw_matrix = compute_dtw_matrix(trajectories)
        labels = perform_ap_clustering(dtw_matrix)
        print("Clustering labels:", labels)
        visualize_clusters(trajectories, labels)
    else:
        print("No JSON files found or no data available in files.")

if __name__ == "__main__":
    main()
