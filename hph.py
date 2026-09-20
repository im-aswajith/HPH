#!/usr/bin/env python3
"""
Hardened multi-layer educational payload hider (v2)
(Lab / red-team research only)

Pipeline (correct order):
  source -> compile -> marshal -> LZMA -> AES-256-GCM -> ChaCha20-Poly1305
         -> zlib -> SHA-256 keystream XOR -> base64

Hardening added in v2:
  * Master key is XOR-split into N obfuscated shares (never stored whole)
  * Payload string is fragmented into shuffled chunks with an index map
  * Anti-debug probes: sys.gettrace / getprofile / sys.monitoring /
    /proc/self/status TracerPid / opaque predicate
  * Self-hash tamper check over the loader file itself
  * Per-build randomised identifiers and shuffled share order
  * All key material zeroed/recomputed at runtime, never written in clear

Still NOT unbreakable against a determined human + memory dump.
The goal is to make static/AI-assisted reversal expensive, not impossible.
"""

import argparse
import base64
import hashlib
import lzma
import marshal
import os
import random
import secrets
import string
import sys
import zlib
from string import Template

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def _rnd_name(minlen: int = 7, maxlen: int = 13) -> str:
    """Random identifier that cannot collide with a Python keyword."""
    return "_" + "".join(
        random.choices(string.ascii_letters, k=random.randint(minlen, maxlen))
    )


def _xor_keystream(data: bytes, key: bytes) -> bytes:
    """SHA-256 counter-mode keystream XOR. Self-inverse."""
    out = bytearray(len(data))
    ctr = 0
    pos = 0
    while pos < len(data):
        blk = hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        for b in blk:
            if pos >= len(data):
                break
            out[pos] = data[pos] ^ b
            pos += 1
        ctr += 1
    return bytes(out)


def _split_secret(secret: bytes, n: int):
    """XOR secret-sharing: XOR of all shares == secret."""
    if n < 2:
        raise ValueError("n must be >= 2")
    shares = [secrets.token_bytes(len(secret)) for _ in range(n - 1)]
    last = bytearray(secret)
    for s in shares:
        for i, b in enumerate(s):
            last[i] ^= b
    shares.append(bytes(last))
    return shares


def _encode_shares(shares):
    """Render each share as a different Python expression (source lines)."""
    lines = []
    for i, s in enumerate(shares):
        mode = i % 6
        if mode == 0:
            lines.append("    bytes.fromhex(%r)," % s.hex())
        elif mode == 1:
            lines.append("    bytes(%r)," % (list(s),))
        elif mode == 2:
            lines.append("    _B.b64decode(%r)," % base64.b64encode(s).decode())
        elif mode == 3:
            lines.append("    bytes(reversed(%r))," % (bytes(reversed(s)),))
        elif mode == 4:
            pad = secrets.token_bytes(len(s))
            masked = bytes(a ^ b for a, b in zip(s, pad))
            lines.append(
                "    bytes(a ^ b for a, b in zip(%r, %r))," % (masked, pad)
            )
        else:
            half = len(s) // 2
            lines.append("    (%r + %r)," % (s[:half], s[half:]))
    return "\n".join(lines)


