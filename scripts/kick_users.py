import requests
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file (if any)
try:
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

def get_group_members(room_id, auth_token, user_id, base_url):
    """
    Get all members of a Rocket.Chat group.
    """
    url = f"{base_url}/api/v1/groups.members"
    
    headers = {
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    
    params = {
        "roomId": room_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('members', [])
    except requests.exceptions.RequestException as e:
        print(f"Error getting group members: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                print(f"API Error: {json.dumps(error_data, indent=2)}")
            except:
                pass
        return None

def kick_user(room_id, user_id_to_kick, auth_token, user_id, base_url):
    """
    Kick a user from a Rocket.Chat group.
    """
    url = f"{base_url}/api/v1/groups.kick"
    
    headers = {
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    
    payload = {
        "roomId": room_id,
        "userId": user_id_to_kick
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error kicking user {user_id_to_kick}: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                return False, error_data
            except:
                return False, str(e)
        return False, str(e)

def main():
    # Get auth token, user ID, base URL from environment variables or prompt user
    auth_token = os.environ.get("RC_TOKEN")
    user_id = os.environ.get("RC_UID")
    room_id = os.environ.get("RC_RID")
    
    # Prompt for server URL
    default_url = "https://dev.rocket.chat"
    base_url = input(f"Enter Rocket.Chat server URL (default: {default_url}): ") or default_url
    
    # Ensure base_url doesn't end with a slash
    base_url = base_url.rstrip('/')
    
    if not auth_token:
        auth_token = input("Enter your Rocket.Chat auth token (X-Auth-Token): ")
    
    if not user_id:
        user_id = input("Enter your Rocket.Chat user ID (X-User-Id): ")
    
    if not room_id:
        room_id = input("Enter the room ID: ")
    
    print(f"Using base URL: {base_url}")
    print(f"Using room ID: {room_id}")
    
    # Get all members of the group
    print("\nFetching group members...")
    members = get_group_members(room_id, auth_token, user_id, base_url)
    
    if not members:
        print("No members found or error occurred.")
        return
    
    # Display the members and their usernames
    print(f"\nFound {len(members)} group members:")
    for index, member in enumerate(members):
        username = member.get('username', 'Unknown')
        name = member.get('name', 'Unknown')
        print(f"{index + 1}. {username} ({name})")
    
    # Ask for users to keep
    print("\nSpecify which users to KEEP in the group (all others will be kicked)")
    print("Options:")
    print("1. Enter a comma-separated list of usernames to keep")
    print("2. Enter a comma-separated list of indices (from the list above) to keep")
    keep_option = input("Choose option (1/2): ")
    
    users_to_keep = []
    
    if keep_option == "1":
        usernames_to_keep = input("Enter usernames to keep (comma-separated): ").split(",")
        usernames_to_keep = [u.strip() for u in usernames_to_keep]
        users_to_keep = [m for m in members if m.get('username', '') in usernames_to_keep]
    elif keep_option == "2":
        try:
            indices = input("Enter indices to keep (comma-separated): ").split(",")
            indices = [int(i.strip()) - 1 for i in indices]
            users_to_keep = [members[i] for i in indices if 0 <= i < len(members)]
        except (ValueError, IndexError):
            print("Invalid indices. Operation cancelled.")
            return
    else:
        print("Invalid option. Operation cancelled.")
        return
    
    # Create the list of users to kick (all members not in the keep list)
    users_to_kick = [m for m in members if m.get('_id') not in [u.get('_id') for u in users_to_keep]]
    
    if not users_to_kick:
        print("No users to kick. Operation cancelled.")
        return
    
    # Display the list of users to kick
    print(f"\nPreparing to kick {len(users_to_kick)} users:")
    for index, user in enumerate(users_to_kick):
        username = user.get('username', 'Unknown')
        name = user.get('name', 'Unknown')
        print(f"{index + 1}. {username} ({name})")
    
    # Ask for confirmation
    confirm = input(f"\nDo you want to kick these {len(users_to_kick)} users? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Kick each user
    print("\nKicking users...")
    success_count = 0
    fail_count = 0
    
    for user in users_to_kick:
        user_id_to_kick = user.get('_id')
        username = user.get('username', 'Unknown')
        
        print(f"Kicking user: {username}")
        success, result = kick_user(room_id, user_id_to_kick, auth_token, user_id, base_url)
        
        if success:
            print(f"Successfully kicked {username}!")
            success_count += 1
        else:
            print(f"Failed to kick {username}: {result}")
            fail_count += 1
        
        # Add a small delay between kicks to avoid rate limiting
        time.sleep(1)
    
    print("\nOperation completed!")
    print(f"Summary: {success_count} users kicked successfully, {fail_count} failed.")

if __name__ == "__main__":
    main()