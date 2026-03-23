import os
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# 1. Configuration
# API Key
api_key = os.getenv("SILICONCLOUD_API_KEY")
if not api_key:
    raise ValueError("Please set the 'SILICONCLOUD_API_KEY' environment variable")

# Initialize OpenAI client pointing to Qwen's compatible API
client = OpenAI(
    api_key="sk-ntvcxmzcntxtxulhfudigidspmbdasfqxvtbukereyljbghc",
    base_url="https://api.siliconflow.cn/v1",
)

# Labels to classify
DEFAULT_LABELS = [
    "Crash/UnhandledException", "Crash/NullPointer", "Crash/Memory", "Stability/Freeze",
    "UI/Layout", "UI/Visual", "UI/Responsive", "UX/Navigation", "Accessibility",
    "Logic/Calculation", "Logic/Workflow", "Data/Corruption", "Data/Format", "Network/Timeout", "Network/APIError", "Connectivity",
    "Build/Dependency", "Env/Compatibility", "Dev/Test",
    "Text/Typo", "Docs/Missing",
    "Security/Auth", "Security/Vulnerability",
    "Other"
]
LABELS_STRING = ", ".join(DEFAULT_LABELS)

# Input and output files
INPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'parsed_data.jsonl'))
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'classified_data_llm.jsonl'))

# Concurrency settings
MAX_WORKERS = 2  # Drastically reduced from 10 to avoid rate limits
REQUEST_DELAY = 1.0  # Increased delay between requests

# 2. System Prompt
SYSTEM_PROMPT = f"""
You are an expert software engineer specializing in bug triaging and classification.
Your task is to classify bug reports into one of the following categories based on their content:
{LABELS_STRING}
When classifying, consider the main issue described in the bug report.
Respond with only the exact label name from the list above.
If the bug does not clearly fit into any category, classify it as 'Other'.
Do not provide any explanations or additional text—only return the label.
Example1:
Bug Report: "The application crashes when I try to upload a large file."
Classification: "Crash/Exception"
Example2:
Bug Report: "The UI freezes when loading the dashboard."
Classification: "UI/UX"
Example3:
Bug Report: "There is a typo in the settings menu."
Classification: "Typo"
Remember to respond with only the label name.
"""

# 3. API Call Function
def get_bug_classification(bug_text):
    """
    Call API to classify a single bug text.
    """
    max_retries = 5  # Maximum number of retries
    retry_delay = 5  # Initial retry delay in seconds

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct",  
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": bug_text}
                ],
                temperature=0,
            )
            
            # Extract the raw label returned by the model
            raw_label = completion.choices[0].message.content.strip()
            
            # Validate if the returned label is in our list
            if raw_label in DEFAULT_LABELS:
                return raw_label
            else:
                for label in DEFAULT_LABELS:
                    if label in raw_label:
                        return label
                return "Other"
                
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"[Warning] Rate limited. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            elif attempt == max_retries - 1:
                # If it's the last attempt and still failing
                print(f"[Error]: API call failed after {max_retries} attempts: {e}")
                return "Error"
            else:
                 # Other errors, maybe network glitch, retry a bit
                 print(f"[Warning] API call failed: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
                 time.sleep(retry_delay)

    return "Error"


# 4. Main Processing Logic
def process_bug_file():
    print(f"Processing {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"[Error]: Input file {INPUT_FILE} not found.")
        return
        
    print(f"Found a total of {len(lines)} bug reports.")

    # List to store (original data, Future object) in order
    tasks = []

    # Use ThreadPoolExecutor to submit tasks
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 1. Submit all tasks
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                bug_text = data.get("llm_input_text")
                
                if bug_text:
                    future = executor.submit(get_bug_classification, bug_text)
                    # Store the original data and future together to maintain order
                    tasks.append((data, future))
                else:
                    print(f"Line {i+1} missing 'llm_input_text', skipping.")
            except json.JSONDecodeError:
                print(f"Line {i+1} JSON decode error, skipping.")

        print("All tasks submitted, waiting for results and writing in order...")
        # 2. Retrieve results in order and write
        # The key here is to iterate over the `tasks` list we created, rather than using as_completed
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
            processed_count = 0
            
            for original_data, future in tasks:
                predicted_label = future.result()

                new_data = {
                    "project_id": original_data.get("project_id"),
                    "bug_id": original_data.get("bug_id"),
                    "source_type": original_data.get("source_type"),
                    "label": predicted_label,
                    "llm_input_text": original_data.get("llm_input_text")
                }
                
                outfile.write(json.dumps(new_data, ensure_ascii=False) + '\n')
                
                processed_count += 1
                if processed_count % 10 == 0:
                    print(f"Processed {processed_count}/{len(tasks)} records...")
                
                # Avoid rate limiting due to high concurrency
                time.sleep(REQUEST_DELAY)

    print(f"Processing completed!")
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_bug_file()