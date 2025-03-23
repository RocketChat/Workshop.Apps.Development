const SUMMARY_PROMPT = `Summarize the following dialogue using 1-3 short and simple sentences. Use as fewer words as possible. Mention the names of specific persons.

Dialogue: ###
Tim: Hi, what's up? Kim: Bad mood tbh, I was going to do lots of stuff but ended up procrastinating Tim: What did you plan on doing? Kim: Oh you know, uni stuff and unfucking my room Kim: Maybe tomorrow I'll move my ass and do everything Kim: We were going to defrost a fridge so instead of shopping I'll eat some defrosted veggies Tim: For doing stuff I recommend Pomodoro technique where u use breaks for doing chores Tim: It really helps Kim: thanks, maybe I'll do that Tim: I also like using post-its in kaban style
###

Summary: Kim may try the pomodoro technique recommended by Tim to get more stuff done.

---

Summarize the following dialogue using 1-3 short and simple sentences. Use as fewer words as possible. Mention the names of specific persons.

Dialogue: ###
John: Ave. Was there any homework for tomorrow? Cassandra: hello :D Of course, as always :D John: What exactly? Cassandra: I'm not sure so I'll check it for you in 20minutes. John: Cool, thanks. Sorry I couldn't be there, but I was busy as fuck...my stupid boss as always was trying to piss me off Cassandra: No problem, what did he do this time? John: Nothing special, just the same as always, treating us like children, commanding to do this and that... Cassandra: sorry to hear that. but why don't you just go to your chief and tell him everything? John: I would, but I don't have any support from others, they are like goddamn pupets and pretend that everything's fine...I'm not gonna fix everything for everyone Cassandra: I understand...Nevertheless, just try to ignore him. I know it might sound ridiculous as fuck, but sometimes there's nothing more you can do. John: yeah I know...maybe some beer this week? Cassandra: Sure, but I got some time after classes only...this week is gonna be busy John: no problem, I can drive you home and we can go to some bar or whatever. Cassandra: cool. ok, I got this homework. it's page 15 ex. 2 and 3, I also asked the others to study another chapter, especially the vocabulary from the very first pages. Just read it. John: gosh...I don't know if I'm smart enough to do it :'D Cassandra: you are, don't worry :P Just circle all the words you don't know and we'll continue on Monday. John: ok...then I'll try my best :D Cassandra: sure, if you will have any questions just either text or call me and I'll help you. John: I hope I won't have to waste your time xD Cassandra: you're not wasting my time, I'm your teacher, I'm here to help. This is what I get money for, also :P John: just kidding :D ok, so i guess we'll stay in touch then Cassandra: sure, have a nice evening :D John: you too, se ya Cassandra: Byeeeee
###

Summary: John didn't show up for class due to some work issues with his boss. Cassandra, his teacher told him which exercises to do, and which chapter to study. They are going to meet up for a beer sometime this week after class.

---

Summarize the following dialogue using 1-3 short and simple sentences. Use as fewer words as possible. Mention the names of specific persons.

Dialogue: ###
Leon: did you find the job yet? Arthur: no bro, still unemployed :D Leon: hahaha, LIVING LIFE Arthur: i love it, waking up at noon, watching sports - what else could a man want? Leon: a paycheck? ;) Arthur: don't be mean... Leon: but seriously, my mate has an offer as a junior project manager at his company, are you interested? Arthur: sure thing, do you have any details? Leon: <file_photo> Arthur: that actually looks nice, should I reach out directly to your friend or just apply to this email address from the screenshot? Leon: it's his email, you can send your resume directly and I will mention to him who you are :)
###

Summary: Arthur is still unemployed. Leon sends him a job offer for junior project manager position. Arthur is interested.

---

Summarize the following dialogue. Mention the names of specific persons. Only give the summary, nothing else.

Dialogue: ###
{dialogue}
###

Summary: `;

export function createSummaryPrompt(dialogue: string): string {
	return SUMMARY_PROMPT.replace('{dialogue}', dialogue);
}

const OTHER_ADD_ON_PROMPT = `
say hi and try to make a conversation

Dialogue to analyze:
{dialogue}
`;

export function createOtherAddonPrompt(dialogue: string): string {
	return OTHER_ADD_ON_PROMPT.replace('{dialogue}', dialogue);
}

const SUMMARY_PROMPT_BY_TOPICS = `
Dialogue: ###
{dialogue}
###

Summarize the above dialogue by topics.

Only messages that are relevant to each other should be grouped together in a topic. It's ok to only have 1 or 2 topic(s) if the dialogue is not very diverse.

Each topic should be summarized in 1-3 things discussed. Mention the names of specific persons.

The output format for each topic should strictly follow the following structure:
*{topic 1}*
- {1 thing discussed}
- {1 thing discussed}
- {1 thing discussed}

*{topic 2}*
- {1 thing discussed}
- {1 thing discussed}
- {1 thing discussed}

For example:
*Meeting to discuss LLMs*
- Aaron Wu shared details about accessing & trying out LLMs on the RC server
- Steps were provided for creating an account, creating a RC App, and uploading it to the server
- Peter Xu mentioned that CI workflow seems like a better idea than pre-commit hooks

*Fixing linting errors*
- Aaron Wu fixed most of the linting errors but encountered issues with UiKitModal file
- The file was found to be missing, so Aaron Wu disabled the linting errors and pushed the commit
- Jeffrey Yu can review the changes in PR #472

*Database Migration Plan Discussion*
- Bob suggested automating the rollback process for quick execution if needed
- The plan was updated to extend post-migration monitoring to two weeks
- Alice agreed with the updates and asked Bob to start working on data conversion scripts

Only give the output using the format above and nothing else.
`;

export function createSummaryPromptByTopics(dialogue: string): string {
	return SUMMARY_PROMPT_BY_TOPICS.replace('{dialogue}', dialogue);
}

//TODO: Prompt you have to modify
const ASSIGNED_TASKS_PROMPT = `
Analyze the following dialogue to identify any assigned tasks. An assigned task is typically indicated by phrases where one person delegates an action to another person or team, often specifying what needs to be done and by whom. Highlight these assigned tasks, including any relevant details such as deadlines or specific instructions.

Your task is to extract and present the assigned tasks clearly. For each assigned task, provide the following details:
Task Title
- Description
- Assignee
- Deadline (if mentioned)

Strictly follow the output format and output nothing else.
Only output assigned tasks if mentioned obviously in the dialogue. Be strict. If no obvious assign tasks are mentioned, simply output "No assigned task mentioned" and nothing else.

Dialogue to analyze:
{dialogue}
`;

export function createAssignedTasksPrompt(dialogue: string): string {
	return ASSIGNED_TASKS_PROMPT.replace('{dialogue}', dialogue);
}
