import { assertAiAssetDto, type AiAsset, type AssetContextGrant, type AssetPacketRequest, type AssetPacketResponse } from "./generated/ai-asset-contract";
import { coreCommand } from "./core";
export function parseAiAsset(value: unknown): AiAsset | null { try { return assertAiAssetDto<AiAsset>("AiAsset",value); } catch { return null; } }
export function parseAssetGrant(value: unknown): AssetContextGrant | null { try { return assertAiAssetDto<AssetContextGrant>("AssetContextGrant",value); } catch { return null; } }
export function prepareAssetPacket(request: AssetPacketRequest): Promise<AssetPacketResponse> { return coreCommand<AssetPacketResponse>("ai_asset_packet",{body:request}); }
