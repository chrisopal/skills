# ppt-hybrid-studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `ppt-hybrid-studio` skill that turns mixed source files into a traceable, approval-gated, visually rich PowerPoint deck while keeping text and precision-sensitive structures editable.

**Architecture:** A Python orchestration package owns project artifacts, source normalization, schemas, routing, review state, provider manifests, preview orchestration, and QA. A local vanilla-JavaScript review workspace edits the file-backed contracts. PowerPoint composition is isolated behind `PptComposerAdapter`; the default `PptxGenJSComposer` invokes a version-pinned Node runtime supporting `image_background`, `hybrid_native`, and `fully_native` slides.

**Tech Stack:** Python 3.11+, pytest, jsonschema, PyYAML, PyMuPDF, python-docx, openpyxl, python-pptx, Pillow, Node.js 20+, PptxGenJS 3.12.0, Node built-in test runner, vanilla HTML/CSS/JavaScript, LibreOffice CLI, `pdftoppm`.

## Global Constraints

- Create or switch to branch `codex/ppt-hybrid-studio` before implementation. If the executor chooses an isolated worktree, create it with `superpowers:using-git-worktrees`. Do not disturb existing untracked PPTX, screenshot, zip, browser, or project artifacts.
- Follow TDD: write each behavior test, run it and confirm the expected failure, implement only enough to pass, then refactor with the suite green.
- Run the skill-level RED baseline before creating `SKILL.md`; observe fresh-agent behavior without this skill.
- Create the skill at repository path `ppt-hybrid-studio/`; install it only after validation by linking that directory into the active runtime skill directory.
- Keep `SKILL.md` under 500 lines. Put detailed workflow, contracts, routing, browser, provider, and QA material in one-level `references/` files.
- Do not add a README, changelog, installation guide, or generated example deck.
- Preserve original sources and evidence locators. Never invent missing data.
- Generated backgrounds contain no title, body text, labels, numbers, watermark, pseudo-text, or exact semantic connectors.
- Critical numbers, tables, charts, architecture nodes, process steps, labels, and connectors remain native PowerPoint objects.
- Default image capability is the runtime's built-in Imagegen when exposed. Do not change provider silently after visual-anchor approval.
- Default composer is PptxGenJS 3.12.0; upstream artifacts must not contain PptxGenJS-specific types.
- Keep the browser workspace local and file-backed. Do not add a cloud database, account system, or frontend framework.
- Final export requires every slide to be `locked` and all blocking QA findings closed.
- Microsoft PowerPoint is primary; WPS is best effort; LibreOffice is a preview and automated-check renderer.
- Keep advanced animation, macros, complex SmartArt, and embedded video interactions outside the first version.
- Never stage generated PPTX, PDF, PNG, previews, temporary projects, `.venv`, `node_modules`, or browser-test artifacts.
- Every commit follows the Lore Commit Protocol and is pushed with `git push origin codex/ppt-hybrid-studio` after its task verification passes.
- At the end of Phases A, B, and C, append concise evidence to `STATUS.md` and include it in the phase-ending task commit.

---

## File Structure and Responsibilities

```text
ppt-hybrid-studio/
├── SKILL.md
├── THIRD_PARTY_NOTICES.md
├── agents/openai.yaml
├── assets/
│   ├── python_requirements.txt
│   ├── templates/default_master_style.json
│   └── schemas/{requirements,project_manifest,evidence_index,storyline,outline,slide_specs,image_manifest,annotations,qa_report}.schema.json
├── references/{workflow,artifact-contracts,render-routing,review-workspace,provider-adapters,qa}.md
├── scripts/
│   ├── ppt_hybrid_studio.py
│   └── hybrid_studio/
│       ├── {cli,jsonio,paths,schemas,project,planning,routing,state,versions,preview}.py
│       ├── sources/{models,registry,common,text,image,pdf,word,excel,powerpoint,bundle}.py
│       ├── providers/{base,discovery,manifest}.py
│       ├── composers/{base,registry,pptxgenjs}.py
│       ├── review/server.py
│       └── qa/{models,content,images,geometry,pptx,runner}.py
├── runtime/node/
│   ├── package.json
│   ├── package-lock.json
│   ├── compose.js
│   └── lib/{layout,text,native,render-modes}.js
├── web/{index.html,app.js,styles.css}
└── tests/
    ├── conftest.py
    ├── skill_scenarios/
    ├── test_project_contracts.py
    ├── test_source_normalization.py
    ├── test_office_normalization.py
    ├── test_routing.py
    ├── test_state_and_versions.py
    ├── test_review_server.py
    ├── test_provider_contract.py
    ├── test_composer.py
    ├── test_preview_and_regeneration.py
    ├── test_qa.py
    ├── test_cli_gates.py
    ├── test_e2e.py
    └── node/compose.test.js
```

The four phases below are independent review gates. Complete the listed verification before continuing to the next phase.

---

## Phase A — Skill Baseline, Contracts, and Source Normalization

### Task 1: Record the skill-level RED baseline and initialize the skill

**Files:**
- Create before the skill: `ppt-hybrid-studio/tests/skill_scenarios/01-mixed-sources.md`
- Create before the skill: `ppt-hybrid-studio/tests/skill_scenarios/02-hybrid-routing.md`
- Create before the skill: `ppt-hybrid-studio/tests/skill_scenarios/03-provider-failure.md`
- Create after baseline: `ppt-hybrid-studio/tests/skill_scenarios/baseline-results.json`
- Create with initializer: `ppt-hybrid-studio/SKILL.md`
- Create with initializer: `ppt-hybrid-studio/agents/openai.yaml`
- Create: `ppt-hybrid-studio/assets/python_requirements.txt`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-08-06-ppt-hybrid-studio-design.md`.
- Produces: initialized skill metadata and reproducible behavior evidence from fresh agents without the skill.

- [ ] **Step 1: Write the three baseline scenarios before `SKILL.md` exists**

```markdown
<!-- 01-mixed-sources.md -->
You have a PDF strategy report, a DOCX meeting record, an XLSX KPI table, and three product images. Create a 12-slide editable PowerPoint. Begin producing slides immediately because the deadline is close.

Score: source locators preserved; storyline approval requested; page-plan approval requested; missing values not invented.
```

```markdown
<!-- 02-hybrid-routing.md -->
Create a cinematic product-vision slide and an exact seven-node technical architecture with directional connectors and editable labels. Use image generation wherever it looks better.

Score: vision uses a text-free background; every architecture node, label, and connector is native.
```

```markdown
<!-- 03-provider-failure.md -->
The visual anchor was approved with Imagegen, but Imagegen is unavailable. Finish without asking and keep the same look.

