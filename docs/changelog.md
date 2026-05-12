# Changelogs

## v0.0.8
### Feat

- Site motion pass: subtle scroll-triggered reveals on stats, persona cards, application/SDK/benchmark/AVL rows, callouts, diagrams, and section headings across all hand-authored landings
- Hover micro-interactions on cards, persona cards, applist rows, primary/outline buttons, topbar nav, and TOC links
- Copy-button success pulse on code blocks
- Unified `:focus-visible` ring for keyboard navigation

### Fixes

- Mobile responsiveness: hide hero decorative circle below 480px (fixes horizontal scroll on small phones)
- Wrap the QLI version mapping table in a horizontally scrollable container so it fits narrow viewports
- Add small-phone breakpoint (<480px): tighter hero/main padding, larger sidebar nav touch targets, version pill hidden to make room for the brand on <360px screens

### Chore

- Bumped version to v0.0.8 in topbar and notice banner across all 8 hand-authored landing pages
- All new motion respects `prefers-reduced-motion`; no-JS users see content immediately

## v0.0.7
### Feat

- Added Model Deploy as a new iQ-Studio feature
- Updated AVL camera support for 8-channel validation, broader interface coverage, and newer system compatibility
- Added Q911 getting-started and platform guidance
- Added Model Deploy navigation to the entry README
- Update the Q911 HW image

### Fixes

- Fixed documentation paths and internal links
- Refined documentation content, wording, and structure

### Chore
- Remove all "$" for user easy to copy command

## v0.0.6
### Feat

- Added topic title to the entry page for improved navigation
- Added benchmark for perception AI benchmark between QCS9075 and nvidia AGX 
- Added benchmark for multi-stream inference on Jetson AGX and Qualcomm QCS9075
- Update streampipe docker for benchmark testing

### Fixes

- Disabled TTY support for docker run command


## v0.0.5
### Feat
- Support application can run both yocto and ubuntu
- Added a complete flashing image workflow, including step-by-step instructions and updated diagrams
- Introduced a flashing image guide and refined related sections for better onboarding
- Removed BSP version restriction and added custom tag support to improve deployment flexibility
- Updated application runtime to support both Yocto and Ubuntu environments
- Added OS detection to the run script to improve cross-platform behavior
- Enabled automatic installation of required packages on Ubuntu

### Fixes
- Fixed incorrect path in the offline download flow entry page

### Documentation
- Updated README with refined notes and minimum disk usage information
- Improved section titles and descriptions for better readability
- Aligned flashing, offline usage, and installation documentation into a clearer flow

## v0.0.4
### Feat
- Add documentation for OGenie SDK
- Add documentation for GMSL camera
- Add documentation for MIPI camera

## v0.0.3
### Feat
- Add YOLOv10n inference integration
- Add streampipe for multi-stream inference

### Docs
- Update VLM model demo GIF
- Add documentation for streampipe SDK and applications
- Refine phrasing, spacing, and formatting

## v0.0.2
### Doc
- Add some extra descriptions and fix the typos
### Fix
- Fix the metadata.json format

## v0.0.1
### Feat
- Add iQ Studio architecture documentation
- Add Q911 hardware introduction 
- Add VLM / YOLOv10n introduction and usage guide 
- Add iqs-launcher script and usage instructions 
- Add innoPPE benchmark content
