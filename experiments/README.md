# Experiments

01–06 are planned entry points, not implementations or measured results. They exit explicitly
rather than running fabricated comparisons. See ../docs/EXPERIMENT_PROTOCOL.md.

`smoke_mlflow.py` is an infrastructure smoke test only. Start local MLflow with `make mlflow`,
then run `uv run --locked python experiments/smoke_mlflow.py`. Dummy metrics carry
`scientific_result=false`; never include them in publication tables.

