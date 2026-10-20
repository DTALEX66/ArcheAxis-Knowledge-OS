// Generated from exact builtin manifest and public validator inputs. Declaration only.
import type { CapabilityManifestIdentity, CapabilityPackageManifest } from './capability-package';
export type CapabilityPackageDetail = {
  identity: CapabilityManifestIdentity; manifest: CapabilityPackageManifest; source_path: string;
  validation: 'VALIDATED_DECLARATION'; host_version: string;
  source_authenticity: 'UNVERIFIED'; qualification: 'UNKNOWN'; runtime: 'UNKNOWN';
};
export type CapabilityPackageDetailProjection = {
  sources: { path: string; sha256: string }[]; entries: CapabilityPackageDetail[];
};
export const CAPABILITY_PACKAGE_DETAILS: CapabilityPackageDetailProjection = {
  "sources": [
    {
      "path": "config/capability-map.v1.json",
      "sha256": "d5873a524c04d5b6213dbd3f5f39d20c0056e5fc96e4d3c977daf7d4f572ed0e"
    },
    {
      "path": "config/capability-packages/pdf-extract.manifest.json",
      "sha256": "8f53e26d96f72fb67eb594c08d5f10e001a09e0280b848ec171be728e9fb7df9"
    },
    {
      "path": "crates/archeaxis-api/Cargo.toml",
      "sha256": "92aefb0bc36e94865983dfb768bdcc3abb1bbe41c204d503280f693df2da19ad"
    },
    {
      "path": "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json",
      "sha256": "cdf7819c9c64e4551c8b88e450707b7e5d4340f0f5349fd187d0bc44f007cf97"
    },
    {
      "path": "packages/contracts/v1/core-document.schema.json",
      "sha256": "3d02bad30f9dde3d0830d74a8b48fad9c73fb02f2393b5922ee0c9afcbb7aee6"
    },
    {
      "path": "packages/contracts/v2/capability-package.schema.json",
      "sha256": "248b38fbaf6ce16b87e7acdd4395f4515ba082977da0d6538fe8c14f9ac02d2f"
    },
    {
      "path": "scripts/contracts/check_capability_package_details.mjs",
      "sha256": "3411ea2086c532ab848f1d0e371177c01c759d9ba3f1511d2df92198825ee215"
    },
    {
      "path": "scripts/contracts/generate_capability_package_details.py",
      "sha256": "f71cfac89b083a8c668c8cbffb45a2d861e02f435e6b2d6a03a3334b84063a12"
    },
    {
      "path": "scripts/contracts/validate_capability_package.py",
      "sha256": "7575d12775fbbec60b697da10cd53f003f177845c735b90f4d2afdc6093eaef1"
    },
    {
      "path": "services/python-workers/routes.json",
      "sha256": "0ac3068fe9a9179eb6575609305d3eaf88e7d9d485a0794b7948333c0a70706f"
    }
  ],
  "entries": [
    {
      "identity": {
        "schema": "archeaxis.capability-package/v1",
        "package_id": "archeaxis.pdf-extract",
        "version": "0.1.0",
        "sha256": "8f53e26d96f72fb67eb594c08d5f10e001a09e0280b848ec171be728e9fb7df9"
      },
      "manifest": {
        "schema": "archeaxis.capability-package/v1",
        "declaration": "DECLARATION_ONLY",
        "package_id": "archeaxis.pdf-extract",
        "version": "0.1.0",
        "capability_ids": [
          "CAP-0020"
        ],
        "resource_keys": [
          "pymupdf"
        ],
        "contribution_points": [
          "format_conversion"
        ],
        "compatibility": {
          "host_versions": {
            "minimum": "0.1.0",
            "maximum_exclusive": "1.0.0"
          },
          "contract_refs": [
            {
              "path": "packages/contracts/v1/core-document.schema.json",
              "sha256": "3d02bad30f9dde3d0830d74a8b48fad9c73fb02f2393b5922ee0c9afcbb7aee6"
            }
          ]
        },
        "runtime_capabilities": [
          "pdf.extract"
        ],
        "permissions": {
          "requested": [
            "selected_source.read",
            "derived_artifact.propose"
          ],
          "data_scope": "explicit_selected_objects_only",
          "network": "none",
          "cost": "none",
          "explicit_grant_required": true,
          "canonical_writer": "rust_core_only",
          "credential_handling": "host_reference_only",
          "local_to_cloud_fallback": "explicit_grant_only",
          "grants_execution": false,
          "grants_knowledge_acceptance": false
        },
        "dependencies": [
          {
            "resource_key": "pymupdf",
            "requirement": "required",
            "version_range": null
          }
        ],
        "license": {
          "expression": null,
          "review": "UNVERIFIED",
          "notice_refs": []
        },
        "inputs": [
          {
            "kind": "raw_asset_reference",
            "contract": {
              "path": "packages/contracts/v1/core-document.schema.json",
              "sha256": "3d02bad30f9dde3d0830d74a8b48fad9c73fb02f2393b5922ee0c9afcbb7aee6"
            },
            "max_bytes": 1048576
          }
        ],
        "outputs": [
          {
            "kind": "document_reference",
            "contract": {
              "path": "packages/contracts/v1/core-document.schema.json",
              "sha256": "3d02bad30f9dde3d0830d74a8b48fad9c73fb02f2393b5922ee0c9afcbb7aee6"
            },
            "max_bytes": 1048576
          }
        ],
        "lifecycle": {
          "cancellation": "host_propagated",
          "exit": "bounded_cleanup",
          "timeout_ms": 120000,
          "unknown_result": "preserve_unknown_no_auto_retry",
          "cleanup_evidence": "required_before_confirmed_exit"
        },
        "fallback": {
          "mode": "unavailable",
          "losses": [],
          "automatic": false
        },
        "update": {
          "strategy": "reviewed_replacement_only",
          "rollback": "preserve_previous_identity_and_originals",
          "canonical_data_migration": false
        }
      },
      "source_path": "config/capability-packages/pdf-extract.manifest.json",
      "validation": "VALIDATED_DECLARATION",
      "host_version": "0.1.0",
      "source_authenticity": "UNVERIFIED",
      "qualification": "UNKNOWN",
      "runtime": "UNKNOWN"
    }
  ]
};