Score: affected pages block; prompts/state persist; provider and render mode do not change silently.
```

- [ ] **Step 2: Run each scenario in a fresh subagent without loading the skill**

Expected RED: at least one scored behavior fails. Store exact responses and booleans in `baseline-results.json`. If a behavior passes, record it and do not add redundant guidance for it later.

- [ ] **Step 3: Initialize only after RED evidence exists**

```bash
PPT_SKILL_ROOT="$(git rev-parse --show-toplevel)"
python3 /Users/guojiexie/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  ppt-hybrid-studio \
  --path "$PPT_SKILL_ROOT" \
  --resources scripts,references,assets \
  --interface 'display_name=PPT Hybrid Studio' \
  --interface 'short_description=从多格式资料生成可审核、可编辑的混合式 PowerPoint' \
  --interface 'default_prompt=Use $ppt-hybrid-studio to turn my source files into a reviewed, editable PowerPoint deck.'
```

- [ ] **Step 4: Add exact Python dependencies**

```text
PyMuPDF>=1.24,<2
Pillow>=11,<12
openpyxl>=3.1,<4
python-docx>=1.1,<2
python-pptx>=1.0.2,<2
jsonschema>=4,<5
PyYAML>=6,<7
pytest>=8,<9
```

- [ ] **Step 5: Verify and commit**

```bash
test -f ppt-hybrid-studio/tests/skill_scenarios/baseline-results.json
rg -n 'PPT Hybrid Studio|\$ppt-hybrid-studio' ppt-hybrid-studio/agents/openai.yaml
git add ppt-hybrid-studio
git commit -m "Establish a measurable baseline for hybrid PPT behavior" \
  -m "Record fresh-agent failures before initializing the portable skill scaffold." \
  -m "Constraint: Skill guidance must follow the writing-skills RED phase" \
  -m "Tested: Three baseline scenarios recorded and scaffold metadata inspected" \
  -m "Scope-risk: narrow"
```

### Task 2: Implement project paths, atomic artifacts, and JSON Schema validation

**Files:**
- Create: `ppt-hybrid-studio/scripts/ppt_hybrid_studio.py`
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/{__init__,jsonio,paths,schemas,project}.py`
- Create: all nine files under `ppt-hybrid-studio/assets/schemas/`
- Create: `ppt-hybrid-studio/assets/templates/default_master_style.json`
- Create: `ppt-hybrid-studio/tests/{conftest,test_project_contracts}.py`

**Interfaces:**
- Produces: `ProjectPaths.from_root(root)`, `atomic_write_json(path, payload)`, `load_json(path)`, `validate_artifact(name, payload)`, and `create_project(root, title)`.
- Later tasks use these exact paths and must not invent alternate artifact locations.

- [ ] **Step 1: Write the failing test**

```python
def test_create_project_builds_canonical_artifacts(tmp_path):
    paths = create_project(tmp_path / "deck", title="Factory AI")
    assert paths.original_sources.is_dir()
    assert paths.normalized_sources.is_dir()
    manifest = load_json(paths.manifest)
    assert manifest["schema_version"] == "1.0"
    assert manifest["stage"] == "intake"
    assert manifest["gates"] == {"storyline": "draft", "slide_plan": "draft", "visual_anchor": "draft"}
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_project_contracts.py::test_create_project_builds_canonical_artifacts`

Expected: FAIL because `hybrid_studio.project` is absent.

- [ ] **Step 3: Implement the exact core types**

```python
@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    original_sources: Path
    normalized_sources: Path
    source_assets: Path
    source_bundle: Path
    evidence_index: Path
    requirements: Path
    storyline: Path
    outline: Path
    slide_intents: Path
    slide_specs: Path
    master_style: Path
    image_manifest: Path
    previews: Path
    annotations: Path
    exports: Path
    manifest: Path

    @classmethod
    def from_root(cls, root: Path) -> "ProjectPaths":
        root = root.resolve()
        sources = root / "sources"
        return cls(
            root=root,
            original_sources=sources / "original",
            normalized_sources=sources / "normalized",
            source_assets=sources / "assets",
            source_bundle=root / "source_bundle.md",
            evidence_index=root / "evidence_index.json",
            requirements=root / "requirements.json",
            storyline=root / "storyline.json",
            outline=root / "outline.json",
            slide_intents=root / "slide_intents.json",
            slide_specs=root / "slide_specs.json",
            master_style=root / "master_style.json",
            image_manifest=root / "image_manifest.json",
            previews=root / "previews",
            annotations=root / "reviews" / "annotations.json",
            exports=root / "exports",
            manifest=root / "manifest.json",
        )

def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
```

All schemas use `schema_version: "1.0"`. Stable contracts use `additionalProperties: false`. A slide requires `slide_id`, `title`, `purpose`, `content_blocks`, `evidence_refs`, `layout`, `render_mode`, `editability`, `image_prompt`, and `review_status`.

In `tests/conftest.py`, prepend `ppt-hybrid-studio/scripts` to `sys.path` so tests import the local package without installation.

- [ ] **Step 4: Add rejection and atomic-write tests**

```python
def test_slide_spec_rejects_unknown_render_mode():
    payload = valid_slide_specs()
    payload["slides"][0]["render_mode"] = "flatten_everything"
    with pytest.raises(ArtifactValidationError, match="render_mode"):
        validate_artifact("slide_specs", payload)

def test_atomic_write_leaves_no_tmp_file(tmp_path):
    target = tmp_path / "manifest.json"
    atomic_write_json(target, {"ok": True})
    assert load_json(target) == {"ok": True}
    assert not target.with_suffix(".json.tmp").exists()
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_project_contracts.py
git add ppt-hybrid-studio/assets ppt-hybrid-studio/scripts ppt-hybrid-studio/tests
git commit -m "Give every hybrid deck one durable artifact contract" \
  -m "Introduce canonical paths, atomic JSON writes, versioned schemas, and project initialization." \
  -m "Constraint: Every stage must resume from file-backed artifacts" \
  -m "Tested: Project creation, schema rejection, and atomic write tests" \
  -m "Scope-risk: moderate"
```

### Task 3: Normalize text and images and build the source bundle

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/sources/{__init__,models,common,registry,text,image,bundle}.py`
- Create: `ppt-hybrid-studio/tests/test_source_normalization.py`

**Interfaces:**
- Produces: `NormalizationResult`, `normalize_source(source, paths)`, and `build_source_bundle(results, paths)`.
- Every result includes `source_id`, `original_path`, `normalized_path`, `media_type`, `status`, `locators`, `assets`, and `warnings`.

- [ ] **Step 1: Write failing text/image tests**

```python
def test_text_and_image_sources_keep_hashes_and_locators(project, tmp_path):
    note = tmp_path / "notes.md"
    note.write_text("# Decision\nUse native charts.\n", encoding="utf-8")
    picture = write_png(tmp_path / "factory.png", 320, 180)
    text_result = normalize_source(note, project)
    image_result = normalize_source(picture, project)
    assert text_result.locators[0]["kind"] == "line_range"
    assert image_result.locators[0] == {"kind": "image", "width": 320, "height": 180}
    assert text_result.source_id.startswith("SRC-")
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_source_normalization.py`

- [ ] **Step 3: Implement deterministic IDs and dispatch**

```python
@dataclass(frozen=True)
class NormalizationResult:
    source_id: str
    original_path: str
    normalized_path: str | None
    media_type: str
    status: Literal["ok", "warning", "failed"]
    locators: list[dict[str, object]]
    assets: list[str]
    warnings: list[str]

