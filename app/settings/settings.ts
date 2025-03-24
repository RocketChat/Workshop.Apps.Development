import {
	ISetting,
	SettingType,
} from '@rocket.chat/apps-engine/definition/settings';
export const settings: ISetting[] = [
	{
		id: 'model',
		i18nLabel: 'Model selection',
		i18nDescription: 'AI model to use for summarization.',
		type: SettingType.SELECT,
		values: [
			{ key: 'llama3-8b', i18nLabel: 'Llama3 8B' },
			{ key: 'mistral-7b:1234', i18nLabel: 'Mistral 7B' },
		],
		required: true,
		public: true,
		packageValue: 'llama3-8b',
	},
	{
		id: 'add-ons',
		i18nLabel: 'Summary add-ons',
		i18nDescription: 'Additional features to enable for the summary command',
		type: SettingType.MULTI_SELECT,
		values: [
			{ key: 'workshop-task', i18nLabel: 'Workshop task' },
			{ key: 'other-add-on', i18nLabel: 'Other Add on' },
		],
		required: false,
		public: true,
		packageValue: '',
	},
];
