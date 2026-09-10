# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [1.1.0] - 10.9.2026

### Added

- Changelog :D
- .mobile-disabled css class for disabling elements on mobile

### Fixed

- **Removed main grids from all endpoints except for home (leftover from old navbar system)**
- Column info no longer appears on mobile
- Fixed spaces in znamka.css (2 -> 4)
- Improved global CSS
- Added missing padding in znamka

## [1.0.0] - 9.9.2026

### Added

- Safety check to get_semesters function abort if no semesters were found
- Semester handling to portfolio and subjects
- Subject semester change redirects to homepage as new request for all grades needs to be made (might change in future)

### Fixed

- If no semester is selected, the app tries to get one from the raw HTML
- Requests now use variable reference to session instead of directly getting it from the session
- Fixed portfolio wrapping on small screens
