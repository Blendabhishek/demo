# Explanation of the Steps:
# Step 1: get_latest_commit_hash(): Fetches the latest commit hash of the specified branch (either main or master).
# Step 2: get_previous_commit_hash(): Fetches the previous commit hash by looking at the last two commits on the branch.
# Step 3: compare_commits(): Compares the latest commit with the previous one. If they differ, it means changes have been detected.
# Step 4: get_changed_files(): Fetches the list of files that have been added, modified, or removed between the two commits.
# Step 5: fetch_file_content(): Fetches the content of the changed files using the GitHub API, decodes them from base64, and prints the first 200 characters for preview.


import os
import requests
import base64
from sentence_transformers import SentenceTransformer
import chromadb

# GitHub API settings
GITHUB_TOKEN = "Your API TOKEN "
REPO_OWNER = "Repo Name"  # e.g., "octocat"
REPO_NAME = "demo"    # e.g., "Hello-World"
BRANCH_NAME = "master"  # Or "master" if you're using that
HASH_FILE = os.path.join(os.path.dirname(__file__), "previous_commit_hash.txt")

# Initialize ChromaDB client and embedding model
client = chromadb.Client()
collection = client.get_or_create_collection("file_vectors")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Helper function to read the last processed commit hash
def read_previous_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return None

# Helper function to store the latest processed commit hash
def write_previous_hash(commit_hash):
    with open(HASH_FILE, "w") as f:
        f.write(commit_hash)

# Function to fetch the latest commit hash from GitHub
def get_latest_commit_hash():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {"sha": BRANCH_NAME, "per_page": 1}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if len(data) > 0:
            return data[0]["sha"]
    else:
        print(f"Failed to fetch latest commit hash: {response.status_code}")
    return None

# Function to fetch changes between two commits
def get_commit_diff(base_commit, head_commit):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{base_commit}...{head_commit}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch commit diff: {response.status_code}")
    return None

# Function to process changed files
def process_changes(changed_files):
    for file in changed_files:
        file_name = file["filename"]
        file_status = file["status"]
        if file_status in ["added", "modified"]:
            print(f"Processing file: {file_name} (Status: {file_status})")
            content_url = file["contents_url"]
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            response = requests.get(content_url, headers=headers)
            if response.status_code == 200:
                file_content = response.json().get("content", "")
                file_content_decoded = base64.b64decode(file_content).decode("utf-8")
                print(f"Content of {file_name}:\n{file_content_decoded}")

                # Generate embeddings and upsert to ChromaDB
                embedding = model.encode(file_content_decoded)
                collection.add(
                    documents=[file_content_decoded],
                    metadatas=[{"file_name": file_name}],
                    ids=[file_name],
                    embeddings=[embedding],
                )
                print(f"File {file_name} upserted to vector DB.")
            else:
                print(f"Failed to fetch content for {file_name}.")
        else:
            print(f"Skipping file: {file_name} (Status: {file_status})")

# Main function to sync changes
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
    diff = get_commit_diff(previous_commit_hash, latest_commit_hash)

    if diff and "files" in diff:
        changed_files = diff["files"]
        process_changes(changed_files)
        write_previous_hash(latest_commit_hash)
    else:
        print("No file changes detected.")

# Run the sync process
if __name__ == "__main__":
    sync_with_vector_db()
