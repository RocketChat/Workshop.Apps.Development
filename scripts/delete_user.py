import requests
import json
import os
import time
import re
from dotenv import load_dotenv

# Load environment variables from .env file (if any)
try:
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

def delete_user(username, auth_token, user_id, base_url="https://dev.rocket.chat"):
    """
    Delete a user from a Rocket.Chat server.
    """
    url = f"{base_url}/api/v1/users.delete"
    
    headers = {
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    
    payload = {
        "username": username
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error deleting user {username}: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                return False, error_data
            except:
                return False, str(e)
        return False, str(e)

def parse_usernames(text):
    """
    Parse usernames from the provided text format
    """
    usernames = []
    pattern = r'@([^ \n]+)'
    
    matches = re.findall(pattern, text)
    for match in matches:
        usernames.append(match)
    
    return usernames

def main():
    # Get auth token and user ID from environment variables or prompt user
    auth_token = os.environ.get("RC_AUTH_TOKEN")
    user_id = os.environ.get("RC_USER_ID")
    base_url = os.environ.get("RC_URL", "https://dev.rocket.chat")
    
    if not auth_token:
        auth_token = input("Enter your Rocket.Chat auth token (X-Auth-Token): ")
    
    if not user_id:
        user_id = input("Enter your Rocket.Chat user ID (X-User-Id): ")
    
    # User list from the provided text
    user_text = """

ZiHao Fang @fzh075
joined the channel
8:11 PM

Sivan Pushpagiri @SivanRP
joined the channel
7:59 PM

Sivan Pushpagiri @pushpagiri.sivan
joined the channel
8:03 PM

rithvick kumar @rithvick.kumar
joined the channel
10:28 PM
March 29, 2025

Poonam Dewangan @poonam.dewangan
joined the channel
10:24 AM

Vasita Puppala @vasita.puppala
joined the channel
8:14 PM
March 31, 2025

Shweta sakshi @shweta.sakshi
joined the channel
7:03 PM


    """
    
    usernames = parse_usernames(user_text)
    
    if not usernames:
        print("No usernames found in the provided text.")
        return
    
    print(f"Found {len(usernames)} usernames:")
    for index, username in enumerate(usernames):
        print(f"{index + 1}. {username}")
    
    # Ask for confirmation
    confirm = input(f"\nDo you want to delete all {len(usernames)} users? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Option to specify a range
    range_option = input("\nDo you want to delete all users or specify a range? (all/range): ")
    start_index = 0
    end_index = len(usernames)
    
    if range_option.lower() == 'range':
        try:
            start_index = int(input("Enter start index (1-based): ")) - 1
            end_index = int(input("Enter end index (1-based): "))
            
            if start_index < 0 or end_index > len(usernames) or start_index >= end_index:
                print("Invalid range. Using all users.")
                start_index = 0
                end_index = len(usernames)
        except ValueError:
            print("Invalid input. Using all users.")
    
    # Delete each user
    print("\nDeleting users...")
    success_count = 0
    fail_count = 0
    
    for i in range(start_index, end_index):
        username = usernames[i]
        print(f"Deleting user: {username}")
        
        success, result = delete_user(username, auth_token, user_id, base_url)
        
        if success:
            print(f"Successfully deleted {username}!")
            success_count += 1
        else:
            print(f"Failed to delete {username}: {result}")
            fail_count += 1
        
        # Add a small delay between deletions to avoid rate limiting
        time.sleep(1)
    
    print("\nOperation completed!")
    print(f"Summary: {success_count} users deleted successfully, {fail_count} failed.")

if __name__ == "__main__":
    main()