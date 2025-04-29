from dataclasses import dataclass
from pathlib import Path
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from .loci_utils import MONGO_MASTER_ASSET_COLLECTION


ROCK_IDS = [
    "06416ba54a824924b21623159c82f598",
    "17f7182cf299480b8e76dd2b3c841e22",
    "63766ad0258d45d78f5d86ccac60542f",
    "5cb67be08a254e70b89964cfea327dd1",
    "8ae0c37f91ea4e95b480fc1e1faf039f",
]
TREE_IDS = [
    "70f0e767fc2f449fa6fef9c2308b395f",
    "75e82512822841d9b758d26f56da4cb4",
    "ca6352151d41470cb1b7a837e3b067e2",
    "caf081828df84d7cbb07b4107991facc",
    "0983d8933531491f9be71c669e8a907b",
]
ASSET_IDS = ROCK_IDS + TREE_IDS
INDEX_FILE_PATH = Path(__file__).parent.resolve() / "index.pkl"


@dataclass
class Asset:
    uid: str
    title: str
    asset_s3_path: str = None


@dataclass
class AssetEmbeddingIndex:
    uids: list[str]
    titles: list[str]
    asset_s3_paths: list[str]
    captions: list[str]
    captions_embeddings: torch.Tensor


MODEL_STELLA = SentenceTransformer(
    "dunzhang/stella_en_400M_v5",
    trust_remote_code=True,
    device="cpu",
    config_kwargs={"use_memory_efficient_attention": False, "unpad_inputs": False},
)


def get_top_k_ids(
    scores: np.ndarray, index: AssetEmbeddingIndex, k: int = 5
) -> tuple[list[str], list[float]]:
    top_k_indices = np.argsort(scores)[-k:][::-1]
    top_k_ids = [index.uids[i] for i in top_k_indices]
    top_k_scores = [scores[i] for i in top_k_indices]
    return top_k_ids, top_k_scores


def create_index(asset_ids: list[str]):
    print(f"Creating index for {len(asset_ids)} assets")

    # get captions from MongoDB
    mongo_query = {"source_id": {"$in": asset_ids}}
    mongo_project = {
        "source_id": 1,
        "captions.sonnet_front_and_back_image_summary_no_filename.caption": 1,
        "asset_path": 1,
        "asset_name": 1,
    }
    assets = MONGO_MASTER_ASSET_COLLECTION.find(mongo_query, mongo_project)
    assets = list(assets)

    uids, captions, titles, asset_s3_paths = [], [], [], []
    for a in assets:
        uids.append(a["source_id"])
        captions.append(
            a["captions"]["sonnet_front_and_back_image_summary_no_filename"]["caption"]
        )
        titles.append(a["asset_name"])
        asset_s3_paths.append(a["asset_path"])

    captions_embeddings = MODEL_STELLA.encode(captions)

    index = AssetEmbeddingIndex(
        uids=uids,
        captions_embeddings=captions_embeddings,
        titles=titles,
        captions=captions,
        asset_s3_paths=asset_s3_paths,
    )

    print(f"Created index with {len(index.uids)} assets")
    return index


def pkl_save_index(index: AssetEmbeddingIndex, file_path: str):
    with open(file_path, "wb") as f:
        pickle.dump(index, f)
    print(f"Saved index with {len(index.uids)} assets to index.pkl")


def pkl_load_index(file_path: str) -> AssetEmbeddingIndex:
    with open(file_path, "rb") as f:
        index = pickle.load(f)
        print(index)

    print(f"Loaded index with {len(index.uids)} assets from {file_path}")
    return index


def get_asset_index() -> AssetEmbeddingIndex:
    """
    Get the asset index for a list of asset IDs.
    """
    if Path(INDEX_FILE_PATH).exists():
        index = pkl_load_index(INDEX_FILE_PATH)
    else:
        index = create_index(ASSET_IDS)
        pkl_save_index(index, INDEX_FILE_PATH)

    return index


def search(query: str, index: AssetEmbeddingIndex, k: int = 5) -> list[Asset]:
    """
    Get the top k asset IDs and scores for a given query.
    """
    query_embeddings = MODEL_STELLA.encode([query], prompt_name="s2p_query")
    scores = MODEL_STELLA.similarity(query_embeddings, index.captions_embeddings)
    scores = scores.numpy().flatten()
    top_k_indices = np.argsort(scores)[-k:][::-1]

    assets = [
        Asset(
            uid=index.uids[i],
            title=index.titles[i],
            asset_s3_path=index.asset_s3_paths[i],
        )
        for i in top_k_indices
    ]
    return assets
