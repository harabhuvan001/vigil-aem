# VIGIL-AEM agent instructions

VIGIL-AEM is an academic research prototype studying negative procedural transfer in LLM agents.
The current status is **environment/bootstrap phase**. Implement only work authorized for the
current task; the bootstrap does not validate the proposed research method.

Every architectural component must correspond to a stated hypothesis, an experiment, a metric,
and an ablation. Record that mapping before adding research behavior.

## Coding rules

- Use Python 3.11 and typed Python wherever practical.
- Use Pydantic models for schemas.
- Prefer deterministic functions when facts are inspectable.
- Use classical ML before unnecessarily complex neural models.
- Use LLM reasoning only where semantic interpretation is required.
- Never hardcode secrets or commit credentials, .env, .envrc, caches, models, tracking artifacts,
  database passwords, or generated benchmark outputs.
- No destructive actions outside sandboxes; no uncontrolled real-world API side effects.
- All experiments must be reproducible. Version prompts; log random seeds and provenance.
- Lock dependencies with uv; use uv sync --locked. Do not use Conda or add a large agent framework.
- Tests must pass before commits. Run make check for code changes.
- Preserve frozen benchmark ground truth and isolate external services from default tests.
- Planned module stubs are intentionally unimplemented. Do not describe them as working methods.

## Research rules

Never fabricate results. Clearly distinguish **observed result**, **expected hypothesis**,
**illustrative example**, and **external literature result**. Bootstrap smoke metrics are
infrastructure checks, never publication results. Never modify benchmark ground truth just to
improve model performance. Do not alter ground truth after viewing test performance.
Follow docs/EXPERIMENT_PROTOCOL.md. Leave publication epsilon unset until preregistered.

## Next authorized research work

The next development task can define SkillShiftBench v0.1 and implement the no-memory versus
similarity-memory baseline. That work needs explicit benchmark specs, frozen splits, versioned
prompts, model revisions, and paired-run provenance.