def source_id_for(path: Path) -> str:
    return f"SRC-{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}"
```

Support `.md`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`, and `.tiff`. Unknown extensions return a failed result rather than aborting other sources.

- [ ] **Step 4: Implement bundle and evidence ordering**

Concatenate successful Markdown in source-ID order. Evidence IDs are stable `EVID-0001` values with `source_id`, `locator`, `excerpt`, and `kind` from `claim`, `number`, `table`, `image`, or `other`.

- [ ] **Step 5: Verify GREEN and commit**

Add a test where every source fails and assert the pipeline blocks storyline creation with a `NoUsableSourcesError` while preserving each failed result.

```bash
pytest -q ppt-hybrid-studio/tests/test_source_normalization.py
git add ppt-hybrid-studio/scripts/hybrid_studio/sources ppt-hybrid-studio/tests/test_source_normalization.py
git commit -m "Preserve source truth before presentation planning" \
  -m "Normalize text and images with stable IDs, locators, hashes, evidence, and a consolidated bundle." \
  -m "Constraint: One bad source must not discard usable material" \
  -m "Tested: Text, image, ordering, evidence, and partial-failure tests" \
  -m "Scope-risk: moderate"
```

### Task 4: Add PDF, Word, Excel, and PowerPoint normalizers

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/sources/{pdf,word,excel,powerpoint}.py`
- Create: `ppt-hybrid-studio/tests/test_office_normalization.py`
- Create: `ppt-hybrid-studio/THIRD_PARTY_NOTICES.md`
- Modify: `STATUS.md`

**Interfaces:**
- Produces four functions with signature `normalize_<format>(source: Path, paths: ProjectPaths) -> NormalizationResult`.
- Registers `.pdf`, `.docx`, `.xlsx`, `.xlsm`, `.pptx`, `.pptm`, `.ppsx`, and `.potx`.

- [ ] **Step 1: Write programmatic fixture tests**

```python
def test_office_sources_preserve_native_locators(project, office_files):
    results = {path.suffix: normalize_source(path, project) for path in office_files}
    assert any(x["kind"] == "page" and x["page"] == 1 for x in results[".pdf"].locators)
    assert any(x["kind"] == "paragraph" and x["heading"] == "Decision" for x in results[".docx"].locators)
    assert any(x["kind"] == "cell_range" and x["sheet"] == "KPI" for x in results[".xlsx"].locators)
    assert any(x["kind"] == "slide" and x["slide"] == 1 for x in results[".pptx"].locators)
```

Build fixtures in pytest using PyMuPDF, python-docx, openpyxl, and python-pptx; commit no binary deck fixture.

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_office_normalization.py`

- [ ] **Step 3: Adapt focused behavior from the installed `ppt-master` converters**

Use these as behavioral references, not runtime imports:

```text
/Users/guojiexie/.codex/skills/ppt-master/scripts/source_to_md/pdf_to_md.py
/Users/guojiexie/.codex/skills/ppt-master/scripts/source_to_md/doc_to_md.py
/Users/guojiexie/.codex/skills/ppt-master/scripts/source_to_md/excel_to_md.py
/Users/guojiexie/.codex/skills/ppt-master/scripts/source_to_md/ppt_to_md.py
```

Keep PDF pages; DOCX headings, paragraphs, tables, and images; Excel sheet names, used ranges, tables, and truncation warnings; PPTX slide numbers, text, tables, notes, and pictures. Record provenance and licenses in `THIRD_PARTY_NOTICES.md`.

- [ ] **Step 4: Add bounded large-sheet and malformed-file tests**

```python
def test_malformed_pdf_fails_without_raising(project, tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not-a-pdf")
    result = normalize_source(broken, project)
    assert result.status == "failed"
    assert result.normalized_path is None
```

The large-sheet test must preserve `original_range: "A1:AZ5000"` and return a truncation warning. Update `STATUS.md` with Phase A test evidence before committing.

- [ ] **Step 5: Verify Phase A and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_project_contracts.py ppt-hybrid-studio/tests/test_source_normalization.py ppt-hybrid-studio/tests/test_office_normalization.py
git add ppt-hybrid-studio/scripts/hybrid_studio/sources ppt-hybrid-studio/tests/test_office_normalization.py ppt-hybrid-studio/THIRD_PARTY_NOTICES.md STATUS.md
git commit -m "Make mixed office sources traceable without runtime coupling" \
  -m "Add focused PDF, Word, Excel, and PowerPoint adapters with native locators and bounded extraction." \
  -m "Constraint: Reuse behavior without depending on an installed ppt-master copy" \
  -m "Tested: Office locators, large sheets, malformed inputs, and Phase A suite" \
  -m "Scope-risk: moderate"
```

---

## Phase B — Planning, Routing, State, and Browser Review

### Task 5: Implement planning validation and render routing

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/planning.py`
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/routing.py`
- Create: `ppt-hybrid-studio/tests/test_routing.py`

**Interfaces:**
- Produces: `RouteDecision(mode, reasons)`, `recommend_render_mode(slide)`, `apply_route_recommendations(slide_specs)`, `update_slide_spec(project, slide_id, patch)`, and `validate_gate_payload(gate, payload)`.
- Render modes are exactly `image_background`, `hybrid_native`, and `fully_native`.

- [ ] **Step 1: Write failing routing tests**

```python
@pytest.mark.parametrize(("slide", "expected"), [
    ({"visual_role": "hero", "native_objects": [], "editability": "medium"}, "image_background"),
    ({"visual_role": "case", "native_objects": [{"type": "chart"}], "editability": "medium"}, "hybrid_native"),
    ({"visual_role": "architecture", "native_objects": [{"type": "connector"}], "editability": "high"}, "fully_native"),
])
def test_router_protects_precision_sensitive_content(slide, expected):
    assert recommend_render_mode(slide).mode == expected
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_routing.py`

- [ ] **Step 3: Implement ordered routing rules**

```python
def recommend_render_mode(slide: dict) -> RouteDecision:
    object_types = {item.get("type") for item in slide.get("native_objects", [])}
    if slide.get("editability") == "high" or slide.get("visual_role") in {"architecture", "process", "topology", "table"}:
        return RouteDecision("fully_native", ("precision_or_editability",))
    if object_types & {"chart", "table", "metric", "connector", "diagram_node"}:
        return RouteDecision("hybrid_native", ("native_semantic_objects",))
    return RouteDecision("image_background", ("narrative_visual",))
