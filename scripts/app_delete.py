import requests
import json
import os
from dotenv import load_dotenv
import time

# Load environment variables from .env file (if any)
try:
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

def get_installed_apps(auth_token, user_id, base_url="https://dev.rocket.chat"):
    """
    Get all installed apps from a Rocket.Chat server.
    """
    url = f"{base_url}/api/apps/installed"
    
    headers = {
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting installed apps: {e}")
        return None

def delete_app(app_id, auth_token, user_id, base_url="https://dev.rocket.chat"):
    """
    Delete an app from a Rocket.Chat server.
    """
    url = f"{base_url}/api/apps/{app_id}"
    
    headers = {
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error deleting app {app_id}: {e}")
        return False, str(e)

def main():
    # Get auth token and user ID from environment variables or prompt user
    auth_token = os.environ.get("RC_AUTH_TOKEN_1")
    user_id = os.environ.get("RC_USER_ID_1")
    base_url = os.environ.get("RC_URL", "https://dev.rocket.chat")
    
    if not auth_token:
        auth_token = input("Enter your Rocket.Chat auth token (X-Auth-Token): ")
    
    if not user_id:
        user_id = input("Enter your Rocket.Chat user ID (X-User-Id): ")
    
    # Get all installed apps
    print("Fetching installed apps...")
    apps_data = get_installed_apps(auth_token, user_id, base_url)

    apps = apps_data.get("apps", []) if apps_data else []
    
    print(f"Found {len(apps)} installed apps.")
    if not apps:
        print("No apps found or error occurred.")
        return
    
    # Filter apps with classFile = "ThreadSummarizerApp.js"
    thread_summarizer_apps = []
    for app in apps:
        print(f"Checking app name: {app.get('name', 'Unknown')}, ID: {app['id']}")
        if "classFile" in app and app["classFile"] == "ThreadSummarizerApp.js":
            thread_summarizer_apps.append(app)
    
    if not thread_summarizer_apps:
        print("No ThreadSummarizerApp.js apps found.")
        return
    
    print(f"Found {len(thread_summarizer_apps)} ThreadSummarizerApp.js apps:")
    for index, app in enumerate(thread_summarizer_apps):
        author_name = app.get('author', {}).get('name', 'Unknown Author')
        print(f"{index + 1}. ID: {app['id']}, Name: {app.get('name', 'Unknown')}, "
              f"Slug: {app.get('nameSlug', 'Unknown')}, Author: {author_name}")
    
    # Ask if user wants to exclude any apps
    exclude_option = input("\nDo you want to exclude any apps from deletion? (y/n): ")
    apps_to_delete = thread_summarizer_apps.copy()
    
    if exclude_option.lower() == 'y':
        exclude_indices = input("Enter the numbers (separated by commas) of apps to exclude: ")
        try:
            exclude_indices = [int(i.strip()) - 1 for i in exclude_indices.split(',')]
            # Filter out the excluded apps
            apps_to_delete = [app for idx, app in enumerate(thread_summarizer_apps) if idx not in exclude_indices]
            
            print(f"\nWill delete {len(apps_to_delete)} apps (excluded {len(thread_summarizer_apps) - len(apps_to_delete)}):")
            for index, app in enumerate(apps_to_delete):
                author_name = app.get('author', {}).get('name', 'Unknown Author')
                print(f"{index + 1}. Name: {app.get('name', 'Unknown')}, Author: {author_name}")
        except ValueError:
            print("Invalid input. Will proceed with all apps.")
    
    # Ask for confirmation
    confirm = input(f"\nDo you want to delete {len(apps_to_delete)} ThreadSummarizerApp.js apps? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Delete each app
    print("\nDeleting apps...")
    for app in apps_to_delete:
        app_id = app['id']
        app_name = app.get('name', 'Unknown')
        app_slug = app.get('nameSlug', 'Unknown')
        author_name = app.get('author', {}).get('name', 'Unknown Author')
        
        print(f"Deleting {app_name} by {author_name} ({app_slug}) with ID: {app_id}")
        success, result = delete_app(app_id, auth_token, user_id, base_url)
        
        if success:
            print(f"Successfully deleted {app_name} by {author_name}!")
        else:
            print(f"Failed to delete {app_name}: {result}")
        
        # Add a small delay between deletions to avoid rate limiting
        time.sleep(1)
    
    print("\nOperation completed!")

if __name__ == "__main__":
    main()