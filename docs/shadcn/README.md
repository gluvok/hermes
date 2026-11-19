# Hermes shadcn/ui Component Documentation

This directory maintains component reference specifications for all shadcn/ui components used in Hermes edge dashboards and kiosk interfaces.

## Standards & Principles
1. **Janus Palette Alignment**: All components adopt the Janus OKLCH semantic palette (`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--accent`, `--destructive`).
2. **Offline Durability**: Components must render deterministically on local Raspberry Pi displays without external CDN dependencies.
3. **Touch-First Sizing**: Interactive controls on the operator kiosk have minimum hit targets of 44px (`size-11` or larger).

## Component Index
- [Badge](badge.md) - Status indicators for ANPR confidence, scale stability, and Wi-Fi mode.
- [Button](button.md) - Action triggers for manual weighment capture, tare, and zero.
- [Card](card.md) - Container surfaces for operator HUD cards and telemetry panels.
- [Dialog](dialog.md) - Modal dialogs for manual plate override and system reboot confirmation.
- [Sheet](sheet.md) - Slide-over drawer for maintainer hardware diagnostics and calibration.
- [Slider](slider.md) - Threshold adjustments for scale debounce and OCR confidence cutoff.
- [Tabs](tabs.md) - Segmented controls for switching between Operator Kiosk and Developer Console.
