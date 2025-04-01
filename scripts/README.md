## Helper Scripts

Automate repetitive tasks

### Set up
1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   > **Note:** Recommended to use a virtual environment to avoid conflicts with other Python projects. `venv` is a good option.

2. Create a `config.json` file in the same directory as the scripts. Use the provided `config.json.example` as a template. Fill in the required fields:
3. Add an `.env` file in the same directory as the scripts. Use the provided `.env.example` as a template. 

### This folder contains helper scripts to automate repetitive tasks.
1. [app_delete.py](./app_delete.py): Delete the app from the server. It deletes the App that has `ThreadSummarizerApp.js` as the class file.
2. [delete_user.py](./delete_user.py): Removes the user from the server. Paste the user joined notifications on L70 `user_text` from any room (e.g., `#general`) and run the script. It will remove the user from the server.
3. [kick_users.py](./kick_users.py): Kicks all users from a private group. It will ask if you want to kick all users from the private group. If you answer `yes`, it will remove all users from the private group. Or exclude some users from the kick. 
4. [invite_users.py](./invite_users.py): Invites all users to a private group. It will ask if you want to invite all users to the private group, pass on the indexes from the list defined in `config.json` file. 