def _fragment(payload: str):
    """Split the payload into shuffled chunks + index map."""
    n = len(payload)
    k = random.randint(8, 16)
    if k >= n:
        k = max(2, n // 2)
    pts = sorted(random.sample(range(1, n), k - 1))
    chunks = []
    prev = 0
    for p in pts:
        chunks.append(payload[prev:p])
        prev = p
    chunks.append(payload[prev:])

    order = list(range(len(chunks)))
    random.shuffle(order)
    shuffled = [chunks[order[i]] for i in range(len(chunks))]
    inv = [order.index(j) for j in range(len(chunks))]
    return shuffled, inv


# ----------------------------------------------------------------------------
# loader template (string.Template -> $placeholders)
# ----------------------------------------------------------------------------

LOADER_TEMPLATE = Template(r'''#!/usr/bin/env python3
# Hardened multi-layer protected script (educational / lab use only).
# Pipeline : marshal -> LZMA -> AES-256-GCM -> ChaCha20-Poly1305 -> zlib
#            -> SHA-256 keystream XOR -> base64
# Hardening: XOR-split master key, fragmented payload, anti-debug probes,
#            payload integrity, self-hash tamper check, opaque predicates,
#            randomised identifiers, no plaintext key material in the file.
import base64 as _B, hashlib as _H, lzma as _L, marshal as _M, os as _O, sys as _S, zlib as _Z
from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AG, ChaCha20Poly1305 as _CP
from cryptography.hazmat.primitives import hashes as _HS
from cryptography.hazmat.primitives.kdf.hkdf import HKDF as _HK
$bind_block
_PH = b"SELFHASH" + b"0" * 56
_SELFHASH = "$selfhash"


def $n_ad():
    try:
        if _S.gettrace() is not None:
            _O._exit(11)
        if _S.getprofile() is not None:
            _O._exit(12)
    except Exception:
        pass
    try:
        with open("/proc/self/status") as _f:
            for _ln in _f:
                if _ln.startswith("TracerPid:"):
                    if int(_ln.split()[1]) != 0:
                        _O._exit(13)
    except Exception:
        pass
    try:
        if hasattr(_S, "monitoring") and _S.monitoring.get_tool(_S.monitoring.DEBUGGER_ID) is not None:
            _O._exit(14)
    except Exception:
        pass
    if (lambda x: (x * x + 7) % 97)(13) == 0:
        _O._exit(15)
    return True


def $n_xor(d, k):
    o = bytearray(len(d))
    c = 0
    p = 0
    while p < len(d):
        blk = _H.sha256(k + c.to_bytes(8, "big")).digest()
        for x in blk:
            if p >= len(d):
                break
            o[p] = d[p] ^ x
            p += 1
        c += 1
    return bytes(o)


def $n_kd(m, s, info, ln=32):
    return _HK(algorithm=_HS.SHA256(), length=ln, salt=s, info=info).derive(m + _BIND)


def $n_mk():
    b = bytearray($n_sh[0])
    for i in range(1, len($n_sh)):
        s = $n_sh[i]
        for j in range(len(b)):
            b[j] ^= s[j]
    return bytes(b)


_SAL = $salt
_EXP = "$integrity"
$n_sh = [
$shares_code
]
$n_pay = [
$chunks_code
]
$n_idx = $idx_code


def $n_run():
    $n_ad()
    mk = $n_mk()
    pay = "".join($n_pay[i] for i in $n_idx)
    if _H.sha256(pay.encode("ascii")).hexdigest() != _EXP:
        _O._exit(21)
    d = _B.b64decode(pay)
    d = $n_xor(d, $n_kd(mk, _SAL, b"L3/keystream", 64))
    d = _Z.decompress(d)
    n2, ct2 = d[:12], d[12:]
    d = _CP($n_kd(mk, _SAL, b"L2/chacha")).decrypt(n2, ct2, None)
    n1, ct1 = d[:12], d[12:]
    d = _AG($n_kd(mk, _SAL, b"L1/aes")).decrypt(n1, ct1, None)
    d = _L.decompress(d)
    exec(_M.loads(d), {"__name__": "__main__", "__file__": __file__})


if __name__ == "__main__":
    try:
        _raw = open(__file__, "rb").read().replace(_SELFHASH.encode(), _PH)
        if _H.sha256(_raw).hexdigest() != _SELFHASH:
            _O._exit(31)
    except OSError:
        pass
    $n_run()
''')


# ----------------------------------------------------------------------------
# build
# ----------------------------------------------------------------------------

def protect(source: str, bind: bool = False) -> str:
    # 1) compile -> marshal
    code_obj = compile(source, "<protected>", "exec")
    raw = marshal.dumps(code_obj)

    # 2) fresh secret material every build
    master = secrets.token_bytes(32)
    salt = secrets.token_bytes(16)

    # 3) optional machine binding
    if bind:
        import socket
        import getpass
        import uuid
        try:
            bind_bytes = (
                socket.gethostname() + "|" + getpass.getuser() + "|" + str(uuid.getnode())
            ).encode()
        except Exception:
            bind_bytes = b""
        bind_block = (
            "\nimport socket as _SK, getpass as _GP, uuid as _UU\n"
            "try:\n"
            "    _BIND = (_SK.gethostname() + \"|\" + _GP.getuser() + \"|\" "
            "+ str(_UU.getnode())).encode()\n"
            "except Exception:\n"
            "    _BIND = b''\n"
        )
    else:
        bind_bytes = b""
        bind_block = "_BIND = b''"

    def kd(info: bytes, length: int = 32) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(), length=length, salt=salt, info=info
        ).derive(master + bind_bytes)

    k_aes = kd(b"L1/aes")
    k_cha = kd(b"L2/chacha")
    k_xor = kd(b"L3/keystream", 64)

    # 4) encryption pipeline
    data = lzma.compress(raw, preset=9 | lzma.PRESET_EXTREME)
    n1 = os.urandom(12)
    data = n1 + AESGCM(k_aes).encrypt(n1, data, None)
    n2 = os.urandom(12)
    data = n2 + ChaCha20Poly1305(k_cha).encrypt(n2, data, None)
    data = zlib.compress(data, 9)
    data = _xor_keystream(data, k_xor)
    payload = base64.b64encode(data).decode("ascii")

    integrity = hashlib.sha256(payload.encode("ascii")).hexdigest()

    # 5) split the master key and shuffle the shares
    shares = _split_secret(master, 6)
    random.shuffle(shares)
    shares_code = _encode_shares(shares)

    # 6) fragment the payload
    shuffled_chunks, inv = _fragment(payload)
    chunks_code = "\n".join("    %r," % c for c in shuffled_chunks)
    idx_code = repr(inv)

    # 7) randomised identifiers
    names = {
        "ad": _rnd_name(),
        "xor": _rnd_name(),
        "kd": _rnd_name(),
        "mk": _rnd_name(),
        "run": _rnd_name(),
        "sh": _rnd_name(),
        "pay": _rnd_name(),
        "idx": _rnd_name(),
    }

    # 8) self-hash placeholder (64 chars)
    placeholder = "SELFHASH" + "0" * 56

    loader = LOADER_TEMPLATE.substitute(
        bind_block=bind_block,
        n_ad=names["ad"],
        n_xor=names["xor"],
        n_kd=names["kd"],
        n_mk=names["mk"],
        n_run=names["run"],
        n_sh=names["sh"],
        n_pay=names["pay"],
        n_idx=names["idx"],
        salt=repr(salt),
        integrity=integrity,
        shares_code=shares_code,
        chunks_code=chunks_code,
        idx_code=idx_code,
        selfhash=placeholder,
    )

    # 9) compute + inject the self-hash
    real_hash = hashlib.sha256(loader.encode("utf-8")).hexdigest()
    loader = loader.replace(placeholder, real_hash)

    return loader


