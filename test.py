import os
from dotenv import load_dotenv
from github import Github, Auth
from langchain_community.utilities.github import GitHubAPIWrapper
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit

# Load environment variables from .env
load_dotenv()

# Configuration
repo_name = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

if not repo_name or not token:
    print("-" * 60)
    print("MISSING CONFIGURATION!")
    print("Please set the following in your .env file:")
    print("GITHUB_REPOSITORY=owner/repo")
    print("GITHUB_PERSONAL_ACCESS_TOKEN=your_pat_here")
    print("-" * 60)
    exit(1)

print(f"Connecting to repository: {repo_name}...")

try:
    # Initialize GitHub instance with PAT
    auth = Auth.Token(token)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    # Manually initialize GitHubAPIWrapper to bypass its strict App-only validation in older LangChain versions
    github_wrapper = GitHubAPIWrapper.model_construct(
        github=g,
        github_repo_instance=repo,
        github_repository=repo_name,
        active_branch=repo.default_branch,
        github_base_branch=repo.default_branch
    )

    # Initialize the toolkit
    toolkit = GitHubToolkit.from_github_api_wrapper(github_wrapper)
    tools = toolkit.get_tools()

    # Helper to find a tool by name
    def get_tool(name):
        return next((t for t in tools if t.name == name), None)

    # 1. Test "Read File"
    read_tool = get_tool("Read File")
    if read_tool:
        # Prompt for file path or use a default
        file_to_read = "README.md" 
        print(f"\n--- Testing Read File: {file_to_read} ---")
        try:
            content = read_tool.run({"formatted_filepath": file_to_read})
            print("CONTENT PREVIEW:")
            print("-" * 30)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("-" * 30)
        except Exception as e:
            print(f"Error reading file '{file_to_read}': {e}")
    else:
        print("Read File tool not found in toolkit.")

    # 2. Test "Search Code"
    search_tool = get_tool("Search code")
    if search_tool:
        query = "langchain" # Default search query
        print(f"\n--- Testing Search Code: '{query}' ---")
        try:
            results = search_tool.run(query)
            print("SEARCH RESULTS:")
            print("-" * 30)
            print(results)
            print("-" * 30)
        except Exception as e:
            print(f"Error searching code for '{query}': {e}")
    else:
        print("Search code tool not found in toolkit.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    print("Please verify your GITHUB_REPOSITORY and GITHUB_PERSONAL_ACCESS_TOKEN.")
