# Limitations

- No research method, frozen LLM, embedding model, training pipeline, skill retriever, learned risk
  predictor, AEM update/decay rule, or real-world benchmark is implemented.
- Six toy cases cannot establish scientific validity, generalization, or safety.
- The in-memory sandboxes do not isolate untrusted code. They cannot authorize real destructive
  actions or uncontrolled external API effects.
- SQL fixtures simulate preconditions; they do not execute SQL or establish PostgreSQL transaction safety.
- Literal boolean applicability checks do not perform semantic reasoning or infer missing facts.
- Seeding cannot guarantee cross-platform GPU equality or deterministic hosted LLM responses.
- Bootstrap reward, severity, and epsilon are illustrative. Publication thresholds remain unset.
- Installed dependencies are locked, but reproducibility also needs model/prompt/data revisions
  and immutable run provenance in future experiments.
- Docker image tags select explicit versions but may be republished; archive verified digests for
  publication. Native Windows and Linux dependency availability may differ.
- Machine-specific service availability and bootstrap checks are recorded in VALIDATION.md.