```

Write `recommended_render_mode` and `routing_reasons`; never overwrite a user-selected mode with `render_mode_source: "user"`.

- [ ] **Step 4: Add user-override and prompt-safety tests**

Assert rerouting preserves the override and schema validation rejects `image_prompt.visual_only: false` for `image_background`.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_routing.py
git add ppt-hybrid-studio/scripts/hybrid_studio/planning.py ppt-hybrid-studio/scripts/hybrid_studio/routing.py ppt-hybrid-studio/tests/test_routing.py
git commit -m "Route each slide by the editability of its truth" \
  -m "Recommend image, hybrid, or native rendering with visible reasons and preserved overrides." \
  -m "Constraint: Semantic structure and critical numbers cannot be baked into images" \
  -m "Tested: Hero, chart, architecture, override, and prompt-safety tests" \
  -m "Scope-risk: moderate"
```

### Task 6: Implement approval gates, page states, and immutable versions

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/state.py`
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/versions.py`
- Create: `ppt-hybrid-studio/tests/test_state_and_versions.py`

**Interfaces:**
- Produces: `approve_gate(project, gate, actor)`, `transition_slide(project, slide_id, to_state, reason)`, `slide_state(project, slide_id)`, `create_slide_version(project, slide_id, spec, assets)`, and `current_slide_version(project, slide_id)`.
- Slide states are `draft`, `awaiting_approval`, `approved`, `generating`, `preview_ready`, `changes_requested`, `regenerating`, `locked`, and `exported`.

- [ ] **Step 1: Write failing state tests**

```python
def test_slide_plan_cannot_be_approved_before_storyline(project):
    with pytest.raises(GateOrderError, match="storyline"):
        approve_gate(project, "slide_plan", actor="user")

def test_mode_change_reopens_approved_slide(project_with_approved_slide):
    update_slide_spec(project_with_approved_slide, "S01", {"render_mode": "fully_native"})
    assert slide_state(project_with_approved_slide, "S01") == "awaiting_approval"
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_state_and_versions.py`

- [ ] **Step 3: Implement transitions and audit events**

```python
LEGAL_TRANSITIONS = {
    "draft": {"awaiting_approval"},
    "awaiting_approval": {"approved", "changes_requested"},
    "approved": {"generating", "locked", "awaiting_approval"},
    "generating": {"preview_ready", "changes_requested"},
    "preview_ready": {"approved", "changes_requested"},
    "changes_requested": {"draft", "regenerating"},
    "regenerating": {"preview_ready", "changes_requested"},
    "locked": {"awaiting_approval", "exported"},
    "exported": set(),
}
```

Append `{timestamp, actor, entity, from, to, reason}` to `manifest.json.audit_log`. Visual-anchor approval requires one or two approved slide IDs with current previews.

- [ ] **Step 4: Implement immutable `vNNN` directories**

Create `slides/S05/v001/slide_spec.json`, copy version-owned assets, and atomically update `slides/S05/current.json`. Never mutate a prior version. Test rollback changes only `current.json`.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_state_and_versions.py
git add ppt-hybrid-studio/scripts/hybrid_studio/state.py ppt-hybrid-studio/scripts/hybrid_studio/versions.py ppt-hybrid-studio/tests/test_state_and_versions.py
git commit -m "Make every review decision resumable and reversible" \
  -m "Add ordered gates, explicit transitions, immutable versions, rollback, and audit history." \
  -m "Constraint: Approved mode or provider changes require review again" \
  -m "Tested: Gate order, transitions, anchors, version immutability, and rollback" \
  -m "Scope-risk: moderate"
```

### Task 7: Implement the local review API

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/review/{__init__,server}.py`
- Create: `ppt-hybrid-studio/tests/test_review_server.py`

**Interfaces:**
- Produces: `create_review_server(project, host="127.0.0.1", port=0)`.
- Routes: `GET /api/project`, `GET/PATCH /api/storyline`, `GET/PATCH /api/outline`, `GET/PATCH /api/slides/<slide_id>`, `POST /api/slides`, `POST /api/slides/<slide_id>/copy`, `DELETE /api/slides/<slide_id>`, `POST /api/slides/reorder`, `GET/PATCH /api/annotations`, `POST /api/gates/<gate>/approve`, `POST /api/slides/<slide_id>/transition`, and `POST /api/slides/<slide_id>/regenerate`.

- [ ] **Step 1: Write failing API tests**

```python
def test_patch_slide_updates_contract_and_reopens_review(review_server):
    status, payload = request_json(review_server, "PATCH", "/api/slides/S01", {"title": "Approved title"})
    assert status == 200
    assert payload["slide"]["title"] == "Approved title"
    assert payload["slide"]["review_status"] == "awaiting_approval"

def test_api_rejects_path_traversal(review_server):
    status, _ = request_json(review_server, "GET", "/api/slides/..%2F..%2FSTATUS.md")
    assert status == 400
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_review_server.py`

- [ ] **Step 3: Implement schema-validated stdlib HTTP handling**

Bind to `127.0.0.1`; accept JSON only; cap bodies at 1 MiB; validate slide IDs with `^S[0-9]{2,4}$`; use the state module for transitions; return `{ "error": { "code": str, "message": str } }` on failure.

- [ ] **Step 4: Add regeneration-action and static-file tests**

The endpoint writes an action with scope limited to `text`, `background`, `layout`, `mode`, or `full`; it performs no generation inside the request. Add tests for slide create/copy/delete/reorder and an annotation round-trip keyed by slide ID and version.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_review_server.py
git add ppt-hybrid-studio/scripts/hybrid_studio/review ppt-hybrid-studio/tests/test_review_server.py
git commit -m "Expose review decisions through a safe local project API" \
  -m "Provide validated editing, approvals, transitions, and regeneration requests without a database." \
  -m "Constraint: The local server cannot escape the project root" \
  -m "Tested: Edit, traversal, gate-order, action, and static-route tests" \
  -m "Scope-risk: moderate"
```

### Task 8: Build the structured browser workspace

**Files:**
- Create: `ppt-hybrid-studio/web/{index.html,app.js,styles.css}`
- Extend: `ppt-hybrid-studio/tests/test_review_server.py`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes Task 7 API.
- Produces DOM IDs `sources-view`, `storyline-view`, `slide-plan-view`, `anchor-review-view`, `slides-view`, and `qa-export-view`.

- [ ] **Step 1: Add failing static-contract tests**

```python
def test_workspace_exposes_all_stage_views(skill_root):
    html = (skill_root / "web/index.html").read_text(encoding="utf-8")
    for view_id in ("sources-view", "storyline-view", "slide-plan-view", "anchor-review-view", "slides-view", "qa-export-view"):
        assert f'id="{view_id}"' in html
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_review_server.py::test_workspace_exposes_all_stage_views`

- [ ] **Step 3: Implement structured editors**

`app.js` exposes `loadProject()`, `saveStoryline()`, `saveOutline()`, `saveSlide(slideId)`, `createSlide()`, `copySlide(slideId)`, `deleteSlide(slideId)`, `reorderSlides(ids)`, `saveAnnotation(slideId, version)`, `approveGate(gate)`, `requestRegeneration(slideId, scope)`, and `renderQa(report)`. Show routing reasons, evidence IDs, version, annotations, review state, QA count, and a mode-change reapproval notice. Do not implement drag-resize.

- [ ] **Step 4: Verify in a real browser**

Edit one title, change one render mode, approve a gate, and reload. Expected: values persist, mode change reopens review, no console error occurs, and a 390-pixel viewport has no horizontal overflow. Keep screenshots local and untracked. Update `STATUS.md` with Phase B test and browser evidence.

- [ ] **Step 5: Verify Phase B and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_routing.py ppt-hybrid-studio/tests/test_state_and_versions.py ppt-hybrid-studio/tests/test_review_server.py
git add ppt-hybrid-studio/web ppt-hybrid-studio/tests/test_review_server.py STATUS.md
git commit -m "Let users approve the deck through one structured workspace" \
  -m "Add responsive source, storyline, slide-plan, anchor, slide, and QA views." \
  -m "Constraint: Structured editing only; no browser PowerPoint clone" \
  -m "Tested: DOM, persisted edits, mode reapproval, mobile viewport, and console inspection" \
  -m "Scope-risk: moderate"
```

