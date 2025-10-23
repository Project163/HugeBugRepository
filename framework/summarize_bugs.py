#!/usr/bin/env python3
# framework/summarize_bugs.py
#
# 该脚本用于扫描 bug-mining/ 目录下的所有项目,
# 并生成一个汇总的 CSV 文件, 包含每个项目的缺陷数量和缺陷ID列表。

import os
import csv
import re
import sys
try:
    import config
except ImportError:
    print("Error: 无法导入 config.py。请确保此脚本与 config.py 在同一目录中。", file=sys.stderr)
    sys.exit(1)

def main():
    # --- 1. 定义路径 ---
    
    # SCRIPT_DIR 是 framework/ 目录
    SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # BUG_MINING_DIR 是 ../bug-mining/
    BUG_MINING_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'bug-mining'))
    
    # OUTPUT_CSV 是 ../bug_summary.csv (即 HugeBugRepository/bug_summary.csv)
    OUTPUT_CSV = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'bug_summary.csv'))
    
    # 从 config.py 获取 report.id 列的名称 (例如 "report.id")
    # 这是您要求提取数字的列 (例如 "BSF-1")
    ISSUE_ID_COLUMN = config.BUGS_CSV_ISSUE_ID

    print(f"扫描目标目录: {BUG_MINING_DIR}")

    if not os.path.exists(BUG_MINING_DIR):
        print(f"Error: 目录未找到: {BUG_MINING_DIR}", file=sys.stderr)
        print("请先运行 fast_bug_miner.py 来生成 bug-mining 目录。", file=sys.stderr)
        sys.exit(1)

    all_project_stats = []

    # --- 2. 遍历 bug-mining 目录 ---
    for project_id in sorted(os.listdir(BUG_MINING_DIR)):
        project_path = os.path.join(BUG_MINING_DIR, project_id)
        
        # 确保只处理目录 (例如 Bsf/, Lang/)
        if not os.path.isdir(project_path):
            continue

        csv_path = os.path.join(project_path, 'active-bugs.csv')
        
        # 检查 active-bugs.csv 是否存在
        if os.path.exists(csv_path):
            print(f"  -> 正在处理: {project_id}")
            bug_count = 0
            issue_ids = []

            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    
                    # 读取表头
                    try:
                        header = next(reader)
                    except StopIteration:
                        print(f"     [Warning] {project_id} 的 active-bugs.csv 是空的, 已跳过。")
                        continue
                        
                    # 查找 "report.id" 列的索引
                    try:
                        id_index = header.index(ISSUE_ID_COLUMN)
                    except ValueError:
                        print(f"     [Error] {project_id} 的 CSV 文件中未找到列: '{ISSUE_ID_COLUMN}', 已跳过。", file=sys.stderr)
                        continue

                    # 遍历所有数据行
                    for row in reader:
                        if not row or len(row) <= id_index:
                            continue
                            
                        bug_count += 1
                        report_id = row[id_index] # 例如 "BSF-1"
                        
                        # 提取数字部分
                        match = re.search(r'\d+', report_id)
                        if match:
                            issue_ids.append(match.group(0)) # "1"
                        else:
                            # 如果没有数字 (例如 "NA" 或其他格式), 则添加原始字符串
                            issue_ids.append(report_id)

                if bug_count > 0:
                    # 将 [1, 5, 10] 转换为 "1,5,10"
                    issue_ids_str = ",".join(issue_ids)
                    all_project_stats.append([project_id, bug_count, issue_ids_str])
                else:
                    print(f"     [Info] {project_id} 已处理, 但未找到缺陷行。")

            except Exception as e:
                print(f"     [Error] 处理 {project_id} 时发生错误: {e}", file=sys.stderr)

        else:
            print(f"  -> 跳过 {project_id} (未找到 active-bugs.csv)")

    # --- 3. 写入汇总的 CSV 文件 ---
    if not all_project_stats:
        print("未找到任何项目数据, 汇总文件未生成。")
        return

    print(f"\n正在将汇总数据写入: {OUTPUT_CSV}")

    try:
        with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(["project_id", "bug_count", "issue_ids"])
            # 写入所有项目的数据
            writer.writerows(all_project_stats)
    except IOError as e:
        print(f"Error: 无法写入汇总文件: {e}", file=sys.stderr)
        sys.exit(1)

    print("汇总完成。")

if __name__ == "__main__":
    main()