# ----------------------------------------------------------------------------
# cli
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Hardened multi-layer educational payload hider (v2)"
    )
    ap.add_argument("input", help="Source .py file")
    ap.add_argument("-o", "--output", help="Output protected file")
    ap.add_argument(
        "--bind",
        action="store_true",
        help="Bind decryption to this machine (hostname|user|MAC). "
             "Non-portable but much harder to reverse elsewhere.",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print("File not found:", args.input)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        src = f.read()

    out = args.output or (os.path.splitext(args.input)[0] + "_hardened.py")
    protected = protect(src, bind=args.bind)

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(protected)
    os.chmod(out, 0o755)

    print("[+] Hardened protected script written:", out)
    print("[+] Pipeline : marshal -> LZMA -> AES-256-GCM -> ChaCha20-Poly1305")
    print("               -> zlib -> SHA-256 keystream XOR -> base64")
    print("[+] Master key XOR-split into 6 obfuscated shares (shuffled)")
    print("[+] Payload fragmented into shuffled chunks with index map")
    print("[+] Anti-debug probes, payload integrity, self-hash tamper check")
    print("[+] Machine binding:", "ON" if args.bind else "OFF")
    print("[!] Still NOT impossible to reverse with a memory dump + patience.")


if __name__ == "__main__":
    main()