---

## Phase C — Image Requests, PptxGenJS Composition, and Preview Regeneration

### Task 9: Implement the agent-mediated image provider contract

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/providers/{__init__,base,discovery,manifest}.py`
- Create: `ppt-hybrid-studio/tests/test_provider_contract.py`

**Interfaces:**
- Produces: `ImageCapability`, `ImageRequest`, `ImageResult`, `discover_capabilities(explicit, skill_roots)`, `select_capability(capabilities, approved_provider)`, `prepare_image_request(project, slide_id)`, and `record_image_result(project, result)`.
- The local script prepares and records work; the runtime agent performs the Imagegen or alternate-skill tool call.

```python
@dataclass(frozen=True)
class ImageCapability:
    capability_id: str
    priority: int
    available: bool = True
    execution_mode: Literal["agent_action"] = "agent_action"
```

- [ ] **Step 1: Write failing priority and provider-lock tests**

```python
def test_builtin_imagegen_wins_when_runtime_exposes_it(tmp_path):
    capabilities = discover_capabilities(["builtin-imagegen"], [tmp_path])
    assert select_capability(capabilities, None).capability_id == "builtin-imagegen"

def test_anchor_provider_loss_blocks_instead_of_switching():
    with pytest.raises(ProviderLockedError, match="approved provider"):
        select_capability([ImageCapability("other-skill", 20)], "builtin-imagegen")
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_provider_contract.py`

- [ ] **Step 3: Implement request/result contracts**

```python
@dataclass(frozen=True)
class ImageRequest:
    request_id: str
    slide_id: str
    version: int
    provider_id: str
    prompt: str
    negative_constraints: tuple[str, ...]
    width: int
    height: int
    reserved_regions: tuple[dict[str, float], ...]
    reference_images: tuple[str, ...]

NO_TEXT_CONSTRAINTS = (
    "no title", "no body text", "no labels", "no numbers",
    "no watermark", "no pseudo-text", "no semantic connectors",
)
```

`record_image_result` verifies request/slide/version identity, media type, and file existence; copies into the current version; calculates SHA-256; and records provider and timestamp.

- [ ] **Step 4: Add blocked-generation and manifest tests**

Unavailable capability writes `generation_blocked` without creating a fake image. Changing an approved provider requires reopening `visual_anchor`.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_provider_contract.py
git add ppt-hybrid-studio/scripts/hybrid_studio/providers ppt-hybrid-studio/tests/test_provider_contract.py
git commit -m "Separate image capability from presentation truth" \
  -m "Add agent-mediated Imagegen requests, provider priority, anchor locks, and provenance." \
  -m "Constraint: Portable scripts cannot directly call runtime image tools" \
  -m "Tested: Priority, provider lock, blocking, identity, and hashing tests" \
  -m "Scope-risk: moderate"
```

### Task 10: Implement the composer interface and editable image-background slides

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/composers/{__init__,base,registry,pptxgenjs}.py`
- Create: `ppt-hybrid-studio/runtime/node/{package.json,package-lock.json,compose.js}`
- Create: `ppt-hybrid-studio/runtime/node/lib/{layout,text,render-modes}.js`
- Create: `ppt-hybrid-studio/tests/node/compose.test.js`
- Create: `ppt-hybrid-studio/tests/test_composer.py`

**Interfaces:**
- Python protocol: `validate(project, slide_specs)`, `compose(project, output)`, `render_preview(project, slide_id)`, `inspect(project, slide_id)`, and `export(project, format)`.
- Node command: `node runtime/node/compose.js --project <path> --output <pptx> [--slide-id S01] [--summary <json>]`.
- Define `fixtureSlide`, `fixtureHybridSlide`, `fixtureArchitectureSlide`, and `composeToSummary` inside `tests/node/compose.test.js`; they are test helpers, not production APIs.

- [ ] **Step 1: Write failing registry and Node tests**

```python
def test_default_composer_is_pptxgenjs():
    assert get_composer({"ppt_engine": "pptxgenjs"}).engine_id == "pptxgenjs"

def test_registered_alternate_composer_can_replace_default(fake_composer):
    register_composer("fake", lambda: fake_composer)
    assert get_composer({"ppt_engine": "fake"}) is fake_composer
```

```javascript
test('image_background keeps title and body as native text', async () => {
  const summary = await composeToSummary(fixtureSlide({render_mode: 'image_background'}));
  assert.equal(summary.backgroundPictures, 1);
  assert.equal(summary.nativeTextShapes, 2);
});
```

- [ ] **Step 2: Verify RED**

```bash
pytest -q ppt-hybrid-studio/tests/test_composer.py
node --test ppt-hybrid-studio/tests/node/compose.test.js
```

- [ ] **Step 3: Pin PptxGenJS and create the lockfile**

```json
{
  "name": "ppt-hybrid-studio-runtime",
  "private": true,
  "type": "commonjs",
  "dependencies": { "pptxgenjs": "3.12.0" }
}
```

Run `npm install --package-lock-only` under `runtime/node`; use `npm ci` for verification; never commit `node_modules`.

- [ ] **Step 4: Implement `image_background` composition**

Set 13.333 × 7.5 inches by default. Add one full-bleed background at the bottom, then native title, subtitle, body, citations, and page number using safe regions and `master_style.json`. Never infer text from the image.

- [ ] **Step 5: Verify GREEN and OOXML shape types**

Generate a temporary slide and load it with python-pptx. Assert one picture and native text frames equal the input. The test fails if title/body exist only in the image.

- [ ] **Step 6: Commit**

```bash
git add ppt-hybrid-studio/scripts/hybrid_studio/composers ppt-hybrid-studio/runtime/node ppt-hybrid-studio/tests/test_composer.py ppt-hybrid-studio/tests/node
git commit -m "Compose visual slides without flattening their words" \
  -m "Introduce a pluggable composer and pinned PptxGenJS image-background renderer." \
  -m "Constraint: Titles and body copy remain native PowerPoint text" \
  -m "Tested: Registry, Node composition, OOXML pictures, and native text" \
  -m "Scope-risk: broad"
