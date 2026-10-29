# Apple-guided interface

Reviewed October 28, 2026. This pass follows the applicable Apple writing and interface guidance for Harness as a browser-based task workbench.

## Decisions and sources

| Area | Applied to Harness | Source |
| --- | --- | --- |
| Purpose and simplicity | Task entry, usage and sessions remain primary. Removed decorative color, duplicate explanations and the dark project rail. | [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles) |
| Voice | Direct, neutral wording; consistent task, session, model and project vocabulary. Removed unnecessary possessives and shortened setup instructions. | [Writing](https://developer.apple.com/design/human-interface-guidelines/writing) |
| Editorial consistency | Title-style button labels, sentence-style descriptions and messages, consistent product names, descriptive links, and ellipses for the project dialog. Folder paths use the regular interface font. | [Apple Style Guide](https://support.apple.com/guide/applestyleguide/welcome/web), [Capitalization and code font](https://support.apple.com/guide/applestyleguide/c-apsgb744e4a3/web) |
| Type | Platform system font; 17px default body, 30px desktop title, 14px secondary text. Relative font units allow enlargement. No thin weights or downloaded Apple fonts. | [Typography](https://developer.apple.com/design/human-interface-guidelines/typography) |
| Hierarchy | Quiet gray sidebar, white content, restrained blue interactive accents, clear task grouping and consistent alignment. Previous audit improvements remain. | [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) |
| Controls | One prominent task action, equal-height controls, visible hover/press/focus states, and 44px minimum button hit regions. Pending actions expose aria-busy. | [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) |
| Sidebar | Optional on desktop, with a persistent Show/Hide Sidebar control. Compact navigation remains accessible on narrow windows. | [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars) |
| Appearance | Semantic custom color tokens with light, dark and increased-contrast variants. Status uses words as well as color. Native forced-color mode remains supported. | [Color](https://developer.apple.com/design/human-interface-guidelines/color) |
| Recovery | Clearing a draft offers Undo. Errors in project/model dialogs and provider setup appear within that context. Existing per-project drafts, preferences, and inline task errors remain. | [Writing](https://developer.apple.com/design/human-interface-guidelines/writing), [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles) |
| Local model confirmation | Uses a labeled browser-native dialog with Cancel and Start Model. The cancel action receives initial focus. Escape cancels before confirmation; pending requests expose a busy state. GPU stop remains immediate. | [Alerts](https://developer.apple.com/design/human-interface-guidelines/alerts) |
| Accessibility | Keyboard controls, labels, skip navigation, text enlargement, contrast variants, reduced motion and noncolor status information. Content reflows with container queries. | [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) |
| Usage | Home-page usage bars remain accurate and static allowance meters, with explicit unknown states and provider links. They are not presented as task completion indicators. | [Progress indicators](https://developer.apple.com/design/human-interface-guidelines/progress-indicators) |

## Platform application

The guidance covers several Apple platforms. Harness is a web app, so AppKit/SwiftUI controls, native Liquid Glass materials, menu-bar integration, Siri, haptics, SF Symbols and native Dynamic Type APIs are not web features implemented here. The browser implementation uses semantic HTML, native form controls and dialogs, system font selection, responsive layout and appearance preferences. It does not imitate an Apple product or include Apple logos or proprietary interface assets.

The requested larger typography takes precedence over using the smaller native macOS default. Browser text enlargement is tested separately from native Dynamic Type. Physical display/True Tone behavior and VoiceOver on an actual Mac were not tested.

## Checks and deployment

- Existing functional Playwright suite passes at 320, 390, 768, 1024, 1280 and 1440px.
- All three screens checked in light/dark and standard/increased contrast at phone/desktop widths.
- Resolved primary-button and secondary-text contrast ratios meet 4.5:1 in the tested appearances.
- 200% text reflows on all screens at 390 and 1440px. Forced colors and reduced motion checked.
- Keyboard sidebar toggling/persistence, draft Undo, local-dialog cancellation, and inline project-dialog errors checked with mocked requests.
- Existing task submission, session search/scope/links, drafts, focus during polling and failure/disconnect recovery remain covered.
- 26 Python tests pass. No live model generation was run.
- Read-only Playwright audit of the deployed panel passes without JavaScript errors or horizontal overflow. Live evidence is in artifacts/ui-evidence/audit-apple; appearance fixtures use fictional data.
- Synced only ui/index.html to the installed runtime, preserving index.before-apple-style.html. Updated the HTML manifest entry. No service restart. Existing release ZIPs unchanged.

The workspace was reorganized during this work. Documentation and evidence use its current docs/ and artifacts/ paths; that organization was preserved.