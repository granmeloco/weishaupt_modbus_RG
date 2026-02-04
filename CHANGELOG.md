# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-02-05

### Added
- **Climate Platform**: Added proper climate (thermostat) entities for all heating circuits (HK1-HK5)
  - Native Home Assistant thermostat interface
  - Support for preset modes (Comfort, Normal, Eco)
  - HVAC modes (Auto, Heat, Off)
  - Works with all standard and custom thermostat cards
  - Integrates with existing modbus temperature controls
- **RG-Version branding**: Integration renamed to "Weishaupt WBB (RG-Version)" to differentiate from original

### Changed
- **Domain changed to `weishaupt_modbus_rg`**: Now a completely separate integration that can coexist with original
- Temperature controls now available as both number entities (existing) and climate entities (new)
- Users can choose between number sliders or thermostat cards for temperature control
- Added @granmeloco to codeowners

---

## Previous Versions (from original repository)

This is a fork of [OStrama/weishaupt_modbus](https://github.com/OStrama/weishaupt_modbus) with enhancements.

### [1.0.17]
- Adjusted mapping for 41102 Anforderung Typ
- Add PV Mode

### [1.0.16]
- Fix dynamic upper and lower bounds for multiple heating circuits

### [1.0.15]
- Fix values for multiple heatpumps

### [1.0.14]
- Fix device naming with multiple heatpumps

### [1.0.13]
- Fix HP reconnect

### [1.0.12]
- Fixed temp range for summer/winter switch

### [1.0.11]
- Update dependencies
- Merge SGR Status

### [1.0.10]
- Connecting of modbus has been optimized
- Bugfixing for dynamic limits

### [1.0.9]
- Weishaupt_modbus is now official part of HACS

### [1.0.8]
- Improved English translation and code enhancements

### [1.0.7]
- Removed matplotlib as a requirement

### [1.0.6]
- Corrected calculation of JAZ

### [1.0.5pre4]
- More calculated sensors supported
- Cubic splines for interpolation when scipy available
- Specific icons for entities
- Dynamic limits for setpoint temperatures
- Experimental Web-Interface support

### [1.0.4]
- Translation enabled
