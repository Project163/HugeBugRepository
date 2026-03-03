#!/usr/bin/env python3
# framework/step2_clean_and_format.py
#
# 第二阶段：清洗与格式化 (Clean & Format)
# 目标：读取 extracted_data.jsonl，执行启发式去噪、长文本截断、Head-2+Tail-2 策略，
# 最终生成适用于 classify_bugs.py 大模型输入的 parsed_data.jsonl。

import os
import json
import argparse
import re

# ==========================================
# Configuration & Constants 
# ==========================================

# 社交噪音/无意义短语 (Stop Phrases)
LOW_VALUE_PHRASES = [
    "thanks", "thank you", "thx", "lgtm", "+1", "bump", 
    "great work", "awesome", "sent from my", "dupe", "duplicate"
]

HIGH_VALUE_KEYWORDS = [
    "fix", "patch", "bisect", "regression", "workaround", 
    "repro", "crash", "panic", "segfault", "assert", 
    "exception", "error", "fail", "root cause", "caused by"
]

class TextCleaner:
    @staticmethod
    def normalize_technical_data(text):
        """归一化技术数据，将高熵字符串替换为通用占位符"""
        if not text: return ""
        text = re.sub(r'\b0x[0-9a-fA-F]{4,}\b', '<PTR>', text)
        text = re.sub(r'\b[0-9a-fA-F]{16,}\b', '<HASH>', text)
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', text)
        return text

    @staticmethod
    def simplify_links(text):
        """智能简化链接和图片"""
        if not text: return ""
        def img_repl(match):
            alt = match.group(1).strip()
            return f"[Image: {alt}]" if alt else "[Image]"
        text = re.sub(r'!\[(.*?)\]\(.*?\)', img_repl, text)

        def link_repl(match):
            anchor_text = match.group(1).strip()
            url = match.group(2).strip()
            if anchor_text.startswith('http') and len(anchor_text) > 20:
                return "[Link]"
            if anchor_text.startswith('#') and len(anchor_text) < 10:
                return f"[Ref: {anchor_text}]"
            return f"[Link: {anchor_text}]" if anchor_text else "[Link]"
            
        text = re.sub(r'\[(.*?)\]\((.*?)\)', link_repl, text)
        text = re.sub(r'(?<![\[\(])https?://\S+', '[URL]', text)
        return text

    @staticmethod
    def remove_quotes(text):
        """移除引用文本，减少上下文冗余"""
        if not text: return ""
        lines = [line for line in text.split('\n') if not line.strip().startswith('>')]
        return '\n'.join(lines)

    @staticmethod
    def truncate_code_blocks(text, max_lines=8):
        """截断过长的代码块或日志"""
        if not text: return ""
        def replacement(match):
            content = match.group(1)
            lines = content.strip().split('\n')
            if len(lines) > max_lines:
                head = '\n'.join(lines[:5]) 
                tail = '\n'.join(lines[-2:])
                return f"```\n{head}\n... [Log Snipped] ...\n{tail}\n```"
            return match.group(0)
        return re.sub(r'```(.*?)```', replacement, text, flags=re.DOTALL)

    @staticmethod
    def clean(text):
        """整合清洗流程"""
        if not text: return ""
        text = TextCleaner.truncate_code_blocks(text)
        text = TextCleaner.remove_quotes(text)
        text = TextCleaner.simplify_links(text)
        text = TextCleaner.normalize_technical_data(text)
        text = re.sub(r'<[^>]+>', ' ', text) # 移除 HTML 标签
        text = re.sub(r'\n{3,}', '\n\n', text) # 合并多余换行
        return text.strip()

def is_useful_comment(text):
    """启发式过滤器：判断清洗后的文本是否对 LLM 分类有价值"""
    clean_t = text.lower().strip()
    if any(kw in clean_t for kw in HIGH_VALUE_KEYWORDS):
        return True
    if len(clean_t) < 60 and any(p in clean_t for p in LOW_VALUE_PHRASES):
        return False
    return len(clean_t) > 20

# ==========================================
# Formatting Logic
# ==========================================

