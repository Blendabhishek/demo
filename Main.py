# Explanation of the Steps:
# Step 1: get_latest_commit_hash(): Fetches the latest commit hash of the specified branch (either main or master).
# Step 2: get_previous_commit_hash(): Fetches the previous commit hash by looking at the last two commits on the branch.
# Step 3: compare_commits(): Compares the latest commit with the previous one. If they differ, it means changes have been detected.
# Step 4: get_changed_files(): Fetches the list of files that have been added, modified, or removed between the two commits.
# Step 5: fetch_file_content(): Fetches the content of the changed files using the GitHub API, decodes them from base64, and prints the first 200 characters for preview.


import requests
import base64

# GitHub API settings
# GITHUB_TOKEN = "your_personal_access_token"
# REPO_OWNER = "Blendabhishek"
# REPO_NAME = "demo"
# BRANCH_NAME = "main"  # Or "master" if you're using that

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Step 1: Fetch the Latest Commit Hash from the main branch
def get_latest_commit_hash():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH_NAME}"
    response = requests.get(url, headers=headers)
    
    # Check if the response was successful
    if response.status_code == 200:
        data = response.json()
        
        # Check if the response is a dictionary (not a list) and contains the commit info
        if isinstance(data, dict) and "sha" in data:
            return data["sha"]
        else:
            print(f"Unexpected response format: {data}")
            return None
    else:
        print(f"Failed to get latest commit hash: {response.status_code}")
        print(response.json())  # Print the response to help with debugging
        return None

# Step 2: Fetch the Previous Commit Hash (to compare with the latest one)
def get_previous_commit_hash(latest_commit_hash):
    # You can use the commits endpoint to get the previous commit
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits?sha={BRANCH_NAME}&per_page=2"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if len(data) > 1:
            return data[1]["sha"]
    else:
        print(f"Failed to get previous commit hash: {response.status_code}")
        print(response.json())
    return None

# Step 3: Compare the commits (check if they are different)
def compare_commits(latest_commit_hash, previous_commit_hash):
    if latest_commit_hash != previous_commit_hash:
        print(f"Changes detected between {previous_commit_hash} and {latest_commit_hash}")
        return True
    else:
        print("No changes detected.")
        return False

# Step 4: Fetch the Changed Files
def get_changed_files(latest_commit_hash, previous_commit_hash):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{previous_commit_hash}...{latest_commit_hash}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("files", [])
    else:
        print(f"Failed to compare commits: {response.status_code}")
        print(response.json())
    return []

# Step 5: Fetch the Content of Changed Files
def fetch_file_content(file_name):
    content_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_name}"
    content_response = requests.get(content_url, headers=headers)
    
    if content_response.status_code == 200:
        file_data = content_response.json()
        file_content = base64.b64decode(file_data['content']).decode('utf-8')
        return file_content
    else:
        print(f"Failed to fetch content for {file_name}. Status Code: {content_response.status_code}")
        return None

# Step 6: Main Function to Run the Workflow
def sync_with_github():
    # Fetch the latest commit hash
    latest_commit_hash = get_latest_commit_hash()
    if latest_commit_hash is None:
        return

    # Fetch the previous commit hash
    previous_commit_hash = get_previous_commit_hash(latest_commit_hash)
    if previous_commit_hash is None:
        return

    # Compare the commits
    if compare_commits(latest_commit_hash, previous_commit_hash):
        # Get the changed files
        changed_files = get_changed_files(latest_commit_hash, previous_commit_hash)
        
        if changed_files:
            for file in changed_files:
                file_name = file.get("filename")
                status = file.get("status")  # added, modified, removed
                print(f"Processing file: {file_name} (Status: {status})")
                
                # Fetch the content of the changed file
                file_content = fetch_file_content(file_name)
                if file_content:
                    print(f"Content of {file_name}:")
                    print(file_content[:200])  # Print the first 200 characters as a sample
                else:
                    print(f"Could not fetch content for {file_name}")
        else:
            print("No files changed.")
    else:
        print("No changes detected between commits.")
