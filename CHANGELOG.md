# Changelog

All notable changes to ArcheAxis Knowledge OS will be documented in this file.

## [Unreleased]

### To Be Added
- Real LLM integration (OpenAI/Anthropic)
- User authentication system
- Production deployment configuration
- Performance monitoring
- Caching layer

## [0.6.14] - 2026-10-17

### Added
- ✅ Complete FSRS-5 algorithm implementation
- ✅ Xiaoqi AI chat API endpoint
- ✅ File upload system (drag & drop + click)
- ✅ Batch upload functionality
- ✅ Learning statistics API
- ✅ Upload status checking
- ✅ AI service status monitoring
- ✅ End-to-end test suite
- ✅ Complete API documentation
- ✅ Deployment guide
- ✅ FileUpload React component with progress

### Improved
- 🔧 UI layout fixes (card stacking issues)
- 🔧 Navigation sidebar scrolling
- 🔧 Content overflow handling
- 🔧 Z-index layer management
- 🔧 Frontend build optimization (1.79MB bundle)

### Fixed
- 🐛 Xiaoqi missing images (listening, completed states)
- 🐛 Layout card overlap problems
- 🐛 Inspector panel positioning

### Changed
- 📝 Honest completion reporting (65% → 82%)
- 📝 Removed false "100% complete" claims
- 📝 Added realistic project status assessment

## [0.6.13] - 2026-10-16

### Added
- UI polish and interaction improvements
- TopNavBar hover effects
- GlobalSearch visual enhancements
- Xiaoqi trigger button animations

### Fixed
- Z-index conflicts in UI layers
- Search result item hover states

## [0.6.12] - Previous versions

### Core Features
- PDF reader with pdf.js integration
- EPUB paragraph reader
- Media player (audio/video)
- Learning review card UI
- Document editor
- Knowledge base API
- SQLite database schema

---

## Version Status

| Version | Date | Status | Completion |
|---------|------|--------|------------|
| 0.6.14 | 2026-10-17 | Current | 82% |
| 0.6.13 | 2026-10-16 | Stable | 65% |
| 0.6.12 | Earlier | Legacy | - |

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Release Process

1. Feature development in feature branches
2. Code review and testing
3. Version bump in package files
4. Update CHANGELOG.md
5. Git tag and release
6. Deploy to production (when ready)

---

Last Updated: 2026-10-17
Next Release: TBD
