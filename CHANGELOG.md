# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Guiding Principles:
* Changelogs are for humans, not machines.
* There should be an entry for every single version.
* The same types of changes should be grouped.
* Versions and sections should be linkable.
* The latest version comes first.
* The release date of each version is displayed.
* Mention whether you follow Semantic Versioning.

Types of changes:
Added - for new features
Changed - for changes in existing functionality
Deprecated - for soon-to-be removed features
Removed - for now removed features
Fixed - for any bug fixes
Security - in case of vulnerabilities
-->

## [0.2.0] - 2022-03-24

### Added

- Support for Deep PATCH for Olympus power limiting.
- Support for changing the 'ControlMode' field for Olympus power controls.
- Dynamic resources for the EventService allowing for subscribing to redfish events.
- Support for sending redfish events when compute system PowerState is affected.

### Changed

- Responses from dynamic resources are now all valid json.

## [0.1.0] - 2022-03-18

### Added

- This is the initial release.
- Supports Bard Peak emulation with dynamic resources for Power Capping, System ResetActions, and Firmware Update.
