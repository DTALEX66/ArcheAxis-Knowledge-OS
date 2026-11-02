/**
 * AAOS quiz-only adapter: original lines from scene-generator.ts are retained
 * verbatim. This does not expose the full generateSceneActions function.
 */
import { fileURLToPath } from 'node:url';
import { nanoid } from '../npm/nanoid-5.1.14/index.js';
import { noopGenerationLogger } from '../generation-0.3.28-outline/src/logger.ts';
import { buildPrompt as upstreamBuildPrompt, PROMPT_IDS } from '../generation-0.3.28-outline/src/prompts/index.ts';
import { buildCourseContext, formatAgentsForPrompt } from './src/prompt-formatters.ts';
import { parseActionsFromStructuredOutput as upstreamParser } from './src/action-parser.ts';
const buildPrompt = (id, vars) => upstreamBuildPrompt(id, vars, fileURLToPath(new URL('.', import.meta.url)));
let parserObservation = null;
function parseActionsFromStructuredOutput(...args) {
  const actions = upstreamParser(...args);
  parserObservation = { count: actions.length };
  return actions;
}
export function resetParserObservation() { parserObservation = null; }
export function getParserObservation() { return parserObservation; }
export async function replayQuizActionsBranch(outline, content, aiCall, options = {}) {
  if (outline.type !== 'quiz' || !('questions' in content)) throw new Error('QUIZ_ONLY');
  const { ctx, agents, userProfile, languageDirective } = options;
  const log = options.logger ?? noopGenerationLogger;
  const agentsText = formatAgentsForPrompt(agents);
  if (outline.type === 'quiz' && 'questions' in content) {
    // Format question list for AI reference
    const questionsText = formatQuestionsForPrompt(content.questions);

    const prompts = buildPrompt(PROMPT_IDS.QUIZ_ACTIONS, {
      title: outline.title,
      keyPoints: (outline.keyPoints || []).map((p, i) => `${i + 1}. ${p}`).join('\n'),
      description: outline.description,
      questions: questionsText,
      courseContext: buildCourseContext(ctx),
      agents: agentsText,
      languageDirective: languageDirective || '',
    });

    if (!prompts) {
      return generateDefaultQuizActions(outline);
    }

    const response = await aiCall(prompts.system, prompts.user);
    const actions = parseActionsFromStructuredOutput(response, outline.type, undefined, log);

    if (actions.length > 0) {
      return processActions(actions, [], agents, log);
    }

    return generateDefaultQuizActions(outline);
  }

  throw new Error('QUIZ_BRANCH_NOT_REACHED');
}
function formatQuestionsForPrompt(questions: QuizQuestion[]): string {
  return questions
    .map((q, i) => {
      const optionsText = q.options
        ? `Options: ${q.options.map((o) => `${o.value}. ${o.label}`).join(', ')}`
        : '';
      return `Q${i + 1} (${q.type}): ${q.question}\n${optionsText}`;
    })
    .join('\n\n');
}
function processActions(
  actions: Action[],
  elements: PPTElement[],
  agents?: AgentInfo[],
  log: GenerationLogger = noopGenerationLogger,
): Action[] {
  const elementIds = new Set(elements.map((el) => el.id));
  const agentIds = new Set(agents?.map((a) => a.id) || []);
  const studentAgents = agents?.filter((a) => a.role === 'student') || [];
  const nonTeacherAgents = agents?.filter((a) => a.role !== 'teacher') || [];

  return actions.map((action) => {
    // Ensure each action has an ID
    const processedAction: Action = {
      ...action,
      id: action.id || `action_${nanoid(8)}`,
    };

    // Validate spotlight elementId
    if (processedAction.type === 'spotlight') {
      const spotlightAction = processedAction;
      if (!spotlightAction.elementId || !elementIds.has(spotlightAction.elementId)) {
        // If elementId is invalid, try selecting the first element
        if (elements.length > 0) {
          spotlightAction.elementId = elements[0].id;
          log.warn(
            `Invalid elementId, falling back to first element: ${spotlightAction.elementId}`,
          );
        }
      }
    }

    // Validate/fill discussion agentId
    if (processedAction.type === 'discussion' && agents && agents.length > 0) {
      if (processedAction.agentId && agentIds.has(processedAction.agentId)) {
        // agentId valid — keep it
      } else {
        // agentId missing or invalid — pick a random student, or non-teacher, or skip
        const pool = studentAgents.length > 0 ? studentAgents : nonTeacherAgents;
        if (pool.length > 0) {
          const picked = pool[Math.floor(Math.random() * pool.length)];
          log.warn(
            `Discussion agentId "${processedAction.agentId || '(none)'}" invalid, assigned: ${picked.id} (${picked.name})`,
          );
          processedAction.agentId = picked.id;
        }
      }
    }

    return processedAction;
  });
}
function generateDefaultQuizActions(_outline: SceneOutline): Action[] {
  return [
    {
      id: `action_${nanoid(8)}`,
      type: 'speech',
      title: '测验引导',
      text: '现在让我们来做一个小测验，检验一下学习成果。',
    },
  ];
}
