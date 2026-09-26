"""Look at the FineWeb data that Parameter Golf actually trains on.

Standard library only, so it runs anywhere with Python 3.9+.

Parameter Golf does not ship raw FineWeb text. It ships *token shards*:

    fineweb_val_000000.bin, fineweb_train_000000.bin, ...

Each shard is a 1024-byte header (256 little-endian int32s: magic 20240520,
version 1, token count) followed by uint16 token ids. Documents are laid end
to end, and each one starts with the BOS token (id 1). There is no EOS. So the
only way to see where one web page stops and the next begins is to split the
stream on BOS and decode each piece with the SentencePiece model.

This script does that, step by step, fetching only the bytes it needs with
HTTP Range requests (no 200 MB downloads):

    python3 peek_fineweb.py                           # sp1024 baseline, val split
    python3 peek_fineweb.py --docs 3 --show-tokens    # also print each token
    python3 peek_fineweb.py --caseops                 # the CaseOps (lossless caps) export
    python3 peek_fineweb.py --split train --shard 7 --start-token 5000000
    python3 peek_fineweb.py --local ./data            # after cached_challenge_fineweb.py

The code mirrors data/download_hf_docs_and_tokenize.py (how shards are written)
and train_gpt.py (how shards are read) in github.com/openai/parameter-golf.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import urllib.request
from array import array
from pathlib import Path

# -- Where the data lives ----------------------------------------------------

BASELINE_REPO = "willdepueoai/parameter-golf"  # data/cached_challenge_fineweb.py
CASEOPS_REPO = "romeerp/parameter-golf-caseops-v1"  # records/.../2026-04-18_PR1626_CaseOps_Taper
REMOTE_ROOT = "datasets"

SHARD_MAGIC = 20240520
SHARD_VERSION = 1
HEADER_BYTES = 256 * 4
BOS_ID = 1


class Source:
    """Reads files (or byte ranges of files) from Hugging Face or a local directory."""

    def __init__(self, repo: str, root: str, base_url: str | None, local: Path | None):
        self.local = local
        self.base = base_url or f"https://huggingface.co/datasets/{repo}/resolve/main"
        self.root = root

    def read(self, rel: str, start: int | None = None, end: int | None = None) -> bytes:
        """Bytes [start, end) of `rel`. `rel` is relative to the manifest's root."""
        if self.local is not None:
            with (self.local / rel).open("rb") as f:
                f.seek(start or 0)
                return f.read(None if end is None else end - (start or 0))
        url = f"{self.base}/{self.root}/{rel}"
        req = urllib.request.Request(url, headers={"User-Agent": "peek_fineweb.py"})
        if start is not None:
            req.add_header("Range", f"bytes={start}-{'' if end is None else end - 1}")
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            if start is not None and resp.status == 200:  # server ignored Range
                data = data[start:end]
            return data


# -- Step 1: the manifest says which datasets and tokenizers exist -------------

def load_manifest(src: Source) -> dict:
    return json.loads(src.read("manifest.json"))


# -- Step 2: the tokenizer (.model is a protobuf; we parse it by hand) ---------

