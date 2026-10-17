# Enterprise UI Design spatial update

The user approved the analysis and its first delivery slice: spatial rules plus one working list-to-detail reference. No business application or downstream bundled token copy is migrated by this change.

## Scope and cleanup plan

1. Import the currently installed v1.0 Skill into `enterprise-ui-design/` as its maintained source; preserve a local baseline outside tracked source. Keep existing token keys/values and theme isolation compatible.
2. Add a focused spatial reference: shell/page/section/component responsibilities, single-owner insets, container/text alignment, content widths, standard/compact density, long content and responsive reflow. Record official sources and distinguish our defaults from source-system requirements.
3. Connect Create/Upgrade/Audit and acceptance checklists to the spatial contract. Remove duplicated entrypoint prose and move MateClaw-only action guidance into an explicit optional project example; preserve actionable copy, contrast, focus, and functional boundaries.
4. Extend JSON tokens additively; deterministically generate CSS without adding dependencies. Add regression checks for preserved tokens, JSON/CSS parity, variable resolution and independent theme/density selectors before changing the generator.
5. Provide reusable HTML/CSS/JS reference source, labeled simulation, with list filtering, detail/edit/save, theme and density controls. No backend or persistence claim beyond local demo storage. Existing fixture state must survive reload.
6. Validate skill/frontmatter/links, tokens and generator, JS syntax, and a real browser at 1366/1440/1920/390 in light/dark plus compact. Inspect screenshots and actual geometry; test keyboard/dialog focus, long text, empty results, validation and reload. Store captures and visual verdict locally; no pixel-reference score without a reference image.
7. Independently review the revised Skill, synchronize the verified source into the installed directory after a drift check, update STATUS, commit relevant reusable source only using Lore trailers, and push the configured feature branch. Verify remote commit and installed file hashes.

## UI Blueprint

- Product/task: equipment maintenance work-order list → inspect a record → edit owner/note → validate/save → return to the same filtered list. All records are simulation; demo persistence is local browser storage.
- Structure: existing blue/gray shell, compact global header, page header, connected filter/table/pagination region; constrained detail/form reading width. No invented notification/search/tenant controls.
- Alignment: page title and table outer edge share a page key line; filter text and table first-cell text share the inner content key line. Panel edges and text edges are separate, intentional tracks. A child section inside a panel does not repeat the panel inset.
- States: populated/long content/no search results, detail/edit dialog, field error, successful local save; themes light/dark; standard/compact density; narrow layout and sidebar collapse without inaccessible hidden navigation.
- Defaults: 32px desktop inline/24px block page inset; 16px narrow inset; 24px section gap; 16px group gap; 20px panel inset; 8px action gap. Compact changes panel/field/cell/control density, not page content hierarchy or body font size.
- Widths: data pages fill available workspace; overview pages can use 1440px max; details 960px max; forms 800px max. These are local starting points, not universal requirements. Respect a host's existing design system.
- Limits: a runnable reference validates the pattern, not a production migration, API integration, business acceptance or a pixel-identical match to another product.

## Acceptance

- Old common/mode token values preserved; new spatial tokens resolve under both densities/themes; generated CSS is reproducible.
- Four viewport widths without page-level horizontal overflow; wide tables scroll within their container; header/actions wrap and modal actions remain reachable.
- Measured page and text key lines agree within a one-CSS-pixel rounding tolerance for this reference only; no repeated inset in nested semantic groups.
- Real filtering, empty reset, detail/edit/save/reload and keyboard behavior exercised; no browser errors. All generated evidence stays local.
