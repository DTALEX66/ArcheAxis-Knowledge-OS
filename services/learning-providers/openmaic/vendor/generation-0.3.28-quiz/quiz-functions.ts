/**
 * Local adapter around the byte-identical OpenMAIC quiz functions.
 * The functions below are upstream scene-generator.ts lines 914-1108.
 * Only imports/prompt root and the final export are added by AAOS.
 */
import { fileURLToPath } from 'node:url';
import { nanoid } from '../npm/nanoid-5.1.14/index.js';
import { parseJsonResponse } from '../generation-0.3.28-outline/src/json-repair.ts';
import { noopGenerationLogger } from '../generation-0.3.28-outline/src/logger.ts';
import { buildPrompt as upstreamBuildPrompt, PROMPT_IDS } from '../generation-0.3.28-outline/src/prompts/index.ts';

const buildPrompt = (id, variables) => upstreamBuildPrompt(id, variables, fileURLToPath(new URL('.', import.meta.url)));

async function generateQuizContent(
  outline: SceneOutline,
  aiCall: AICallFn,
  languageDirective?: string,
  log: GenerationLogger = noopGenerationLogger,
  onFailure?: (failure: SceneContentFailure) => void,
): Promise<GeneratedQuizContent | null> {
  const quizConfig = outline.quizConfig || {
    questionCount: 3,
    difficulty: 'medium',
    questionTypes: ['single'],
  };

  const prompts = buildPrompt(PROMPT_IDS.QUIZ_CONTENT, {
    title: outline.title,
    description: outline.description,
    keyPoints: (outline.keyPoints || []).map((p, i) => `${i + 1}. ${p}`).join('\n'),
    questionCount: quizConfig.questionCount,
    difficulty: quizConfig.difficulty,
    questionTypes: quizConfig.questionTypes.join(', '),
    languageDirective: languageDirective || '',
  });

  if (!prompts) {
    onFailure?.({ code: 'prompt-unavailable' });
    return null;
  }

  log.debug(`Generating quiz content for: ${outline.title}`);
  const response = await aiCall(prompts.system, prompts.user);
  const generatedQuestions = parseJsonResponse<QuizQuestion[]>(response);

  if (!generatedQuestions || !Array.isArray(generatedQuestions)) {
    log.error(`Failed to parse AI response for: ${outline.title}`);
    onFailure?.({ code: 'invalid-model-output' });
    return null;
  }

  log.debug(`Got ${generatedQuestions.length} questions for: ${outline.title}`);

  // Ensure each question has an ID and normalize options format.
  // Plain strings become letter/content pairs. Object fields stay as written.
  const questions: QuizQuestion[] = generatedQuestions.map((q) => {
    const isText = q.type === 'short_answer';
    const options = isText ? undefined : normalizeQuizOptions(q.options);
    return {
      ...q,
      id: q.id || `q_${nanoid(8)}`,
      options,
      answer: isText
        ? undefined
        : normalizeQuizAnswer(q as unknown as Record<string, unknown>, options),
      hasAnswer: isText ? false : true,
    };
  });

  const contractFailure = findQuizOptionsContractFailure(questions);
  if (contractFailure) {
    log.error(`Quiz option contract failed for "${outline.title}": ${contractFailure}`);
    onFailure?.({ code: 'invalid-model-output' });
    return null;
  }

  return { questions };
}

const QUIZ_OPTION_VALUE = /^[A-Z]$/;

/**
 * Reason a built quiz breaks the choice-option contract, or null when it holds.
 *
 * Choice questions (everything except `short_answer`) need a non-empty option
 * list whose `value`s are single ASCII letters A-Z, and every answer entry
 * must equal one of those values exactly. Short-answer questions are skipped.
 */