def _varint(buf: bytes, i: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if b < 0x80:
            return result, i
        shift += 7


def _fields(buf: bytes):
    """Yield (field_number, wire_type, value) for one protobuf message."""
    i = 0
    while i < len(buf):
        key, i = _varint(buf, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = _varint(buf, i)
        elif wire == 1:
            value, i = buf[i : i + 8], i + 8
        elif wire == 2:
            n, i = _varint(buf, i)
            value, i = buf[i : i + n], i + n
        elif wire == 5:
            value, i = buf[i : i + 4], i + 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield field, wire, value


# sentencepiece_model.proto: ModelProto.pieces = 1; SentencePiece{piece=1, score=2, type=3}
NORMAL, UNKNOWN, CONTROL, USER_DEFINED, UNUSED, BYTE = 1, 2, 3, 4, 5, 6


def load_sentencepiece(model_bytes: bytes) -> list[tuple[str, int]]:
    """Return [(piece, type)] indexed by token id."""
    vocab = []
    for field, _, value in _fields(model_bytes):
        if field != 1:
            continue
        piece, kind = "", NORMAL
        for f, _, v in _fields(value):
            if f == 1:
                piece = v.decode("utf-8")
            elif f == 3:
                kind = v
        vocab.append((piece, kind))
    return vocab


def decode(ids, vocab) -> str:
    """Same as sp.decode(ids): join pieces, turn <0xNN> byte pieces back into
    UTF-8, drop control tokens, and turn the '▁' word marker into a space."""
    out = bytearray()
    for t in ids:
        piece, kind = vocab[t]
        if kind == CONTROL:
            continue
        if kind == BYTE:
            out.append(int(piece[3:5], 16))
        elif kind == UNKNOWN:
            out += " ⁇ ".encode()
        else:
            out += piece.replace("▁", " ").encode("utf-8")
    return out.decode("utf-8", errors="replace")


# -- Step 3: read a slice of a shard -------------------------------------------

def read_header(src: Source, rel: str) -> int:
    header = struct.unpack("<256i", src.read(rel, 0, HEADER_BYTES))
    if header[0] != SHARD_MAGIC or header[1] != SHARD_VERSION:
        raise ValueError(f"{rel}: not a Parameter Golf shard (header {header[:3]})")
    return header[2]  # number of tokens in this shard


def read_tokens(src: Source, rel: str, start: int, count: int) -> array:
    raw = src.read(rel, HEADER_BYTES + 2 * start, HEADER_BYTES + 2 * (start + count))
    tokens = array("H")  # uint16, same as np.fromfile(dtype="<u2")
    tokens.frombytes(raw)
    if sys.byteorder == "big":
        tokens.byteswap()
    return tokens


# -- Step 4: split the stream into documents at every BOS ----------------------

def split_docs(tokens, first_token: int):
    """Yield (start, end, complete_start, complete_end) spans, one per document.

    A span that touches the edge of the slice we fetched may be only part of a
    document; the two flags say whether we saw its real start (a BOS) and its
    real end (the next BOS)."""
    bos = [i for i, t in enumerate(tokens) if t == BOS_ID]
    if not bos or bos[0] > 0:  # tail of a document that began before our slice
        yield 0, bos[0] if bos else len(tokens), first_token == 0, bool(bos)
    for k, start in enumerate(bos):
        end = bos[k + 1] if k + 1 < len(bos) else len(tokens)
        yield start, end, True, k + 1 < len(bos)


# -- Step 5 (CaseOps only): undo the lossless capitalization transform ---------
# Port of decode_lossless_caps_v2 from records/.../lossless_caps.py.

TITLE, ALLCAPS, CAPNEXT, ESC = "", "", "", ""


def decode_caseops(text: str) -> str:
    out = []
    pending_escape = False
    word_mode = None  # "title" | "allcaps" for the next ASCII word
    active_allcaps = capnext = in_word = False
    for ch in text:
        is_alpha = ch.isascii() and ch.isalpha()
        if pending_escape:
            out.append(ch)
            pending_escape = False
            in_word = is_alpha
            active_allcaps = active_allcaps and is_alpha
            continue
        if ch == ESC:
            pending_escape = True
        elif ch == TITLE:
            word_mode = "title"
        elif ch == ALLCAPS:
            word_mode = "allcaps"
        elif ch == CAPNEXT:
            capnext = True
        elif is_alpha:
            if not in_word:  # first letter of a word
                upper = word_mode is not None or capnext
                active_allcaps = word_mode == "allcaps"
                in_word = True
            else:
                upper = active_allcaps or capnext
            out.append(ch.upper() if upper else ch)
            word_mode, capnext = None, False
        else:
            out.append(ch)
            in_word = active_allcaps = False
    return "".join(out)


def show_piece(piece: str) -> str:
    names = {TITLE: "⟨TITLE⟩", ALLCAPS: "⟨ALLCAPS⟩", CAPNEXT: "⟨CAPNEXT⟩", ESC: "⟨ESC⟩"}
    return names.get(piece, piece)


# -- Putting it together --------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--caseops", action="store_true", help=f"use {CASEOPS_REPO} instead of {BASELINE_REPO}")
    ap.add_argument("--repo", help="Hugging Face dataset repo id")
    ap.add_argument("--dataset", help="dataset name from manifest.json (default: first one)")
    ap.add_argument("--split", default="val", choices=["val", "train"])
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--start-token", type=int, default=0, help="token offset inside the shard")
    ap.add_argument("--window", type=int, default=200_000, help="tokens to fetch (2 bytes each)")
    ap.add_argument("--docs", type=int, default=5, help="documents to print")
    ap.add_argument("--chars", type=int, default=600, help="characters of each document to print (0 = all)")
    ap.add_argument("--show-tokens", action="store_true", help="also print each document's tokens")
    ap.add_argument("--local", type=Path, help="read from a local data/ dir instead of Hugging Face")
    ap.add_argument("--base-url", help=argparse.SUPPRESS)  # e.g. a local mirror, for testing
    args = ap.parse_args()

    repo = args.repo or (CASEOPS_REPO if args.caseops else BASELINE_REPO)
    src = Source(repo, REMOTE_ROOT, args.base_url, args.local)

    manifest = load_manifest(src)
    datasets = manifest["datasets"]
    ds = next((d for d in datasets if d["name"] == args.dataset), None) if args.dataset else datasets[0]
    if ds is None:
        sys.exit(f"no dataset {args.dataset!r}; choose from {[d['name'] for d in datasets]}")
    tok = next(t for t in manifest["tokenizers"] if t["name"] == ds["tokenizer_name"])
    print(f"repo      {repo}")
    print(f"datasets  {[d['name'] for d in datasets]}")
    print(f"using     {ds['name']}  (tokenizer {tok['name']}, vocab {tok['vocab_size']})")
    print(f"docs      {manifest.get('num_docs')} total, first {manifest.get('num_val_docs')} are val")

    vocab = load_sentencepiece(src.read(tok["model_path"]))
    is_caseops = "caseops" in (tok.get("text_transform") or tok["name"] or "")

    shard = f"datasets/{ds['name']}/fineweb_{args.split}_{args.shard:06d}.bin"
    n_tokens = read_header(src, shard)
    start = min(args.start_token, n_tokens)
    count = min(args.window, n_tokens - start)
    tokens = read_tokens(src, shard, start, count)
    print(f"shard     {shard}: {n_tokens:,} tokens; fetched [{start:,}, {start + count:,})")

    printed = 0
    for a, b, has_start, has_end in split_docs(tokens, start):
        if printed == args.docs:
            break
        ids = tokens[a:b]
        text = decode(ids, vocab)
        if is_caseops:
            text = decode_caseops(text)
        n_bytes = len(text.encode("utf-8"))
        flags = ("" if has_start else " (started before this window)") + (
            "" if has_end else " (continues past this window)"
        )
        print()
        print(f"═══ doc at token {start + a:,}: {len(ids):,} tokens, {n_bytes:,} bytes, "
              f"{n_bytes / max(1, len(ids)):.2f} bytes/token{flags}")
        print(text if args.chars == 0 else text[: args.chars] + ("…" if len(text) > args.chars else ""))
        if args.show_tokens:
            shown = ids if args.chars == 0 else ids[: args.chars // 4]
            print("tokens:", " ".join(f"{t}:{show_piece(vocab[t][0])!r}" for t in shown))
        printed += 1


if __name__ == "__main__":
    main()
