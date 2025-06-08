# Copyright (c) 2025 An Hongxu
# Peking University - School of Software and Microelectronics
# Email: anhongxu@stu.pku.edu.cn
#
# For academic use only. Commercial usage is prohibited without authorization.

# This script checks the consistency of blockchain data across multiple data nodes.

import os
from collections import defaultdict

def get_file_content(file_path):
    """读取文件内容并返回"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def compare_files(data_nodes):
    """比较所有 data_node 文件夹中的文件内容"""
    file_contents = [] 

    # 收集所有文件的内容
    for node in data_nodes:
        file_path = os.path.join(node, "blocks.json")
        if os.path.exists(file_path):
            content = get_file_content(file_path)
            file_contents.append(content)
        else:
            print(f"Warning: {file_path} does not exist.")

    # 比较文件内容
    all_consistent = True
    unique_contents = set(file_contents)
    if len(unique_contents) > 1:
        print(f"Inconsistent content found:")
        for i, content in enumerate(unique_contents):
            print(f"Version {i + 1}:")
            print(content)
        all_consistent = False

    if all_consistent:
        print("All files have consistent content across all data nodes.")
    else:
        print("Some files have inconsistent content.")

def main():
    # 获取当前目录下的所有 data_node 文件夹
    current_dir = os.getcwd()
    data_nodes = [os.path.join(current_dir, d) for d in os.listdir(current_dir) if d.startswith('data_node_')]
    print(f"Data nodes: {data_nodes}")

    if not data_nodes:
        print("No data_node folders found.")
        return

    compare_files(data_nodes)

if __name__ == "__main__":
    main()