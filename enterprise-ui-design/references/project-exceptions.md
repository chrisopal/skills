# Existing project exceptions

Read only when the named existing product is in scope. These are compatibility notes, not universal enterprise design rules. Do not change that product's convention as an incidental consequence of a shared Skill update.

## MateClaw presales table actions

The existing presales surface uses blue primary buttons for ordinary commands and red for destructive commands. Keep each operation cell in an explicit flex group with an 8px gap and zero inherited button margins. Reserve enough column width for the common two-button group; when wrapping is necessary, keep each line left-aligned. Verify populated long-text rows.

This local convention does not require every table in another product to use filled primary buttons. New surfaces follow the host's action hierarchy and the shared recognizable-actions rule.

## LIMS Huixin details

Apply the [detail layout system](detail-layout-system.md) with the existing Huixin teal brand and semantic tokens. Equipment and samples use the ordinary object composition. Keep usage and calibration distinct for equipment, and keep custody and commission relations available for samples. File and structured report templates use the document composition, with mapping or configuration before version history and optional provenance at the bottom.

For task and form-instance details, reuse the object/status/action hierarchy and aligned facts. Preserve the frozen record renderer, review and retest eligibility, and version-specific record navigation. Use sparse icons at section or action level. Preserve real field-mapping keys in the configuration context, business names in ordinary reading, and checksums in the matching version's optional verification area.
