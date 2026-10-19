export type ImportReceipt = { source_id: string; sha256: string; duplicate: boolean };

/** Bind custody acknowledgement to the bytes submitted, before enabling conversion. */
export function confirmedImport(value: unknown, expectedSha256: string): ImportReceipt {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("导入回执未确认；请保留原件并重试。");
  const receipt = value as Partial<ImportReceipt>;
  if (typeof receipt.source_id !== "string" || !receipt.source_id.trim()
    || typeof receipt.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(receipt.sha256)
    || typeof receipt.duplicate !== "boolean") throw new Error("导入回执未确认 source_id/sha256/duplicate；请保留原件并重试。");
  if (receipt.sha256 !== expectedSha256) throw new Error("导入回执与上传原件的 SHA-256 不符；保管未确认，请保留原件，未启动转换。");
  return receipt as ImportReceipt;
}
