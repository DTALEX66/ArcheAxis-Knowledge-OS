/** Ephemeral navigation identities; canonical content remains owned by Core. */
import type { FolderMemberSelection } from "./ingestRelations";
export type SourceJourneyTarget = {source_id:string;source_revision:string;sha256:string;job_id?:string;folder_member?:FolderMemberSelection};
export type CandidateJourneyTarget = SourceJourneyTarget & {knowledge_id:string;anchor_id:string;transform_id:number};
