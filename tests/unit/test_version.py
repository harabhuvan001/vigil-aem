from vigil.utils.version import capture_versions


def test_provenance_handles_non_repository(tmp_path):
    provenance = capture_versions(
        repo_root=tmp_path, model_identifier="fixture/model", model_revision="frozen-revision"
    )
    assert provenance.python_version.startswith("3.11.")
    assert provenance.operating_system
    assert provenance.package_versions["pydantic"]
    assert provenance.git_commit is None
    assert provenance.model_identifier == "fixture/model"
    assert provenance.model_revision == "frozen-revision"
