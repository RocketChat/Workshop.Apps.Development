import {
	IHttp,
	IModify,
	IRead,
} from '@rocket.chat/apps-engine/definition/accessors';
import { IRoom } from '@rocket.chat/apps-engine/definition/rooms';
import {
	ISlashCommand,
	SlashCommandContext,
} from '@rocket.chat/apps-engine/definition/slashcommands';
import { IUser } from '@rocket.chat/apps-engine/definition/users';
import { notifyMessage } from '../helpers/notifyMessage';
import { createTextCompletion } from '../helpers/createTextCompletion';
import {
	createAssignedTasksPrompt,
	createOtherAddonPrompt,
	createSummaryPrompt,
	createSummaryPromptByTopics,
} from '../constants/prompts';
import { App } from '@rocket.chat/apps-engine/definition/App';
import { IMessageRaw } from '@rocket.chat/apps-engine/definition/messages';

export class SummarizeCommand implements ISlashCommand {
	public command = 'chat-summary-demo';
	public i18nParamsExample = 'Summarize messages in a thread or channel';
	public i18nDescription = '';
	public providesPreview = false;
	private readonly app: App;

	constructor(app: App) {
		this.app = app;
	}

	public async executor(
		context: SlashCommandContext,
		read: IRead,
		modify: IModify,
		http: IHttp
	): Promise<void> {
		const user = context.getSender();
		const room = context.getRoom();
		const threadId = context.getThreadId();
		const addOns = await this.app
			.getAccessors()
			.environmentReader.getSettings()
			.getValueById('add-ons');

		let messages: string;
		if (!threadId) {
			messages = await this.getRoomMessages(room, read);
		} else {
			messages = await this.getThreadMessages(room, read, user, threadId);
		}

		let summary: string;
		if (!threadId) {
			const prompt = createSummaryPromptByTopics(messages);
			summary = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				prompt,
				threadId
			);
		} else {
			const prompt = createSummaryPrompt(messages);
			summary = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				prompt,
				threadId
			);
		}
		await notifyMessage(room, read, user, summary, threadId);

		//TODO: give response based on addons selected
		if (addOns.includes('workshop-task')) {
			const assignedTasksPrompt = createAssignedTasksPrompt(messages);
			const assignedTasks = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				assignedTasksPrompt,
				threadId
			);
			await notifyMessage(room, read, user, assignedTasks, threadId);
		}

		if (addOns.includes('other-add-on')) {
			const otherAddonPrompt = createOtherAddonPrompt(messages);
			const otherAddonResponse = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				otherAddonPrompt,
				threadId
			);
			await notifyMessage(room, read, user, otherAddonResponse, threadId);
		}
	}

	private async getRoomMessages(room: IRoom, read: IRead): Promise<string> {
		const messages: IMessageRaw[] = await read
			.getRoomReader()
			.getMessages(room.id, {
				limit: 100,
				sort: { createdAt: 'asc' },
			});

		const messageTexts: string[] = [];
		for (const message of messages) {
			if (message.text) {
				messageTexts.push(
					`Message at ${message.createdAt}\n${message.sender.name}: ${message.text}\n`
				);
			}
		}
		return messageTexts.join('\n');
	}

	private async getThreadMessages(
		room: IRoom,
		read: IRead,
		user: IUser,
		threadId: string
	): Promise<string> {
		const threadReader = read.getThreadReader();
		const thread = await threadReader.getThreadById(threadId);

		if (!thread) {
			await notifyMessage(room, read, user, 'Thread not found');
			throw new Error('Thread not found');
		}

		const messageTexts: string[] = [];
		for (const message of thread) {
			if (message.text) {
				messageTexts.push(`${message.sender.name}: ${message.text}`);
			}
		}

		// threadReader repeats the first message once, so here we remove it
		messageTexts.shift();
		return messageTexts.join('\n');
	}
}
