#!/usr/bin/env python3
# framework/step1_extract_reports.py
#
# 第一阶段：提取与标准化 (Extract & Normalize)
# 目标：从 bug-mining/ 的异构报告中无损提取标题、描述和评论（包含作者信息），生成高保真的统一 JSON 结构。

import os
import json
import argparse
from bs4 import BeautifulSoup
import re

def extract_jira_xml(xml_content):
    """提取 Jira XML 数据（无损，包含作者）"""
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        item_node = soup.find('item')
        if not item_node:
            return None
            
        title_node = item_node.find('summary')
        title = title_node.get_text() if title_node else ""
        
        desc_node = item_node.find('description')
        description = desc_node.get_text() if desc_node else ""
        
        comments = []
        for comment in item_node.find_all('comment'):
            raw_body = comment.get_text()
            # 获取 author 属性，若不存在则默认为 Unknown
            author = comment.get('author', 'Unknown') 
            
            if raw_body:
                # 升级为结构化字典
                comments.append({
                    "author": author,
                    "body": raw_body
                })
                
        return {
            "title": title,
            "description": description,
            "comments": comments
        }
    except Exception as e:
        print(f"[Warning]: Failed to parse Jira XML: {e}")
        return None

def extract_github_json(report_json, timeline_json):
    """提取 GitHub JSON 数据（无损，包含作者，保留原有的 Bot 过滤逻辑）"""
    try:
        title = report_json.get('title', '')
        description = report_json.get('body', '') or ""
        
        comments = []
        if timeline_json:
            for event in timeline_json:
                if event.get('event') == 'commented' and event.get('body'):
                    raw_body = event['body']
                    
                    # 优先尝试从 actor 获取，其次从 user 获取
                    author = event.get('user', {}).get('login') or event.get('actor', {}).get('login') or 'Unknown'
                    
                    # 继承原有的基础过滤：排除无意义的 Bot 纯干扰回复
                    if 'bot' in author.lower() and 'fail' not in raw_body.lower():
                        continue
                        
                    comments.append({
                        "author": author,
                        "body": raw_body
                    })
                    
        return {
            "title": title,
            "description": description,
            "comments": comments
        }
    except Exception as e:
        print(f"[Warning]: Failed to parse GitHub JSON: {e}")
        return None

def extract_google_json(report_json):
    """提取 Google Code JSON 数据（无损，包含作者）"""
    try:
        title = report_json.get('summary', '')
        all_comments = report_json.get('comments', [])
        
        description = ""
        comments = []
        
        if all_comments:
            # Google Code 的第一个 comment 通常是 Issue 的 Description
            description = all_comments[0].get('content', '')
            if len(all_comments) > 1:
                for comment in all_comments[1:]:
                    raw_body = comment.get('content', '')
                    # 提取 commenterId
                    author = str(comment.get('commenterId', 'Unknown'))
                    
                    if raw_body:
                        comments.append({
                            "author": author,
                            "body": raw_body
                        })
                        
        return {
            "title": title,
            "description": description,
            "comments": comments
        }
    except Exception as e:
        print(f"[Warning]: Failed to parse Google JSON: {e}")
        return None

def main(bug_mining_root, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    processed_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        project_ids = sorted([d for d in os.listdir(bug_mining_root) if os.path.isdir(os.path.join(bug_mining_root, d))])
        
        for project_id in project_ids:
            project_dir = os.path.join(bug_mining_root, project_id)
            reports_dir = os.path.join(project_dir, 'reports')
            
            if not os.path.isdir(reports_dir):
                continue
                
            print(f"--- Extracting Project: {project_id} ---")
            files = os.listdir(reports_dir)
            report_files = {} 
            
            for file in files:
                match = re.match(r'(\d+)(\.timeline)?\.(json|xml)', file)
                if not match: continue
                bug_id = match.group(1)
                is_timeline = bool(match.group(2))
                ext = match.group(3)
                
                if bug_id not in report_files:
                    report_files[bug_id] = {'report': None, 'timeline': None, 'ext': None}
                    
                if is_timeline:
                    report_files[bug_id]['timeline'] = os.path.join(reports_dir, file)
                else:
                    report_files[bug_id]['report'] = os.path.join(reports_dir, file)
                    report_files[bug_id]['ext'] = ext

            for bug_id in sorted(report_files.keys(), key=int):
                paths = report_files[bug_id]
                if not paths['report']: continue
                
                raw_extracted_data = None
                source_type = "unknown"
                
                try:
                    if paths['ext'] == 'xml':
                        source_type = "jira"
                        with open(paths['report'], 'r', encoding='utf-8') as f:
                            raw_extracted_data = extract_jira_xml(f.read())
                            
                    elif paths['ext'] == 'json':
                        with open(paths['report'], 'r', encoding='utf-8') as f_rep:
                            report_data = json.load(f_rep)
                            
                        if paths['timeline']: 
                            source_type = "github"
                            with open(paths['timeline'], 'r', encoding='utf-8') as f_time:
                                timeline_data = json.load(f_time)
                            raw_extracted_data = extract_github_json(report_data, timeline_data)
                        else:
                            source_type = "google"
                            raw_extracted_data = extract_google_json(report_data)
                            
                    if raw_extracted_data:
                        output_record = {
                            "project_id": project_id,
                            "bug_id": bug_id,
                            "source_type": source_type,
                            "raw_data": raw_extracted_data
                        }
                        f_out.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                        processed_count += 1
                        
                except Exception as e:
                    print(f"[Error] Failed extracting {project_id}/{bug_id} ({paths['report']}): {e}")

    print(f"\n=================================================")
    print(f"Extraction complete. Processed {processed_count} reports.")
    print(f"Output saved to: {output_file}")
    print(f"=================================================")

if __name__ == "__main__":
    DEFAULT_BUG_MINING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug-mining'))
    DEFAULT_OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'extracted_data.jsonl'))

    parser = argparse.ArgumentParser(description="Step 1: Extract bug reports into a unified, raw JSONL format (with Author).")
    parser.add_argument('-i', '--input_dir', default=DEFAULT_BUG_MINING_DIR)
    parser.add_argument('-o', '--output_file', default=DEFAULT_OUTPUT_FILE)
    args = parser.parse_args()

    main(args.input_dir, args.output_file)