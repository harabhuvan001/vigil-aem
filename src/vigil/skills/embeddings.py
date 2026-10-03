"""Pinned CPU Sentence Transformers goal embeddings and cosine similarities."""

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from vigil.benchmark.schema import SourceSkill, TransferTask
from vigil.evaluation.prototype_schema import PrototypeConfig


def goal_similarities(
    tasks: list[TransferTask], skills: list[SourceSkill], config: PrototypeConfig
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    model = SentenceTransformer(
        config.embedding_model,
        revision=config.embedding_revision,
        device="cpu",
        cache_folder=".cache/embeddings",
        token=False,
        trust_remote_code=False,
    )
    vectors = model.encode(
        [task.natural_language_goal for task in tasks] + [s.goal for s in skills],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,
    )
    matrix = vectors[: len(tasks)] @ vectors[len(tasks) :].T
    target_matrix = vectors[: len(tasks)] @ vectors[: len(tasks)].T
    return (
        np.asarray(np.clip(matrix, -1, 1), dtype=np.float64),
        np.asarray(np.clip(target_matrix, -1, 1), dtype=np.float64),
    )