export function findQuizOptionsContractFailure(questions: readonly QuizQuestion[]): string | null {
  for (let index = 0; index < questions.length; index += 1) {
    const question = questions[index];
    if (!question || question.type === 'short_answer') continue;

    const where = question.id ? `question ${index + 1} (${question.id})` : `question ${index + 1}`;
    const options = question.options;
    if (!options || options.length === 0) {
      return `${where}: choice question has no options`;
    }

    const optionValues = new Set<string>();

    for (let optionIndex = 0; optionIndex < options.length; optionIndex += 1) {
      const value = options[optionIndex]?.value;
      if (typeof value !== 'string' || !QUIZ_OPTION_VALUE.test(value)) {
        const shown = JSON.stringify(value);
        return `${where}: option ${optionIndex + 1} value ${shown} is not a single letter A-Z`;
      }

      if (optionValues.has(value)) {
        return `${where}: option ${optionIndex + 1} repeats value ${JSON.stringify(value)}`;
      }

      optionValues.add(value);
    }

    const answer = question.answer;
    if (!answer || answer.length === 0) {
      return `${where}: answer key does not reference an option value`;
    }

    for (const entry of answer) {
      if (!optionValues.has(entry)) {
        return `${where}: answer ${JSON.stringify(entry)} does not match an option value`;
      }
    }
  }

  return null;
}

type NormalizedQuizOption = { value: string; label: string };

/**
 * Normalize quiz options from AI response.
 * AI may generate plain strings ["OptionA", "OptionB"] or QuizOption objects.
 * Plain strings become { value: "A", label: "OptionA" }. Object `value` and
 * `label` are kept as provided — a letter in `label` with content in `value`
 * is not swapped.
 */
export function normalizeQuizOptions(
  options: unknown[] | undefined,
): NormalizedQuizOption[] | undefined {
  if (!options || !Array.isArray(options)) return undefined;

  return options.map((opt, index) => {
    const letter = String.fromCharCode(65 + index); // A, B, C, D...

    if (typeof opt === 'string') {
      return { value: letter, label: opt };
    }

    if (typeof opt === 'object' && opt !== null) {
      const obj = opt as Record<string, unknown>;
      return {
        value: typeof obj.value === 'string' ? obj.value : letter,
        label: typeof obj.label === 'string' ? obj.label : String(obj.value || obj.text || letter),
      };
    }

    return { value: letter, label: String(opt) };
  });
}

/**
 * Normalize quiz answer from AI response.
 * AI may generate correctAnswer as string or string[], under various field names.
 * This normalizes to string[] format matching option values.
 *
 * The LLM writes the answer key inconsistently, as option CONTENT ("(6, 2)")
 * or as a LETTER ("A"). Only exact, unique alignment is resolved: an entry
 * that equals exactly one option value, or exactly one option label, becomes
 * that option's value. Formatting variants (case, whitespace, full-width
 * forms, wrapper punctuation) are NOT normalized, and ambiguous entries (two
 * options sharing a value or a label) are left untouched — consistent with
 * the grading-side resolver, which must not accept a variant a stored key
 * would never resolve to.
 */
export function normalizeQuizAnswer(
  question: Record<string, unknown>,
  options?: { value: string; label: string }[],
): string[] | undefined {
  // AI might use "correctAnswer", "answer", or "correct_answer"
  const raw =
    question.answer ??
    question.correctAnswer ??
    (question as Record<string, unknown>).correct_answer;
  if (!raw) return undefined;

  const answers = (Array.isArray(raw) ? raw : [raw]).map(String);

  if (!options || options.length === 0) {
    return answers;
  }

  // Exact alignment only (per review): value or label must match the answer
  // byte-for-byte; no case folding, whitespace/Unicode normalization, or
  // wrapper interpretation. Fail closed on ambiguity: convert only when
  // exactly one distinct option value matches.
  return answers.map((a) => {
    const valueMatches = options.filter((o) => o.value === a);
    const labelMatches = options.filter((o) => o.label === a);
    const candidates = new Set<string>();
    for (const o of valueMatches) candidates.add(o.value);
    for (const o of labelMatches) candidates.add(o.value);
    if (candidates.size === 1) return [...candidates][0];
    return a;
  });
}

export { generateQuizContent };
