import os
import json
import time
import requests
import math
from concurrent.futures import ThreadPoolExecutor


# 1. Configuration and Constants
# API Key
API_KEY = os.getenv("SILICONCLOUD_API_KEY")
if not API_KEY:
    raise ValueError("[Error]: Please set the 'SILICONCLOUD_API_KEY' environment variable")

API_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL_NAME = "BAAI/bge-m3"

WORK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification'))

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'cache'), exist_ok=True)

INPUT_FILE = os.path.abspath(os.path.join(WORK_DIR, 'parsed_data.jsonl'))
OUTPUT_FILE = os.path.abspath(os.path.join(WORK_DIR, 'classified_data_embedding.jsonl'))
CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cache', 'embedding_cache.json'))

MAX_WORKERS = 10
REQUEST_DELAY = 0.05

# Text truncation length
# Embedding models have a maximum token limit (BGE typically 8k tokens).
# If the text is too long (e.g., contains long stack traces), it can cause a 413 error.
# 20000 characters roughly correspond to 5000-8000 tokens, which is a safe value.
MAX_CHARS = 20000 


# 2. Fine-grained Label Definitions
LABEL_DESCRIPTIONS = {
    # --- 1. Function (Design/Logic) ---
    "Function :: Access Control (CWE-284)": 
        "Security issues where the application fails to restrict access to authorized users. Includes privilege escalation, permission bypass, and unauthorized actions.",
    
    "Function :: Logic Mismatch (CWE-573)": 
        "The implemented business logic does not match the requirements or specifications. Includes functional gaps, wrong workflows, or state transition errors.",

    # --- 2. Algorithm (Complexity/Math) ---
    "Algorithm :: Calculation Error (CWE-682)": 
        "Mathematical or arithmetic errors. Includes incorrect formulas, unit conversion mistakes, integer overflow results, or logic operator misuse.",
    
    "Algorithm :: Resource/Memory Leak (CWE-400)": 
        "Performance issues caused by uncontrolled resource consumption. Includes memory leaks, infinite loops, CPU spikes, and inefficient algorithms.",

    # --- 3. Checking (Validation/Bounds) ---
    "Checking :: Input Validation (CWE-20)": 
        "Failure to validate or sanitize input data. Includes injection attacks (SQLi, XSS), format string errors, and processing of malformed data.",
    
    "Checking :: Boundary/Buffer (CWE-119)": 
        "Memory corruption or access issues. Includes buffer overflows, index out of bounds (IOOB), and accessing memory outside intended limits.",
    
    "Checking :: Missing Check (CWE-754)": 
        "Failure to check for unusual or exceptional conditions. Specifically includes Null Pointer Dereference (NPE), uncaught exceptions, and missing return value checks.",

    # --- 4. Assignment (Values/Types) ---
    "Assignment :: Initialization (CWE-665)": 
        "Variables, objects, or resources are not properly initialized before use. Includes using wrong default values or configuration loading failures.",
    
    "Assignment :: Type/Cast Error (CWE-704)": 
        "Errors involving incorrect data type conversions. Includes casting failures (ClassCastException), integer truncation, or unexpected type mismatches.",

    # --- 5. Interface (API/Data Flow) ---
    "Interface :: API Misuse (CWE-628)": 
        "Incorrect use of internal or external APIs. Includes passing arguments in the wrong order, wrong argument count, or calling methods incorrectly.",
    
    "Interface :: Data Encoding (CWE-707)": 
        "Issues with data format translation between systems. Includes JSON/XML parsing errors, serialization failures, and improper character encoding/escaping.",

    # --- 6. Timing (Concurrency) ---
    "Timing :: Race Condition (CWE-362)": 
        "Concurrency issues where the outcome depends on the timing of threads or processes. Includes race conditions, interference, and synchronization failures.",
    
    "Timing :: Resource Lifecycle (CWE-664)": 
        "Improper management of a resource's lifecycle. Includes double-freeing memory, use-after-free, and failing to release locks or file handles (deadlocks).",

    # --- 7. Build (Config/Deps) ---
    "Build :: Configuration (CWE-16)": 
        "Issues arising from improper environmental configuration. Includes wrong environment variables, hardcoded credentials, or deployment setting errors.",
    
    "Build :: Dependency (CWE-1357)": 
        "Problems related to third-party libraries. Includes version conflicts, missing gems/npm packages, or vulnerable supply chain dependencies.",

    # --- 8. Documentation ---
    "Documentation :: Wrong Comments (CWE-1116)": 
        "Discrepancies between the code and its comments or documentation. Includes typos in UI text, outdated API docs, or misleading instructions.",

    # --- Fallback ---
    "Other": 
        "A generic defect that does not fit clearly into the standard ODC or CWE categories, or lacks sufficient information to classify."
}

