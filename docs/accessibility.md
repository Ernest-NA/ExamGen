# Accessibility Guidelines

This document summarizes patterns used in ExamGen to meet WCAG 2.1 AA.

## Landmarks and Navigation
- Use `nav` with `role="navigation"` and descriptive `aria-label`.
- Provide a skip link at the top of every page pointing to `#main-content`.
- Wrap page content in `<main id="main-content" tabindex="-1">`.

## Focus and Keyboard
- All interactive elements must be reachable via keyboard.
- Visible focus is handled globally in `app.css` using the `:focus` selector.

## Tables
- Header cells use `scope="col"`.
- Tables include a caption or `aria-label` describing their purpose.

## Live Regions
- Status updates are announced using the `#status` element with `aria-live="polite"`.

These conventions should be followed when adding new templates or components.
