# Workshop.Apps.Development
Guide to get started with Rocket.Chat Apps Development Workshop.

## Getting Started

### Requirements
- Node.js v20.18.1
- Unix-based OS (Linux, MacOS, WSL2)

1. Install `rc-apps` globally:

```bash
  npm install -g @rocket.chat/apps-cli
```

To verify that the installation was successful, run:

```bash
  rc-apps -v
```
The output should be the version of the `rc-apps` CLI. Example:

```bash
@rocket.chat/apps-cli/1.12.0 darwin-arm64 node-v20.18.1
```

> Notice the "darwin-arm64" part of the output. This is the platform that the CLI is running on. The platform will be different depending on the operating system you are using.

2. Clone the repository:
```
git clone https://github.com/RocketChat/Apps.Chat.Summarize.git
```

3. Change to the directory of the repository:
```
cd Apps.Chat.Summarize/app 
```

4. Modify the following:
- In the `app.json` file:
  - `nameSlug` - The App username, which must be unique. Currently, the value is `ai-chat-summarizer` change it to something unique, e.g., `ai-chat-summarizer-<yourname>`.
  - `id` - The App UUID, which must be unique. You can generate a new UUID using an online UUID generator. Head to [https://www.uuidgenerator.net/version4](https://www.uuidgenerator.net/version4) and click on the "Generate" button. Copy the generated UUID and paste it in the `id` field. Please do **NOT** use `0034268f-e49a-4113-be51-4a5ca77aeeb1` as it is already in use.
  - `author` - Modify to include your name.
- Replace the `icon.png` file with your own icon. We recommend using an AI-generated image. Consider using prompts related to your initial. Use a prompt like '[your concept here], avatar' at an AI image generator like [https://image.pollinations.ai/](https://image.pollinations.ai/).
> Note you can modify the text as `https://image.pollinations.ai/prompt/{prompt}` where `{prompt}` is the text you want to generate the image for.
> Note: Make sure to delete the `icon.png` file before replacing it with your own icon. And make sure the new icon is named `icon.png`, with the storage size not exceeding KBs.

5. Open the file `/commands/SummarizeCommand.ts` and modify the `command` field to a unique command name. Currently, the value is `chat-summary` change it to something unique, e.g., `chat-summary-<yourname>`.

6. Run the following command to install the dependencies:
```
npm install
```

7. Run the following command to build the app:
```
rc-apps package
```

8. Modify the `.rcappsconfig` file with  server URL, username and password.
  E.g., 
  ```
  {
    "url": "https://your_server_url",
    "username": "your_username",
    "password": "your_password"
  }
  ```
  > Note: replace the `your_server_url`, `your_username` and `your_password` with the server URL shared in the room, your username and password.

Then run the following command to deploy the app:
```
rc-apps deploy
```

9. Modify the API call to the LLM from `http://llama3-8b` to `http://llama3-8b:1234` and try out the slash command. 

> (Hint: Try modifying the settings key and packageValue `llama3-8b` in the `setting.ts` file to `llama3-8b:1234`)
10. Try out the slash command in the Rocket.Chat server.

11. If you are able to successfully deploy the app and try out the slash command (it will return a summary), congratulations!🎉 For the next steps, please refer to the [Apps documentation](https://developer.rocket.chat/docs/rocketchat-apps-engine) to familiarize yourself with the Apps development and try to understand the code you have modified.