# 3. Utility Functions
def get_embedding(text):
    """
    Call API to get the embedding vector for the given text.
    """
    if not text:
        return None

    # If the text is too long, truncate it to the first MAX_CHARS characters
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    # Preprocessing: remove newline characters
    cleaned_text = text.replace("\n", " ").strip()
    
    payload = {
        "model": MODEL_NAME,
        "input": cleaned_text,
        "encoding_format": "float"
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 413:
            print(f"[Error]: 413, Text is still too long. Current length: {len(cleaned_text)}")
            return None

        response.raise_for_status()
        data = response.json()
        return data['data'][0]['embedding']
    except Exception as e:
        print(f"Embedding API Error: {e}")
        return None

def cosine_similarity(v1, v2):
    """
    Calculate the cosine similarity between two vectors.
    """
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

def load_cache():
    """Load embedding cache from local file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning]: Failed to load cache file: {e}")
    return {}

def save_cache(cache_data):
    """Save cache to local file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"Updated label embedding cache: {CACHE_FILE}")
    except Exception as e:
        print(f"[Error] Failed to save cache: {e}")

# 4. Main Logic
def get_label_embeddings_with_cache():
    """
    Get embeddings for all labels.
    Prefer using cache; if description changes or no cache, call API to compute.
    """
    print("Preparing label embeddings...")
    
    # 1. Load existing cache
    cache = load_cache()
    embeddings = {}
    cache_updated = False
    
    # 2. Iterate over the labels defined in the current code
    print(f"Checking {len(LABEL_DESCRIPTIONS)} label definitions...")
    
    for label, description in LABEL_DESCRIPTIONS.items():
        # Check if the label exists in cache and the description matches
        if label in cache and cache[label].get('description') == description:
            # Cache hit
            embeddings[label] = cache[label]['vector']
        else:
            # Cache miss (new label or description changed), need to recompute
            status = "Description updated" if label in cache else "New label"
            print(f"  - [{status}] Computing vector: {label}")
            
            vec = get_embedding(description)
            if vec:
                embeddings[label] = vec
                # Update cache structure
                cache[label] = {
                    'description': description,
                    'vector': vec
                }
                cache_updated = True
                time.sleep(0.1)
            else:
                print(f"  - [Error] Failed to generate vector: {label}")

    # 3. Clean up deleted labels (if a label is removed from the code, it should also be removed from the cache)
    current_keys = set(LABEL_DESCRIPTIONS.keys())
    cached_keys = set(cache.keys())
    deprecated_keys = cached_keys - current_keys
    
    if deprecated_keys:
        print(f"  - Cleaning up {len(deprecated_keys)} deprecated cache labels...")
        for k in deprecated_keys:
            del cache[k]
        cache_updated = True

    # 4. If there are updates, write back to disk
    if cache_updated:
        save_cache(cache)
    else:
        print("All labels hit the cache, no need to call the API.")
        
    return embeddings

def classify_bug_vector(bug_vec, label_embeddings):
    best_label = "Other"
    best_score = -1.0

    for label, label_vec in label_embeddings.items():
        score = cosine_similarity(bug_vec, label_vec)
        if score > best_score:
            best_score = score
            best_label = label
            
    return best_label, best_score

def process_line(line_data, label_embeddings):
    """
    Process a single line of data
    """
    bug_text = line_data.get("llm_input_text", "")
    if not bug_text:
        return None

    bug_vec = get_embedding(bug_text)
    if not bug_vec:
        return "Error"

    predicted_label, score = classify_bug_vector(bug_vec, label_embeddings)
    return predicted_label

def main():
    label_embeddings = get_label_embeddings_with_cache()

    if not label_embeddings:
        print("[Error]: Unable to generate label embeddings.")
        return

    print("-" * 50)
    print(f"Label embeddings ready, starting to process {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"[Error]: File not found {INPUT_FILE}")
        return

    print(f"There are {len(lines)} lines of data to process.")

    # Create a list to store (original data, Future object)
    # This way can iterate in the original order when writing results
    tasks = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 1. Submit all tasks
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                future = executor.submit(process_line, data, label_embeddings)
                tasks.append((data, future))
            except json.JSONDecodeError:
                print(f"Line {i+1} JSON error")
                # If JSON parsing fails, we add None to the task list to keep index alignment (or ignore directly)
                # For simplicity, ignore the line and do not add to tasks

        print("All tasks submitted, waiting for results and writing in order...")

        # 2. Get results in order and write
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
            processed_count = 0
            
            for original_data, future in tasks:
                # future.result() will block until the specific task is completed
                # This ensures it process results in the order of the tasks list
                predicted_label = future.result()
                
                if predicted_label:
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
                    print(f"Processed: {processed_count}/{len(tasks)}")
                
                # Simple rate control
                time.sleep(REQUEST_DELAY)

    print(f"Processing complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()