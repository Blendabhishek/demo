# Detecting GitHub Changes and Syncing with Vector DB

This project demonstrates how to detect changes in the `main` (or `master`) branch of a GitHub repository, fetch the changed file names and their contents, and update a vector database accordingly. The script is designed to run daily, ensuring the vector database remains synchronized with the latest changes in the repository.

---

## Features
- **Track Changes**: Detect changes in the `main` branch of a specified GitHub repository.
- **File Sync**: Retrieve the file names and content of modified, added, or deleted files.
- **Vector Database Integration**: Update a vector database (e.g., ChromaDB) with the latest file data.
- **Scheduled Execution**: Set up daily or twice-daily execution via a cron job or task scheduler.

---

## Requirements
### Dependencies
- Python 3.8 or higher
- Libraries:
  - `requests`
  - `os`
  - `base64`
  - `sentence-transformers`
  - `chromadb`

Install the required Python libraries using:
```bash
pip install requests sentence-transformers chromadb
```

### GitHub Access
- A GitHub Personal Access Token with `repo` permissions.
- Access to the repository you wish to monitor.

---

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your_username/your_repo.git
   cd your_repo
   ```

2. **Set Up Environment Variables**:
   Create a `.env` file or export the variables directly.
   ```bash
   export GITHUB_TOKEN="your_personal_access_token"
   export REPO_OWNER="Your Repo Name"
   export REPO_NAME="demo"
   ```

3. **Modify the Script**:
   Update the `BRANCH`, `GITHUB_TOKEN`, `REPO_OWNER`, and `REPO_NAME` variables in the script to match your repository details.

4. **Run the Script**:
   ```bash
   python Detect_changes.py
   ```

---

## How It Works

1. **Initial Setup**:
   - The script fetches the latest commit hash of the `main` branch and saves it to `previous_commit_hash.txt`.

2. **Daily Execution**:
   - On subsequent runs, the script compares the latest commit hash with the saved hash to identify changes.

3. **File Retrieval**:
   - Files modified, added, or deleted are identified.
   - The content of modified/added files is fetched and processed.

4. **Vector DB Update**:
   - The vector database is updated by removing outdated vectors and adding new ones based on the changed files.

---

## Script Workflow

1. **Fetch Latest Commit Hash**:
   - Uses the GitHub API to fetch the latest commit hash for the `main` branch.

2. **Compare Hashes**:
   - If the hash has changed, fetch the details of the changes.

3. **Process Changes**:
   - For each changed file, fetch content, and update the vector database.

4. **Save New Hash**:
   - Save the latest commit hash for the next run.

---

## Scheduling the Script

### Using Cron (Linux/MacOS):
1. Open the crontab editor:
   ```bash
   crontab -e
   ```
2. Add an entry to run the script daily:
   ```bash
   0 0 * * * /path/to/python /path/to/Detect_changes.py
   ```

### Using Task Scheduler (Windows):
1. Open Task Scheduler.
2. Create a new task:
   - Set the trigger to daily or twice a day.
   - Set the action to execute the script using Python.

---

## Example Output

### Initial Run
```
Fetching latest commit hash...
Initial run detected. Setting commit hash to e08e52570f711184e33e56e73f650175d68be737.
```

### Subsequent Runs
```
Fetching latest commit hash...
Changes detected between e603dfa0612c91588a593fda837363c5ada7accd and c9e453a192dcc0452eae1ea3b7078a26af788f71.
Processing file: test.txt (Status: modified)
Content of test.txt:
its a sample file to test the Repos!!!
Vector DB updated successfully.
```

---

## Troubleshooting

### Common Issues

1. **Permission Denied**:
   - Ensure the script has write permissions for the working directory.

2. **Missing Dependencies**:
   - Install missing libraries using `pip`.

3. **Invalid GitHub Token**:
   - Verify that the token has the required permissions.

### Debugging
Enable debug logs by adding print statements to track the flow of execution.

---

## License
This project is open-source and available under the [MIT License](LICENSE).