def format_for_llm(title, description, comments_list):
    """
    构建 LLM 输入，应用 Head-2 + Tail-2 策略。
    这里的 comments_list 已经是拼接了 Author 的清洗后字符串列表。
    """
    # 限制 Description 的长度
    if len(description) > 2000:
        description = description[:2000] + "\n...[Description Truncated]..."
        
    llm_text = f"[Title]: {title}\n"
    llm_text += f"[Symptom]:\n{description}\n"
    
    if comments_list:
        # --- 核心修改：Head-2 + Tail-2 截断策略 ---
        if len(comments_list) > 4:
            # 保留前2条（症状澄清/初步尝试）
            head = comments_list[:2]
            # 保留后2条（最终结论/PR链接/修复确认）
            tail = comments_list[-2:]
            
            # 使用特定标记明确告知 LLM 中间有省略
            selected_comments = head + ["... [Middle Discussions Snipped for Brevity] ..."] + tail
        else:
            selected_comments = comments_list
        # ----------------------------------------

        discussion_text = "\n- ".join(selected_comments)
        
        # 安全网：如果剩下的这4条依然极其长，再做字符级截断
        if len(discussion_text) > 3000:
            head_text = discussion_text[:1500]
            tail_text = discussion_text[-1500:]
            discussion_text = f"{head_text}\n...[Text Truncated]...\n{tail_text}"
            
        llm_text += f"\n[Context/Logs]:\n- {discussion_text}"
        
    return llm_text

# ==========================================
# Main Processing Pipeline
# ==========================================

def main(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"[Error]: Input file not found: {input_file}")
        return

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    processed_count = 0
    skipped_count = 0

    print(f"--- Starting Data Cleaning & Formatting ---")
    print(f"Reading from: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
        for line_num, line in enumerate(f_in, 1):
            if not line.strip():
                continue
                
            try:
                record = json.loads(line)
                raw_data = record.get("raw_data", {})
                
                # 1. 清洗 Title
                clean_title = TextCleaner.clean(raw_data.get("title", ""))
                
                # 2. 清洗 Description
                clean_desc = TextCleaner.clean(raw_data.get("description", ""))
                
                # 3. 清洗并过滤 Comments，同时拼接 Author
                clean_comments = []
                for comment_obj in raw_data.get("comments", []):
                    author = comment_obj.get("author", "Unknown")
                    raw_body = comment_obj.get("body", "")
                    
                    clean_body = TextCleaner.clean(raw_body)
                    if clean_body and is_useful_comment(clean_body):
                        # 核心修改：将作者信息融合入有效评论中
                        clean_comments.append(f"[{author}]: {clean_body}")
                
                # 4. 如果连 Title 和 Description 都为空，则跳过
                if not clean_title and not clean_desc and not clean_comments:
                    skipped_count += 1
                    continue

                # 5. 组装 LLM 输入格式
                llm_input_text = format_for_llm(clean_title, clean_desc, clean_comments)
                
                # 6. 生成适用于 classify_bugs.py 的最终记录
                output_record = {
                    "project_id": record.get("project_id"),
                    "bug_id": record.get("bug_id"),
                    "source_type": record.get("source_type"),
                    "llm_input_text": llm_input_text
                }
                
                f_out.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                processed_count += 1
                
                if processed_count % 100 == 0:
                    print(f"  -> Processed {processed_count} records...")

            except json.JSONDecodeError:
                print(f"[Warning]: Line {line_num} is not valid JSON, skipping.")
            except Exception as e:
                print(f"[Error]: Failed processing line {line_num}: {e}")

    print(f"\n=================================================")
    print(f"Data Cleaning & Formatting Complete.")
    print(f"Processed: {processed_count} reports.")
    print(f"Skipped (Empty after cleaning): {skipped_count}")
    print(f"Output saved to: {output_file}")
    print(f"=================================================")

if __name__ == "__main__":
    DEFAULT_INPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'extracted_data.jsonl'))
    DEFAULT_OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'parsed_data.jsonl'))

    parser = argparse.ArgumentParser(description="Step 2 & 3: Clean raw JSONL data and format it for LLM classification.")
    parser.add_argument('-i', '--input_file', default=DEFAULT_INPUT_FILE, help="Path to raw_extracted_data.jsonl")
    parser.add_argument('-o', '--output_file', default=DEFAULT_OUTPUT_FILE, help="Path to parsed_data.jsonl")
    args = parser.parse_args()

    main(args.input_file, args.output_file)