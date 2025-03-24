# Workshop.Apps.Development
Guide to get started with Rocket.Chat Apps Development Workshop.

## Getting Started

### Requirements
- Node.js v20.18.1
- Unix-based OS (Linux, macOS, WSL2)

### Pre-requisites

1. Join the Workshop server workspace shared in the workshop room.
2. Join the room `#challengechat` in the workshop server.
> **Hint**: Find the room under the **Directory** tab in the left sidebar.
3. Note down the server URL and your credentials (username and password) for the workshop server.

## Part 1: Deploying Your First Rocket.Chat App
In this part, you'll learn how to deploy a summarization app and implement a slash command.

#### 1. Install the Rocket.Chat Apps CLI
Install `rc-apps` globally:

```bash
npm install -g @rocket.chat/apps-cli
```

Verify the installation:

```bash
rc-apps -v
```

You should see the CLI version information:

```bash
@rocket.chat/apps-cli/1.12.0 darwin-arm64 node-v20.18.1
```

> **Note:** The platform information (e.g., "darwin-arm64") will differ depending on your operating system.

#### 2. Clone the repository

```bash
git clone https://github.com/RocketChat/Workshop.Apps.Development.git
```

#### 3. Navigate to the app directory

```bash
cd Workshop.Apps.Development/app 
```

#### 4. Personalize your app
Modify the following files:

- In the `app.json` file:
  - Change `nameSlug` to a unique value (e.g., `ai-chat-summarizer-<yourname>`)
  - Generate a new UUID at [uuidgenerator.net](https://www.uuidgenerator.net/version4) for the `id` field
    - **Important:** Do NOT use `0034268f-e49a-4113-be51-4a5ca77aeeb1`
  - Update the `author` field with your name

- Replace the `icon.png` file:
  1. Delete the existing icon
  2. Create a new icon (recommend using AI image generation)
  3. You can use [Pollinations.AI](https://image.pollinations.ai/prompt/YOUR_INITIAL_avatar) with your initial
  4. Save as `icon.png` (keep file size small)

#### 5. Customize your command
Open `/commands/SummarizeCommand.ts` and change the `command` field to a unique name (e.g., `<yourname>-chat-summary`).

#### 6. Install dependencies

```bash
npm install
```

#### 7. Build your app

```bash
rc-apps package
```

#### 8. Update the LLM API endpoint
Open the file [`/settings/settings.ts`](https://github.com/RocketChat/Workshop.Apps.Development/blob/main/app/settings/settings.ts) and modify the L12 key value and package value to `[llama3-8b.local:1234](http://llama3-8b.local:1234)`.

> **Note:** The API call is made to `http://llama3-8b.local:1234/v1/chat/completions` so `llama3-8b.local` is the hostname and `1234` the port.

#### 9. Configure and deploy
Edit the `.rcappsconfig` file with your credentials:

```json
{
  "url": "https://workspace_server_url",
  "username": "your_username",
  "password": "your_password"
}
```

> **Important:** Use the server URL shared in the workshop room along with your personal credentials.

Deploy your app:

```bash
rc-apps deploy
```

#### 10. Test your slash command
Type `/<yourname>-chat-summary` in the thread on the `#challengechat` channel and press Enter.

## Part 2: The App

### How does the app works?
![image](https://github.com/user-attachments/assets/c662a7f7-7802-4ab7-8db5-dd5f4458e599)

The app works in a simple way. It only does three steps:
1. Read the messages
2. Summarize the messages (main feature)
3. Execute the add-ons


### What is exactly add-ons?
<div style="text-align: center">
<img src="https://github.com/user-attachments/assets/972a9b70-276b-4a81-9859-4f2c0e374c4f" width="500">
</div>

In the `Marketplace`, you will be able to see these settings. For every add-ons you check, the **app will create corresponding prompt and execute an LLM call**. In this case, instead of just summarizing the message (step 2), the app will also output what are the summaries **for each participant.**

### Enabling the add-ons

1. Navigate to **Administration** (kebab menu) → **Marketplace**
2. Select the **Private Apps** tab
3. Find and click on your deployed app
4. Go to the **Settings** tab
5. In the **Summary add-ons** section, select any one add-on
6. Click **Save**
7. Test your command again with `/<yourname>-chat-summary` in the `#challengechat` channels' thread 
> **For curious minds ✨**, the prompt for the add-on can be found in the [`/constants/prompt.ts`](https://github.com/RocketChat/Workshop.Apps.Development/blob/main/app/constants/prompts.ts) file. You can modify the prompt to suit your needs.
8. Verify that you see the chat summary plus the selected add-on functionality
9. Take a screenshot of your successful result
10. Share your screenshot in the workshop channel along with your email address to receive an invitation to the Workshop Meetup

### Where is the add-on code?

<div style="text-align: center">
<img src="https://github.com/user-attachments/assets/99005a33-a3c7-4a96-8374-5a39e97fdcf9" width="500">
</div>

Basically, this code only do
```
if ("assigned-tasks" is checked) {
    // 1. Create assigned task prompt
    // 2. Execute LLM call
    // 3. Show message to user
}
```

So, if the question is "can I add my own add-ons"? Obviously yes, you can just 
1. Add another block of if statement,
2. Create corresponding prompt, and 
3. Execute the LLM call (same code everywhere)

**HOWEVER !!** Don't forget to add your add-ons in the settings here to make it appear in the settings.

<div style="text-align: center">
<img src="https://github.com/user-attachments/assets/65afde95-a40a-48d6-9bd0-60d6c1936732" width="500">
</div>

## Next Steps
To deepen your understanding, explore the [Rocket.Chat Apps documentation](https://developer.rocket.chat/docs/rocketchat-apps-engine) and most importantly, **have fun!** understading the App code you just deployed and how to improve it.

## Resources
- [Rocket.Chat Apps Documentation](https://developer.rocket.chat/docs/rocketchat-apps-engine)
- [Prompt Engineering](https://www.promptingguide.ai/)