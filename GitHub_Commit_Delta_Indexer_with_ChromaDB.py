import os
import requests
import base64
from sentence_transformers import SentenceTransformer
import chromadb
import warnings
from datetime import datetime
warnings.filterwarnings("ignore")

# GitHub API settings
GITHUB_TOKEN = ""  # Replace with your GitHub token
REPO_OWNER = "Blendabhishek"
REPO_NAME = "demo"
BRANCH_NAME = "master"
HASH_FILE = os.path.join(os.path.dirname(__file__), "previous_commit_hash.txt")

# Initialize ChromaDB client and embedding model
client = chromadb.Client()
collection = client.get_or_create_collection("commit_delta_vectors")
model = SentenceTransformer('all-MiniLM-L6-v2')

def read_previous_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return None

def write_previous_hash(commit_hash):
    with open(HASH_FILE, "w") as f:
        f.write(commit_hash)

def get_latest_commit_hash():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {"sha": BRANCH_NAME, "per_page": 1}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data[0]["sha"] if data else None
    print(f"Failed to fetch latest commit hash: {response.status_code}")
    return None

def get_commit_diff(base_commit, head_commit):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{base_commit}...{head_commit}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    print(f"Failed to fetch commit diff: {response.status_code}")
    return None

def process_file_delta(file):
    """Extract and format the delta information from a file change"""
    delta_info = {
        'filename': file['filename'],
        'status': file['status'],
        'additions': file['additions'],
        'deletions': file['deletions'],
        'changes': file['changes'],
        'patch': file.get('patch', ''),
    }
    return delta_info

def process_changes(changed_files, commit_info):
    """Process each changed file and store its delta information"""
    timestamp = datetime.now().isoformat()
    
    for file in changed_files:
        delta_info = process_file_delta(file)
        
        # Create a comprehensive delta description
        delta_description = f"""
        File: {delta_info['filename']}
        Status: {delta_info['status']}
        Changes: +{delta_info['additions']} -{delta_info['deletions']}
        
        Patch:
        {delta_info['patch']}
        
        Commit Message: {commit_info.get('commit', {}).get('message', 'No message provided')}
        """
        
        # Generate a unique ID for this delta
        delta_id = f"{commit_info['sha'][:8]}_{delta_info['filename']}"
        
        # Generate embeddings for the delta description
        embedding = model.encode(delta_description).tolist()
        
        # Store metadata about the change
        metadata = {
            'filename': delta_info['filename'],
            'commit_sha': commit_info['sha'],
            'status': delta_info['status'],
            'additions': delta_info['additions'],
            'deletions': delta_info['deletions'],
            'timestamp': timestamp,
            'author': commit_info.get('commit', {}).get('author', {}).get('name', 'Unknown'),
            'commit_message': commit_info.get('commit', {}).get('message', 'No message provided')
        }
        
        # Add to ChromaDB
        collection.add(
            documents=[delta_description],
            metadatas=[metadata],
            ids=[delta_id],
            embeddings=[embedding]
        )
        
        print(f"Indexed delta for {delta_info['filename']} (Commit: {commit_info['sha'][:8]})")

def get_commit_info(commit_sha):
    """Fetch detailed information about a specific commit"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{commit_sha}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def sync_with_vector_db():
    previous_commit_hash = read_previous_hash()
    latest_commit_hash = get_latest_commit_hash()

    if not latest_commit_hash:
        print("Could not fetch the latest commit hash. Exiting...")
        return

    if not previous_commit_hash:
        print(f"Initial run detected. Setting commit hash to {latest_commit_hash}.")
        write_previous_hash(latest_commit_hash)
        return

    if previous_commit_hash == latest_commit_hash:
        print("No new changes detected. Exiting...")
        return

    print(f"Changes detected between {previous_commit_hash} and {latest_commit_hash}.")
    
    # Get the diff and commit information
    diff = get_commit_diff(previous_commit_hash, latest_commit_hash)
    commit_info = get_commit_info(latest_commit_hash)

    if diff and "files" in diff:
        changed_files = diff["files"]
        process_changes(changed_files, commit_info)
        write_previous_hash(latest_commit_hash)
    else:
        print("No file changes detected.")

if __name__ == "__main__":
    sync_with_vector_db()