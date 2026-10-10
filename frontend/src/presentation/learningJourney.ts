import {coreCommand} from "../api/core";
import {readCourse,type Course} from "../components/KnowledgeCoursePanel";
export type LearningJourneyTarget={item_key:string;knowledge_id:string;knowledge_version:string;assessment_id:string;source_id:string|null;anchor_id:string|null;course?:Course};
function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid learning identity");return value as Record<string,unknown>;}
export function assertJourneyAssessment(value:unknown,target:LearningJourneyTarget){const a=record(value);if(a.item_key!==target.item_key||a.assessment_id!==target.assessment_id||a.knowledge_id!==target.knowledge_id||a.knowledge_version!==target.knowledge_version||a.source_id!==target.source_id||a.anchor_id!==target.anchor_id)throw new Error("learning assessment identity changed");}
/** Read the exact persisted assessment; never create a substitute or select a search hit. */
export async function resolveLearningJourney(item_key:string):Promise<LearningJourneyTarget>{
 const a=record(await coreCommand("assessment_get",{item_key}));
 if(a.item_key!==item_key||typeof a.assessment_id!=="string"||!a.assessment_id||typeof a.knowledge_id!=="string"||!a.knowledge_id||a.knowledge_version!==a.knowledge_id||typeof a.question!=="string"||typeof a.content!=="string"||!(a.source_id===null||typeof a.source_id==="string")||!(a.anchor_id===null||typeof a.anchor_id==="string"))throw new Error("unverified assessment binding");
 const knowledge=record(await coreCommand("knowledge_get",{id:a.knowledge_id}));
 if(knowledge.knowledge_id!==a.knowledge_id||knowledge.status!=="accepted"||knowledge.source_id!==a.source_id||knowledge.anchor_id!==a.anchor_id)throw new Error("learning requires the exact accepted knowledge");
 let course:Course|undefined;
 if(item_key.startsWith("course:")){
  const match=/^course:([A-Za-z0-9][A-Za-z0-9_.-]{0,255}):artifact:([A-Za-z0-9][A-Za-z0-9_.-]{0,255})$/.exec(item_key);
  if(!match)throw new Error("invalid course learning key");
  course=readCourse(await coreCommand("course_get",{course_id:match[1]}),a.knowledge_id);
  if(course.id!==match[1]||course.artifactId!==match[2]||course.sourceId!==a.source_id)throw new Error("course learning identity mismatch");
 }
 return {item_key,knowledge_id:a.knowledge_id,knowledge_version:a.knowledge_id,assessment_id:a.assessment_id,source_id:a.source_id as string|null,anchor_id:a.anchor_id as string|null,course};
}
