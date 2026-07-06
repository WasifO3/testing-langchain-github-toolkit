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

    def search_repo_contents(query, limit=5):
        """Fallback search that scans repository files directly when GitHub code search returns no results."""
        matches = []

        def walk(path):
            try:
                items = repo.get_contents(path)
            except Exception:
                return

            if isinstance(items, list):
                for item in items:
                    if item.type == "dir":
                        walk(item.path)
                    elif item.type == "file":
                        try:
                            file_obj = repo.get_contents(item.path)
                            content = file_obj.decoded_content.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                        if query.lower() in content.lower():
                            matches.append({"path": item.path, "content": content})
                            if len(matches) >= limit:
                                return
            else:
                try:
                    content = items.decoded_content.decode("utf-8", errors="ignore")
                except Exception:
                    content = ""
                if query.lower() in content.lower():
                    matches.append({"path": items.path, "content": content})

        walk("")
        return matches

    # 1. Test "Read File"
    read_tool = get_tool("Read File")
    if read_tool:
        # Prompt for file path or use a default
        file_to_read = "new_test.py" 
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
        query = "search_repo_contents"
        print(f"\n--- Testing Search Code: '{query}' ---")
        try:
            results = search_tool.run({"search_query": query})
            print("TOOL SEARCH RESULTS:")
            print("-" * 30)
            print(results)
            print("-" * 30)
            if "0 results found." in results.lower() or "no results" in results.lower():
                raise ValueError("GitHub toolkit returned no results")
        except Exception as e:
            print(f"Toolkit search returned no results ({e}). Falling back to repository scan...")
            fallback_matches = search_repo_contents(query)
            if fallback_matches:
                print("FALLBACK SEARCH RESULTS:")
                print("-" * 30)
                for match in fallback_matches:
                    print(f"Filepath: {match['path']}")
                    print(match["content"][:1000])
                    print("<END OF FILE>")
                    print("-" * 30)
            else:
                print("No matches found in repository contents.")
    else:
        print("Search code tool not found in toolkit.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    print("Please verify your GITHUB_REPOSITORY and GITHUB_PERSONAL_ACCESS_TOKEN.")

print("All tools available:", [tool.name for tool in tools])