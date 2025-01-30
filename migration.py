import csv
import os
import subprocess
import requests
import json
import shutil  # Import shutil for cross-platform directory deletion

# Constants
GITLAB_URL = "https://gitlab.com/"
GITLAB_TOKEN = ""
GITHUB_URL = "https://api.github.com"
GITHUB_TOKEN = ""
GITHUB_ORG = "Ifeax"

# Headers for GitHub API
github_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Accept": "application/vnd.github.v3+json"
}

# Headers for GitLab API
gitlab_headers = {
    "Private-Token": GITLAB_TOKEN
}

# Function to create a GitHub repository
def create_github_repo(repo_name):
    url = f"{GITHUB_URL}/orgs/{GITHUB_ORG}/repos"
    data = {"name": repo_name, "private": True}
    response = requests.post(url, headers=github_headers, json=data)
    if response.status_code == 201:
        print(f"Created GitHub repository: {repo_name}")
    else:
        print(f"Failed to create GitHub repository: {repo_name}, Status Code: {response.status_code}, Response: {response.text}")

# Function to get project ID
def get_gitlab_project_id(project_path):
    search_url = f"{GITLAB_URL}/api/v4/projects/{project_path.replace('/', '%2F')}"
    response = requests.get(search_url, headers=gitlab_headers)
    if response.status_code == 200:
        project_data = response.json()
        if "id" in project_data:
            return project_data["id"]
    print(f"Failed to get project ID for {project_path}, Status: {response.status_code}, Response: {response.text}")
    return None

# Function to clone GitLab repository and push to GitHub
def migrate_repository(gitlab_repo_path, github_repo_name):
    gitlab_repo_url = f"{GITLAB_URL}{gitlab_repo_path}.git"
    github_repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_ORG}/{github_repo_name}.git"
    
    repo_dir = f"{gitlab_repo_path.split('/')[-1]}.git"

    # Check if the folder exists and remove it before cloning
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir, ignore_errors=True)

    print(f"Cloning GitLab repository: {gitlab_repo_url}")
    result = subprocess.run(["git", "clone", "--mirror", gitlab_repo_url], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to clone GitLab repository: {gitlab_repo_url}, Error: {result.stderr}")
        return
    
    os.chdir(repo_dir)
    
    print(f"Pushing to GitHub repository: {github_repo_url}")
    result = subprocess.run(["git", "push", "--mirror", github_repo_url], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to push to GitHub repository: {github_repo_url}, Error: {result.stderr}")
    
    os.chdir("..")
    shutil.rmtree(repo_dir, ignore_errors=True)
    print(f"Successfully migrated {gitlab_repo_path} to GitHub repository: {github_repo_name}")

# Function to migrate issues from GitLab to GitHub
def migrate_issues(gitlab_repo_id, github_repo_name):
    gitlab_issues_url = f"{GITLAB_URL}/api/v4/projects/{gitlab_repo_id}/issues"
    response = requests.get(gitlab_issues_url, headers=gitlab_headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch issues from GitLab. Status code: {response.status_code}, Response: {response.text}")
        return
    
    try:
        gitlab_issues = response.json()
    except json.JSONDecodeError:
        print("Error decoding JSON response from GitLab.")
        return
    
    if not isinstance(gitlab_issues, list):
        print("Unexpected response format. Expected a list of issues.")
        return
    
    github_issues_url = f"{GITHUB_URL}/repos/{GITHUB_ORG}/{github_repo_name}/issues"
    
    for issue in gitlab_issues:
        try:
            data = {
                "title": issue.get("title", "Untitled Issue"),
                "body": issue.get("description", "No description available"),
                "created_at": issue.get("created_at")
            }
            response = requests.post(github_issues_url, headers=github_headers, json=data)
            
            if response.status_code == 201:
                print(f"Migrated issue: {issue['title']}")
            else:
                print(f"Failed to migrate issue: {issue['title']}, Status Code: {response.status_code}, Response: {response.text}")
        except KeyError:
            print("Error processing an issue, skipping...")

# Main function
def main():
    with open("gitlab_projects.csv", mode="r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            gitlab_repo_path = row[0]
            github_repo_name = row[1]
            print(f"Processing repository: {gitlab_repo_path} -> {github_repo_name}")
            
            # Create GitHub repository
            create_github_repo(github_repo_name)
            
            # Migrate repository
            migrate_repository(gitlab_repo_path, github_repo_name)
            
            # Fetch the GitLab project ID dynamically
            repo_id = get_gitlab_project_id(gitlab_repo_path)
            if not repo_id:
                print(f"Skipping repository {gitlab_repo_path} due to missing project ID.")
                continue
            
            # Migrate issues
            migrate_issues(repo_id, github_repo_name)

if __name__ == "__main__":
    main()
