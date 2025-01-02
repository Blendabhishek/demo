import os
import requests
import datetime
import uuid
import warnings
from typing import List, Dict, Any, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes._generated.models import VectorSearchAlgorithmKind
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.indexes.models import *
# from azure.search.documents.indexes.models import (
#     SearchIndex,
#     SimpleField,
#     SearchableField,
#     SearchField,
#     VectorSearch,
#     VectorSearchAlgorithmConfiguration,
#     VectorSearchProfile
# )
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

warnings.filterwarnings("ignore")


class GitHubCommitDeltaIndexer:
    def __init__(
            self,
            search_endpoint: str,
            search_key: str,
            index_name: str,
            azure_openai_endpoint: str,
            azure_openai_key: str,
            embedding_model: str,
            api_version: str,
            github_token: str,
            repo_owner: str,
            repo_name: str,
            branch_name: str = "main"
    ):
        # Azure Cognitive Search settings
        self.search_endpoint = search_endpoint
        self.index_name = index_name
        self.vector_dimension = 1536  # Dimension for Azure OpenAI embeddings

        # GitHub settings
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch_name = branch_name
        self.hash_file = os.path.join(os.path.dirname(__file__), "previous_commit_hash.txt")

        # Initialize Azure Cognitive Search clients
        self.credential = AzureKeyCredential(search_key)
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.credential
        )
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            credential=self.credential,
            index_name=self.index_name
        )

        # Initialize Azure OpenAI embeddings
        self.embedding_model = AzureOpenAIEmbeddings(
            azure_endpoint=azure_openai_endpoint,
            openai_api_key=azure_openai_key,
            azure_deployment=embedding_model,
            openai_api_version=api_version,
            chunk_size=5
        )

        # Create or update index
        self._create_or_update_index()

    def _create_or_update_index(self) -> None:
        """Create or update the Azure Cognitive Search index with vector search capabilities"""
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="commit_sha", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="additions", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="deletions", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=self.vector_dimension,
                vector_search_profile_name="my-profile"
            )
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="my-algorithm",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="my-profile",
                    algorithm_configuration_name="my-algorithm"
                )
            ]
        )

        # Define the index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )

        try:
            # Create or update the index
            self.index_client.create_or_update_index(index)
            print(f"Index {self.index_name} created or updated successfully")
        except Exception as e:
            print(f"Error creating/updating index: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")

    def search_similar_changes(self, query_text: str, top: int = 5) -> List[Dict]:
        """Search for similar changes using vector similarity."""
        try:
            # Generate embedding for the query text
            query_vector = self.generate_embedding(query_text)

            # Use the `vector_queries` parameter explicitly
            vector_query = {
                "vector": query_vector,
                "k": top,
                "fields": "content_vector"
            }

            # Perform the vector search
            results = self.search_client.search(
                search="*",  # Standard search query
                vector_queries=[vector_query],  # Pass vector queries as a list
                top=top,
                select="filename,commit_sha,content,status,additions,deletions,timestamp"
            )

            return [result for result in results]
        except Exception as e:
            print(f"Error performing vector search: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            return []

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        return self.embedding_model.embed_query(text)

    def read_previous_hash(self) -> Optional[str]:
        """Read the previous commit hash from file"""
        if os.path.exists(self.hash_file):
            with open(self.hash_file, "r") as f:
                return f.read().strip()
        return None

    def write_previous_hash(self, commit_hash: str) -> None:
        """Write the current commit hash to file"""
        with open(self.hash_file, "w") as f:
            f.write(commit_hash)

    def get_latest_commit_hash(self) -> Optional[str]:
        """Get the latest commit hash from GitHub"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits"
        headers = {"Authorization": f"token {self.github_token}"}
        params = {"sha": self.branch_name, "per_page": 1}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data[0]["sha"] if data else None
        except Exception as e:
            print(f"Error fetching latest commit hash: {e}")
            return None

    def get_commit_diff(self, base_commit: str, head_commit: str) -> Optional[Dict]:
        """Get the diff between two commits"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/compare/{base_commit}...{head_commit}"
        headers = {"Authorization": f"token {self.github_token}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching commit diff: {e}")
            return None

    def get_commit_info(self, commit_sha: str) -> Optional[Dict]:
        """Get detailed information about a specific commit"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}"
        headers = {"Authorization": f"token {self.github_token}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching commit info: {e}")
            return None

    def index_commit_delta(self, delta_info: Dict, commit_info: Dict) -> None:
        """Index a commit delta into Azure Cognitive Search with vector embedding"""
        try:
            # Create document ID
            doc_id = f"{commit_info['sha']}_{delta_info['filename']}"

            # Create delta description for vectorization
            delta_description = f"""
            File: {delta_info['filename']}
            Status: {delta_info['status']}
            Changes: +{delta_info['additions']} -{delta_info['deletions']}
            Patch: {delta_info.get('patch', '')}
            Commit Message: {commit_info.get('commit', {}).get('message', '')}
            """

            # Generate vector embedding
            vector_embedding = self.generate_embedding(delta_description)

            # Prepare the document
            document = {
                "id": doc_id,
                "filename": delta_info['filename'],
                "content": delta_description,
                "commit_sha": commit_info['sha'],
                "status": delta_info['status'],
                "additions": delta_info['additions'],
                "deletions": delta_info['deletions'],
                "timestamp": datetime.datetime.now().isoformat(),
                "content_vector": vector_embedding
            }

            # Upload to Azure Cognitive Search
            self.search_client.upload_documents([document])
            print(f"Indexed delta for {delta_info['filename']} (Commit: {commit_info['sha'][:8]})")

        except Exception as e:
            print(f"Error indexing commit delta: {e}")

    def process_commits(self) -> None:
        """Main function to process commits and index changes"""
        previous_commit_hash = self.read_previous_hash()
        latest_commit_hash = self.get_latest_commit_hash()

        if not latest_commit_hash:
            print("Could not fetch the latest commit hash. Exiting...")
            return

        if not previous_commit_hash:
            print(f"Initial run detected. Setting commit hash to {latest_commit_hash}")
            self.write_previous_hash(latest_commit_hash)
            return

        if previous_commit_hash == latest_commit_hash:
            print("No new changes detected. Exiting...")
            return

        print(f"Changes detected between {previous_commit_hash[:8]} and {latest_commit_hash[:8]}")

        # Get the diff and commit information
        diff = self.get_commit_diff(previous_commit_hash, latest_commit_hash)
        commit_info = self.get_commit_info(latest_commit_hash)

        if diff and "files" in diff:
            for file in diff["files"]:
                self.index_commit_delta(file, commit_info)
            self.write_previous_hash(latest_commit_hash)
        else:
            print("No file changes detected.")

def main():
    # Configuration
    CONFIG = {
        "search_endpoint": "search_endpoint_name",
        "search_key": "key",
        "index_name": "index_name",
        "azure_openai_endpoint": "",
        "azure_openai_key": "",
        "embedding_model": "",
        "api_version": "",
        "github_token": "",
        "repo_owner": "",
        "repo_name": "",
        "branch_name": ""
    }
    
    try:
        # Initialize indexer
        indexer = GitHubCommitDeltaIndexer(**CONFIG)
        
        # Process commits
        indexer.process_commits()
        
        # Example search (optional)
        results = indexer.search_similar_changes(
            "Sample query to find similar code changes",
            top=5
        )
        
        for result in results:
            print(f"\nFound similar change in {result['filename']}")
            print(f"Commit: {result['commit_sha']}")
            print(f"Status: {result['status']}")
            print(f"Content: {result['content']}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
