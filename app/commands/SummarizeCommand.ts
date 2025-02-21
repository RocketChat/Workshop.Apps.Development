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
	createFileSummaryPrompt,
	createFollowUpQuestionsPrompt,
	createParticipantsSummaryPrompt,
	createPromptInjectionProtectionPrompt,
	createSummaryPrompt,
	createSummaryPromptByTopics,
} from '../constants/prompts';
import { App } from '@rocket.chat/apps-engine/definition/App';
import { IMessageRaw } from '@rocket.chat/apps-engine/definition/messages';

export class SummarizeCommand implements ISlashCommand {
	public command = 'chat-summary-amarta';
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
		const xAuthToken = await this.app
			.getAccessors()
			.environmentReader.getSettings()
			.getValueById('x-auth-token');
		const xUserId = await this.app
			.getAccessors()
			.environmentReader.getSettings()
			.getValueById('x-user-id');

		let messages: string;
		if (!threadId) {
			messages = await this.getRoomMessages(
				room,
				read,
				user,
				http,
				addOns,
				xAuthToken,
				xUserId
			);
		} else {
			messages = await this.getThreadMessages(
				room,
				read,
				user,
				http,
				threadId,
				addOns,
				xAuthToken,
				xUserId
			);
		}

		await notifyMessage(room, read, user, messages, threadId);

		// const promptInjectionProtectionPrompt =
		// 	createPromptInjectionProtectionPrompt(messages);
		// const isPromptInjection = await createTextCompletion(
		// 	this.app,
		// 	room,
		// 	read,
		// 	user,
		// 	http,
		// 	promptInjectionProtectionPrompt,
		// 	threadId
		// );
		// if (isPromptInjection) {
		// 	await notifyMessage(
		// 		room,
		// 		read,
		// 		user,
		// 		'Prompt injection detected! You are not allowed to summarize messages that have potential attack to the AI model',
		// 		threadId
		// 	);
		// 	throw new Error('Prompt injection detected');
		// }

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

		if (addOns.includes('assigned-tasks')) {
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

		if (addOns.includes('follow-up-questions')) {
			const followUpQuestionsPrompt = createFollowUpQuestionsPrompt(messages);
			const followUpQuestions = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				followUpQuestionsPrompt,
				threadId
			);
			await notifyMessage(room, read, user, followUpQuestions, threadId);
		}

		if (addOns.includes('participants-summary')) {
			const participantsSummaryPrompt =
				createParticipantsSummaryPrompt(messages);
			const participantsSummary = await createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				participantsSummaryPrompt,
				threadId
			);
			await notifyMessage(room, read, user, participantsSummary, threadId);
		}
	}

	private async getFileSummary(
		fileId: string,
		read: IRead,
		room: IRoom,
		user: IUser,
		http: IHttp,
		xAuthToken: string,
		xUserId: string,
		threadId?: string
	): Promise<string> {
		const uploadReader = read.getUploadReader();
		const file = await uploadReader.getById(fileId);
		if (file && file.type === 'text/plain') {
			const response = await fetch(file.url, {
				method: 'GET',
				headers: {
					'X-Auth-Token': xAuthToken,
					'X-User-Id': xUserId,
				},
			});
			const fileContent = await response.text();
			const fileSummaryPrompt = createFileSummaryPrompt(fileContent);
			return createTextCompletion(
				this.app,
				room,
				read,
				user,
				http,
				fileSummaryPrompt,
				threadId
			);
		}
		return 'File type is not supported';
	}

	private async getRoomMessages(
		room: IRoom,
		read: IRead,
		user: IUser,
		http: IHttp,
		addOns: string[],
		xAuthToken: string,
		xUserId: string
	): Promise<string> {
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
			if (addOns.includes('file-summary') && message.file) {
				if (!xAuthToken || !xUserId) {
					await notifyMessage(
						room,
						read,
						user,
						'Personal Access Token and User ID must be filled in settings to enable file summary add-on'
					);
					continue;
				}
				const fileSummary = await this.getFileSummary(
					message.file._id,
					read,
					room,
					user,
					http,
					xAuthToken,
					xUserId
				);
				messageTexts.push('File Summary: ' + fileSummary);
			}
		}
		return messageTexts.join('\n');
	}

	private async getThreadMessages(
		room: IRoom,
		read: IRead,
		user: IUser,
		http: IHttp,
		threadId: string,
		addOns: string[],
		xAuthToken: string,
		xUserId: string
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
			if (addOns.includes('file-summary') && message.file) {
				if (!xAuthToken || !xUserId) {
					await notifyMessage(
						room,
						read,
						user,
						'Personal Access Token and User ID must be filled in settings to enable file summary add-on'
					);
					continue;
				}
				const fileSummary = await this.getFileSummary(
					message.file._id,
					read,
					room,
					user,
					http,
					xAuthToken,
					xUserId,
					threadId
				);
				messageTexts.push('File Summary: ' + fileSummary);
			}
		}

		// threadReader repeats the first message once, so here we remove it
		messageTexts.shift();
		return messageTexts.join('\n');
	}
}
