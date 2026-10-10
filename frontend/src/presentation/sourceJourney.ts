/** Ephemeral navigation identities; canonical content remains owned by Core. */
export type SourceJourneyTarget = {source_id:string;source_revision:string;sha256:string;job_id?:string};
export type CandidateJourneyTarget = SourceJourneyTarget & {knowledge_id:string;anchor_id:string;transform_id:number};
