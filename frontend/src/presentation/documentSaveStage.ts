/** A journal refusal is not a Document CAS conflict: no body was sent. */
export class DocumentJournalError extends Error {
  constructor(public readonly failure:unknown) {
    super("工作草稿保全未确认，正文未发送。");
  }
}
