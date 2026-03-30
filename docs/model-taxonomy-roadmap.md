# Model Taxonomy Roadmap (Incremental)

## Current inventory (source of truth)

- Usage-style categories currently live in `Capability` and `llm_model_capabilities`.
- Technical capabilities currently live in `llm_models` fields:
  - `supports_json`
  - `supports_tools`
  - `supports_vision`
  - `input_modalities`
  - `output_modalities`
  - `supported_parameters`
- Public UI labels are presentation-derivations from mixed signals:
  - `model_type_labels`
  - `capabilities` (legacy)
- Routing readiness and MVP verification are guarded by:
  - `llm_models.evaluation_status = verified`
  - `llm_model_routing_settings.enabled_for_routing = true`
  - `llm_model_routing_settings.is_evaluated_for_routing = true`

## Canonical taxonomy

### ModelCategory (usage specialization)

- `chat`
- `analysis`
- `code`
- `multimodal_general`
- `vision`
- `ocr`

### TechnicalCapability (technical support)

- `json`
- `tools`
- `vision`
- `text_input`
- `text_output`
- `image_input`
- `audio_input`
- `audio_output`

### BenchmarkScope (verification scope)

- `text`
- `code`
- `json_tools`
- `vision`
- `ocr`

## Verified semantics (kept stable)

- `verified` continues to mean: passed live benchmark for MVP text-first scope and eligible for routing.
- Scope-specific growth is represented with benchmark scope metadata, not by redefining `verified`.
- New clients should read `verification_scopes`; legacy clients can keep using `is_verified`.

## API contract direction

- New public fields (incremental):
  - `model_categories: string[]`
  - `technical_capabilities: string[]`
  - `verification_scopes: string[]`
- Legacy compatibility kept:
  - `capabilities`
  - `supports_json`
  - `supports_tools`
  - `supports_vision`

## Phase rollout

1. Stabilize MVP text-first with taxonomy fields available, routing behavior unchanged.
2. Expose taxonomy clearly in UI badges and API consumers (with legacy fallbacks).
3. Expand benchmark coverage by `benchmark_scope`.
4. Add scoped multimodal routing pools (`vision`, `ocr`) behind explicit request scope/flags.

## Known tradeoffs

- Temporary duplicate semantics across legacy and new fields.
- Category inference from provider metadata is imperfect; conservative derivation is preferred.
- Ranking should not consume the full taxonomy until specialized benchmarks are available per scope.
