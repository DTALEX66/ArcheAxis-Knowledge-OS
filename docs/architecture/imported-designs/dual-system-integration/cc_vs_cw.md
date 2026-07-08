# CC vs CW Source Comparison

## Size Comparison
| Metric | CC Source (CC) | CW Source (CW) |
|--------|-----------------|-----------------|
| Total files | ~1900+ | ~80+ |
| Language | TypeScript | Python |
| Lines of code | ~512,000 | ~30,000 |
| Status | Leaked v2.1.88 | Active port/development |
| License | Proprietary (Source) | Apache 2.0 |
| Runtime | Bun | Python 3.10+ |

## Key Differences
- CC: Full industrial agent harness with real API integration
- CW: Python port focused on architecture replication
- CC has 40+ built-in tools vs CW's ~15
- CC has complex sandbox/security system missing in CW
- CW has cleaner Python idioms (dataclasses, async generators)

## Integration Strategy
- Use CC for: complex patterns (Zod chain, sandbox, bridge)
- Use CW for: Python-native structure, permission system, clean interfaces
- KB combines: CC's depth + CW's language fit + original FSRS/review system
