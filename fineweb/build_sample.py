"""Build fineweb/sample.json from the first real val documents of both Parameter Golf exports."""
import base64, json, struct, sys
from pathlib import Path
from array import array
sys.path.insert(0, str(Path(__file__).resolve().parent))
from peek_fineweb import Source, BASELINE_REPO, CASEOPS_REPO, REMOTE_ROOT, read_header, read_tokens, BOS_ID

TARGET = 150_000  # sp1024 tokens to keep (cut at a document boundary)
out, n_docs = {}, None
for repo in (BASELINE_REPO, CASEOPS_REPO):
    src = Source(repo, REMOTE_ROOT, None, None)
    m = json.loads(src.read("manifest.json"))
    ds = m["datasets"][0]
    tok = next(t for t in m["tokenizers"] if t["name"] == ds["tokenizer_name"])
    shard = f"datasets/{ds['name']}/fineweb_val_000000.bin"
    read_header(src, shard)
    toks = read_tokens(src, shard, 0, TARGET + 20_000)
    bos = [i for i, t in enumerate(toks) if t == BOS_ID]
    if n_docs is None:
        n_docs = max(k for k, p in enumerate(bos) if p <= TARGET)  # docs fully inside TARGET
    cut = bos[n_docs]
    if cut > len(toks) - 1: raise SystemExit("window too small")
    kept = toks[:cut]
    header = [0] * 256; header[0], header[1], header[2] = 20240520, 1, len(kept)
    for d in m["datasets"]:
        d["stats"].update(files_val=1, files_train=0, tokens_val=len(kept), tokens_train=0, docs_val=n_docs)
    m["sample"] = f"First {n_docs} real validation documents of {repo} (val shard 0, tokens [0, {len(kept)}))."
    out[f"{repo}/manifest.json"] = base64.b64encode(json.dumps(m).encode()).decode()
    out[f"{repo}/{tok['model_path']}"] = base64.b64encode(src.read(tok["model_path"])).decode()
    out[f"{repo}/{shard}"] = base64.b64encode(struct.pack("<256i", *header) + kept.tobytes()).decode()
    print(repo, ds["name"], n_docs, "docs", len(kept), "tokens")
json.dump(out, open(Path(__file__).resolve().parent / "sample.json", "w"))
