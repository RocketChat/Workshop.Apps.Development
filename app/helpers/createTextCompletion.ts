import { IHttp, IRead } from '@rocket.chat/apps-engine/definition/accessors';
import { IRoom } from '@rocket.chat/apps-engine/definition/rooms';
import { IUser } from '@rocket.chat/apps-engine/definition/users';
import { notifyMessage } from './notifyMessage';
import { App } from '@rocket.chat/apps-engine/definition/App';

export async function createTextCompletion(
    app: App,
    room: IRoom,
    read: IRead,
    user: IUser,
    http: IHttp,
    prompt: string,
    threadId?: string
): Promise<string> {
    const model = await app
        .getAccessors()
        .environmentReader.getSettings()
        .getValueById('model');
    const url = `http://${model}/v1`;

    const body = {
        model,
        messages: [
            {
                role: 'system',
                content: prompt,
            },
        ],
        temperature: 0,
    };

    const response = await http.post(url + '/chat/completions', {
        headers: {
            'Content-Type': 'application/json',
        },
        content: JSON.stringify(body),
    });

    if (!response.content) {
        await notifyMessage(
            room,
            read,
            user,
            'Something is wrong with AI. Please try again later',
            threadId
        );
        throw new Error('Something is wrong with AI. Please try again later');
    }


    return JSON.parse(response.content).choices[0].message.content;
}