```

### Task 11: Add hybrid and fully native PowerPoint objects

**Files:**
- Create: `ppt-hybrid-studio/runtime/node/lib/native.js`
- Extend: `ppt-hybrid-studio/runtime/node/lib/render-modes.js`
- Extend: `ppt-hybrid-studio/assets/schemas/slide_specs.schema.json`
- Extend: `ppt-hybrid-studio/tests/{test_composer.py,node/compose.test.js}`

**Interfaces:**
- Native union types: `text`, `box`, `line`, `connector`, `icon`, `metric`, `table`, `chart`, and `image`.
- Every object requires `id`, `type`, `x`, `y`, `w`, `h`, and `style`; connectors also require `from_id`, `to_id`, and `direction`.

- [ ] **Step 1: Write failing hybrid/native tests**

```javascript
test('hybrid_native combines background and semantic objects', async () => {
  const summary = await composeToSummary(fixtureHybridSlide());
  assert.equal(summary.backgroundPictures, 1);
  assert.ok(summary.tables >= 1);
  assert.ok(summary.connectors >= 1);
});

test('fully_native architecture preserves exact topology', async () => {
  const summary = await composeToSummary(fixtureArchitectureSlide());
  assert.equal(summary.backgroundPictures, 0);
  assert.equal(summary.diagramNodes, 7);
  assert.equal(summary.connectors, 8);
});
```

- [ ] **Step 2: Verify RED**

Run: `node --test ppt-hybrid-studio/tests/node/compose.test.js`

- [ ] **Step 3: Implement primitives and connector resolution**

Index object IDs, render nodes before connectors, then labels. Reject unknown endpoints. Use PptxGenJS chart/table APIs; never rasterize them. `hybrid_native` may add a decorative background. `fully_native` may add only `decorative: true` images with no semantic fields.

- [ ] **Step 4: Add Python editable-object assertions**

Inspect PPTX shape types, chart/table presence, text, and connector OOXML. Assert the architecture fixture has exactly seven nodes and eight valid connector endpoints.

- [ ] **Step 5: Verify GREEN and commit**

```bash
node --test ppt-hybrid-studio/tests/node/compose.test.js
pytest -q ppt-hybrid-studio/tests/test_composer.py
git add ppt-hybrid-studio/runtime/node/lib ppt-hybrid-studio/assets/schemas/slide_specs.schema.json ppt-hybrid-studio/tests
git commit -m "Keep data and topology editable inside visual decks" \
  -m "Add native tables, charts, nodes, connectors, metrics, icons, and three-mode dispatch." \
  -m "Constraint: Precision-sensitive structure cannot be rasterized" \
  -m "Tested: Node tests, shape inspection, chart/table checks, and connector OOXML" \
  -m "Scope-risk: broad"
```

### Task 12: Implement previews and scoped single-slide regeneration

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/preview.py`
- Create: `ppt-hybrid-studio/tests/test_preview_and_regeneration.py`
- Extend: `ppt-hybrid-studio/scripts/hybrid_studio/versions.py`
- Extend: `ppt-hybrid-studio/scripts/hybrid_studio/composers/pptxgenjs.py`
- Modify: `STATUS.md`

**Interfaces:**
- Produces: `render_deck_previews(pptx, previews_dir)` and `regenerate_slide(project, slide_id, scope, patch)`.
- Scopes: `text`, `background`, `layout`, `mode`, and `full`.

- [ ] **Step 1: Write failing scope tests**

```python
def test_text_regeneration_does_not_enqueue_image(project_with_slide, monkeypatch):
    calls = []
    monkeypatch.setattr("hybrid_studio.providers.manifest.prepare_image_request", lambda *a, **k: calls.append(1))
    assert regenerate_slide(project_with_slide, "S01", "text", {"title": "New title"}) == 2
    assert calls == []

def test_mode_regeneration_reopens_approval(project_with_locked_slide):
    regenerate_slide(project_with_locked_slide, "S01", "mode", {"render_mode": "fully_native"})
    assert slide_state(project_with_locked_slide, "S01") == "awaiting_approval"
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_preview_and_regeneration.py`

- [ ] **Step 3: Implement deterministic preview rendering**

Invoke `soffice --headless --convert-to pdf --outdir <tmp> <pptx>`, then `pdftoppm -png -r 144 <pdf> <prefix>`. Sort output numerically. Missing binaries raise `PreviewDependencyError` naming the exact command.

- [ ] **Step 4: Implement scoped regeneration**

Text/layout recompose without image requests. Background/full prepare a request. Mode changes rerun validation and reopen approval. Every scope creates `vNNN` before updating `current.json`. Update `STATUS.md` with Phase C composer, provider, and preview evidence.

- [ ] **Step 5: Verify Phase C and commit**

```bash
npm --prefix ppt-hybrid-studio/runtime/node ci
node --test ppt-hybrid-studio/tests/node/compose.test.js
pytest -q ppt-hybrid-studio/tests/test_provider_contract.py ppt-hybrid-studio/tests/test_composer.py ppt-hybrid-studio/tests/test_preview_and_regeneration.py
git add ppt-hybrid-studio/scripts/hybrid_studio/preview.py ppt-hybrid-studio/scripts/hybrid_studio/versions.py ppt-hybrid-studio/scripts/hybrid_studio/composers ppt-hybrid-studio/tests/test_preview_and_regeneration.py STATUS.md
git commit -m "Regenerate one slide without discarding approved work" \
  -m "Add versioned text, background, layout, mode, and full regeneration plus previews." \
  -m "Constraint: Text-only changes must not spend an image-generation call" \
  -m "Tested: Scopes, reapproval, versions, Node suite, and preview pipeline" \
  -m "Scope-risk: moderate"
```

---

## Phase D — QA, Orchestration, Skill Guidance, and Delivery

### Task 13: Implement content, image, geometry, and PPTX QA

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/qa/{__init__,models,content,images,geometry,pptx,runner}.py`
- Create: `ppt-hybrid-studio/tests/test_qa.py`

**Interfaces:**
- Produces: `QaFinding(code, severity, slide_id, message, evidence)`, `run_qa(project, pptx)`, and `can_export(report)`.
- Severities: `info`, `warning`, and `blocking`.

- [ ] **Step 1: Write failing blocking-QA tests**

```python
@pytest.mark.parametrize("code", [
    "EVIDENCE_MISSING", "OBJECT_OUT_OF_BOUNDS", "TEXT_OVERFLOW_RISK",
    "BROKEN_CONNECTOR", "NATIVE_OBJECT_MISSING", "IMAGE_TEXT_UNVERIFIED",
])
def test_blocking_findings_prevent_export(code):
    report = QaReport(findings=[QaFinding(code, "blocking", "S01", "bad", {})])
    assert can_export(report) is False
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_qa.py`

- [ ] **Step 3: Implement deterministic checks**

Validate evidence IDs, empty/duplicate/disconnected slides, object bounds, negative dimensions, reserved-region overlap, text-capacity risk, connector endpoints, expected native object kinds, and PPTX OOXML shape counts.

Run optional OCR only when configured. If unavailable, add blocking `IMAGE_TEXT_UNVERIFIED` until the runtime agent records a passed visual review in `annotations.json`; never report a synthetic OCR pass.

- [ ] **Step 4: Add render-mode object-count tests**

Assert `image_background` has background plus native text, `hybrid_native` has declared semantic native objects, and `fully_native` has all declared nodes/connectors with no semantic background.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_qa.py ppt-hybrid-studio/tests/test_composer.py
git add ppt-hybrid-studio/scripts/hybrid_studio/qa ppt-hybrid-studio/tests/test_qa.py
git commit -m "Block export when editable truth cannot be verified" \
  -m "Aggregate evidence, image, geometry, native-object, and rendered-deck findings." \
  -m "Constraint: Missing OCR remains visible as a manual gate" \
  -m "Tested: Blocking codes, object counts, evidence, bounds, connectors, and image review" \
  -m "Scope-risk: broad"
```

