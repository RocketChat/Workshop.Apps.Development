import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def invite_users(room_id, user_ids, auth_token, user_id):
    """Invites a list of users to a Rocket.Chat room."""

    url = "https://open.rocket.chat/api/v1/groups.invite"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Auth-Token": auth_token,
        "X-User-Id": user_id,
    }

    for user_id_to_invite in user_ids:
        payload = json.dumps({
            "roomId": room_id,
            "username": user_id_to_invite
        })

        try:
            print("pyaload", payload)
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            print(f"Invited user {user_id_to_invite} successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Error inviting user {user_id_to_invite}: {e}")


def main():
    """Main function to read config and invite users."""

    # Load configuration from JSON file
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON in config.json.")
        return

    # Get the starting index and number of users from the CLI
    try:
        start_index = int(input("Enter the starting index (0 for the beginning): "))
        num_users = int(input("Enter the number of users to invite: "))
        list_index = int(input("Enter the list index (0 for the first list, -1 for the last list): "))
    except ValueError:
        print("Error: Invalid input. Please enter integers.")
        return

    # Extract usernames from the config
    try:
        usernames = config["entries"][list_index]["usernames"][start_index:start_index + num_users]
    except (KeyError, IndexError):
        print("Error: Could not extract usernames from config.json.")
        return
    
    # Show the extracted usernames and get confirmation
    print("Usernames to invite:", usernames)
    confirm = input("Do you want to invite these users? (y/n): ")
    if confirm.lower() != "y":
        print("Operation cancelled.")
        return

    # Get Rocket.Chat credentials from environment variables
    auth_token = os.environ.get("RC_TOKEN")
    user_id = os.environ.get("RC_UID")
    room_id = os.environ.get("RC_RID")

    if not auth_token or not user_id:
        print("Error: ROCKETCHAT_AUTH_TOKEN and ROCKETCHAT_USER_ID environment variables must be set.")
        return

    # Invite the users
    invite_users(room_id, usernames, auth_token, user_id)


if __name__ == "__main__":
    main()