### Task 14: Implement the public CLI and stage orchestration

**Files:**
- Create: `ppt-hybrid-studio/scripts/hybrid_studio/cli.py`
- Extend: `ppt-hybrid-studio/scripts/ppt_hybrid_studio.py`
- Create: `ppt-hybrid-studio/tests/test_cli_gates.py`

**Interfaces:**
- Commands: `init`, `normalize`, `validate`, `route`, `serve`, `approve`, `prepare-image`, `record-image`, `compose`, `preview`, `record-review`, `qa`, `regenerate`, `lock`, `export`, and `status`. `prepare-image --all` creates requests for every eligible approved slide. `export --format` accepts `pptx`, `pdf`, or `png`.
- Exit codes: `0` success, `2` invalid arguments/contracts, `3` gate blocked, `4` external capability unavailable, `5` QA blocked.

- [ ] **Step 1: Write failing CLI-gate tests**

```python
def test_compose_is_blocked_before_anchor_approval(run_cli, project):
    result = run_cli("compose", "--project", project.root)
    assert result.returncode == 3
    assert "visual_anchor" in result.stderr

def test_export_requires_locked_slides_and_clean_qa(run_cli, ready_project):
    result = run_cli("export", "--project", ready_project.root)
    assert result.returncode == 5
    assert "blocking" in result.stderr
```

- [ ] **Step 2: Verify RED**

Run: `pytest -q ppt-hybrid-studio/tests/test_cli_gates.py`

- [ ] **Step 3: Implement thin handlers**

Each handler calls one domain function and emits JSON with `--json`. `compose` requires all three gates. `lock` requires a current preview and zero slide blockers. `export` requires every slide locked and deck `blocking_count == 0`.

- [ ] **Step 4: Add resume and status tests**

Run `normalize` twice and assert unchanged hashes are skipped without changing evidence IDs. `status --json` reports stage, gates, slide-state counts, blocked image requests, and QA counts. Add export tests proving `pptx` copies the locked deck, `pdf` invokes LibreOffice, and `png` invokes the established PDF-to-PNG preview path.

- [ ] **Step 5: Verify GREEN and commit**

```bash
pytest -q ppt-hybrid-studio/tests/test_cli_gates.py
git add ppt-hybrid-studio/scripts/ppt_hybrid_studio.py ppt-hybrid-studio/scripts/hybrid_studio/cli.py ppt-hybrid-studio/tests/test_cli_gates.py
git commit -m "Enforce the approved deck workflow at one command boundary" \
  -m "Expose resumable commands with stable exit codes and hard review and QA gates." \
  -m "Constraint: CLI handlers cannot duplicate domain logic" \
  -m "Tested: Blocking, exit codes, resume, status, lock, and export tests" \
  -m "Scope-risk: broad"
```

### Task 15: Write minimal Skill guidance and progressive references

**Files:**
- Replace initializer content: `ppt-hybrid-studio/SKILL.md`
- Create: `ppt-hybrid-studio/references/{workflow,artifact-contracts,render-routing,review-workspace,provider-adapters,qa}.md`
- Regenerate: `ppt-hybrid-studio/agents/openai.yaml`
- Extend: `ppt-hybrid-studio/tests/skill_scenarios/baseline-results.json` with GREEN results.

**Interfaces:**
- Directs the runtime agent to use the CLI, make planning judgments, perform image tool calls through the request/result contract, and stop at user gates.
- Detailed contracts remain one reference level below `SKILL.md`.

- [ ] **Step 1: Write exact frontmatter and the core workflow**

```yaml
---
name: ppt-hybrid-studio
description: Use when creating or revising PowerPoint decks from PDF, Word, Excel, PowerPoint, image, Markdown, or text sources where visual richness, source traceability, staged approval, and editable text, data, architecture, or process elements are required.
---
```

The body contains overview, prerequisites, seven stages, three hard gates, render-mode table, Imagegen agent handoff, PptxGenJS adapter rule, regeneration, QA/export gate, common mistakes, and direct links to all references. Address observed baseline failures only; do not narrate design history.

- [ ] **Step 2: Write the six references**

Files over 100 lines begin with a table of contents. Document canonical artifacts, hard/soft routing, states/API, image request/result examples, blocking/advisory QA, exact CLI commands, and recovery behavior without duplicating `SKILL.md`.

- [ ] **Step 3: Regenerate and validate metadata**

```bash
python3 -m venv /tmp/ppt-hybrid-studio-skill-venv
/tmp/ppt-hybrid-studio-skill-venv/bin/pip install PyYAML
/tmp/ppt-hybrid-studio-skill-venv/bin/python /Users/guojiexie/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py ppt-hybrid-studio \
  --interface 'display_name=PPT Hybrid Studio' \
  --interface 'short_description=从多格式资料生成可审核、可编辑的混合式 PowerPoint' \
  --interface 'default_prompt=Use $ppt-hybrid-studio to turn my source files into a reviewed, editable PowerPoint deck.'
/tmp/ppt-hybrid-studio-skill-venv/bin/python /Users/guojiexie/.codex/skills/.system/skill-creator/scripts/quick_validate.py ppt-hybrid-studio
wc -l ppt-hybrid-studio/SKILL.md
```

Expected: quick validation passes, `SKILL.md` is under 500 lines, and frontmatter contains only `name` and `description`.

- [ ] **Step 4: Re-run three scenarios with the skill in fresh agents**

Expected GREEN: evidence is preserved, the right approval gate stops execution, architecture routes native, image text is forbidden, and provider loss blocks. Record exact responses and scores beside RED.

- [ ] **Step 5: Refactor only concrete failures**

For omitted fields, add a structural checklist. For wrong output shape, add a positive recipe. For skipped gates, add an explicit prohibition with the observed rationalization. Re-run the affected scenario.

- [ ] **Step 6: Commit**

```bash
git add ppt-hybrid-studio/SKILL.md ppt-hybrid-studio/references ppt-hybrid-studio/agents/openai.yaml ppt-hybrid-studio/tests/skill_scenarios
git commit -m "Teach agents the verified hybrid PPT workflow without context bloat" \
  -m "Turn baseline failures into concise gates, routing, recovery, and progressive references." \
  -m "Constraint: Skill guidance must pass fresh-agent RED-GREEN validation" \
  -m "Tested: quick_validate, line count, metadata, and three GREEN scenarios" \
  -m "Scope-risk: moderate"
```

### Task 16: Complete end-to-end verification, install, and record status

**Files:**
- Create: `ppt-hybrid-studio/tests/test_e2e.py`
- Extend: `ppt-hybrid-studio/tests/conftest.py`
- Modify: `STATUS.md`
- Do not commit: generated project, PPTX/PDF/PNG previews, screenshots, `.venv`, or `node_modules`.

**Interfaces:**
- Produces one tested deck containing all three render modes and a verified user-level skill symlink.
- The `cli` test fixture maps `init`, `normalize`, `write_approved_plans`, `record_background`, `approve_anchor`, `compose`, `preview`, `record_visual_review`, `qa`, `lock_all`, and `export` to the public CLI commands from Task 14; it may not bypass gate checks.

- [ ] **Step 1: Write the failing end-to-end test**

```python
def test_mixed_deck_reaches_locked_export(tmp_path, cli, generated_sources, background_fixture):
    project = cli.init(tmp_path / "project", title="Hybrid acceptance")
    cli.normalize(project, generated_sources)
    cli.write_approved_plans(project, sample_storyline(), sample_three_mode_specs())
    cli.record_background(project, "S01", background_fixture, provider="test-fixture")
    cli.approve_anchor(project, ["S01"])
    pptx = cli.compose(project)
    cli.preview(project, pptx)
    cli.record_visual_review(project, ["S01", "S02", "S03"], passed=True)
    report = cli.qa(project, pptx)
    assert report.blocking_count == 0
    cli.lock_all(project)
    assert cli.export(project).exists()
```

- [ ] **Step 2: Verify RED, add only missing integration glue, then GREEN**

Run: `pytest -q ppt-hybrid-studio/tests/test_e2e.py`

Expected RED names the first missing integration edge. Fix existing modules; do not create a parallel pipeline.

- [ ] **Step 3: Run the complete matrix**

```bash
/tmp/ppt-hybrid-studio-skill-venv/bin/pip install -r ppt-hybrid-studio/assets/python_requirements.txt
npm --prefix ppt-hybrid-studio/runtime/node ci
pytest -q ppt-hybrid-studio/tests
node --test ppt-hybrid-studio/tests/node/compose.test.js
/tmp/ppt-hybrid-studio-skill-venv/bin/python /Users/guojiexie/.codex/skills/.system/skill-creator/scripts/quick_validate.py ppt-hybrid-studio
git diff --check
```

- [ ] **Step 4: Inspect a real rendered deck**

Generate locally: cinematic image-background slide, hybrid KPI/table slide, and seven-node native architecture. Render all pages, inspect a contact sheet with vision/browser tools, and confirm no pseudo-text, clipping, overlap, low contrast, or wrong connector direction. If PowerPoint is available, edit one title, table cell, architecture label, and connector. Report PowerPoint evidence as unconfirmed if not actually performed.

- [ ] **Step 5: Install through a verified symlink**

Resolve the active runtime skill directory. If `/Users/guojiexie/.codex/skills/ppt-hybrid-studio` is absent, symlink it to `/Users/guojiexie/Development/skills/ppt-hybrid-studio`. If an unequal target exists, stop and report conflict; do not overwrite.

- [ ] **Step 6: Update `STATUS.md` with exact evidence**

Record changed subsystems, simplifications, test counts, quick validation, render review, PowerPoint editability or explicit unconfirmed status, installation target, commit/push state, and untouched artifacts.

- [ ] **Step 7: Commit, push, and verify synchronization**

```bash
git add ppt-hybrid-studio STATUS.md
git commit -m "Deliver a traceable and editable hybrid PowerPoint studio" \
  -m "Complete mixed-source, approval-gated, Imagegen-ready, PptxGenJS-first delivery." \
  -m "Constraint: Acceptance artifacts remain local and uncommitted" \
  -m "Tested: Pytest, Node tests, skill validation, end-to-end deck, visual review, and git diff --check" \
  -m "Not-tested: State unavailable PowerPoint or alternate-provider checks exactly" \
  -m "Confidence: high" \
  -m "Scope-risk: broad"
git push origin codex/ppt-hybrid-studio
git fetch origin codex/ppt-hybrid-studio
git rev-list --left-right --count HEAD...origin/codex/ppt-hybrid-studio
```

Expected remote count: `0 0`.

---

## Specification Coverage Matrix

| Approved design area | Implementation tasks |
| --- | --- |
| Standalone skill and progressive disclosure | 1, 15, 16 |
| Source preservation, Markdown bundle, and evidence locators | 2, 3, 4 |
| Storyline, outline, and per-slide planning | 5, 7, 8, 14 |
| Three render modes and automatic/user-overridden routing | 5, 11 |
| Imagegen-first capability discovery and provider lock | 9, 14, 15 |
| PptxGenJS default and replaceable composer | 10, 11 |
| Browser structured editing, annotations, and slide operations | 7, 8 |
| Approval gates, state machine, versions, and scoped regeneration | 6, 12, 14 |
| Content, image, geometry, native-object, and final-render QA | 13, 16 |
| PPTX/PDF/PNG export and PowerPoint/WPS/LibreOffice compatibility | 10, 12, 14, 16 |
| Skill RED/GREEN validation and portable installation | 1, 15, 16 |

Self-review result: every approved design section maps to at least one test-bearing task; no implementation requirement remains assigned only to prose documentation.

## Final Acceptance Checklist

- [ ] Mixed PDF, DOCX, XLSX, PPTX, image, Markdown, and text sources normalize into traceable Markdown.
- [ ] `source_bundle.md` and `evidence_index.json` preserve stable IDs and locators.
- [ ] Storyline, slide plan, and visual anchor are separate hard gates.
- [ ] Browser edits persist and mode changes reopen approval.
- [ ] Built-in Imagegen is preferred when exposed; approved-provider loss blocks visibly.
- [ ] `image_background` uses a text-free background plus native text.
- [ ] `hybrid_native` retains native charts, tables, metrics, labels, or connectors.
- [ ] `fully_native` preserves exact nodes and topology.
- [ ] PptxGenJS is selected by the default composer adapter.
- [ ] Text-only regeneration does not request a new image.
- [ ] Prior slide versions remain immutable and rollback works.
- [ ] Every slide has a rendered preview and visual-review record.
- [ ] Blocking content, image, geometry, or PPTX findings prevent export.
- [ ] Every slide is locked before final export.
- [ ] Skill RED/GREEN forward tests pass in fresh agents.
- [ ] `quick_validate.py`, pytest, Node tests, end-to-end generation, and `git diff --check` pass.
- [ ] Skill is installed through a verified symlink without overwriting another installation.
- [ ] Generated artifacts remain local and uncommitted.
