<div align="center">

# 🛡️ HPH v2

### **Hardened Multi-Layer Educational Payload Hider**

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=20&duration=2800&pause=900&color=00F7FF&center=true&vCenter=true&width=700&lines=Educational+Red-Team+Research;Multi-Layer+Payload+Protection;Cryptography+%2B+Obfuscation;Anti-Tamper+%2B+Anti-Debug;Built+for+Security+Research" alt="Typing Animation" />

<br>

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge\&logo=python\&logoColor=white)](https://www.python.org/)
[![Cryptography](https://img.shields.io/badge/Cryptography-AES%20%2B%20ChaCha20-00A67D?style=for-the-badge\&logo=letsencrypt\&logoColor=white)](#-cryptographic-pipeline)
[![Security Research](https://img.shields.io/badge/Purpose-Security%20Research-FF0055?style=for-the-badge\&logo=hackthebox\&logoColor=white)](#-disclaimer)
[![License](https://img.shields.io/badge/License-Research%20Use-8A2BE2?style=for-the-badge)](#-license)
[![GitHub](https://img.shields.io/badge/GitHub-im--aswajith-181717?style=for-the-badge\&logo=github)](https://github.com/im-aswajith)

<br>

**A layered Python protection experiment designed to make static and automated analysis significantly more difficult.**

> ⚠️ **Educational / Lab / Red-Team Research Project**

</div>

---

## ⚡ What Is HPH?

**HPH — Hardened Payload Hider** is a Python-based educational security research tool that transforms a Python source program into a protected loader.

Instead of simply encoding or encrypting a payload once, the project applies **multiple transformation, encryption, integrity, fragmentation, and runtime-hardening layers**.

The project is explicitly designed around the idea that:

> **Obfuscation is not unbreakable security. It is a cost multiplier for analysis.**

The implementation itself acknowledges that a determined analyst with access to runtime memory can potentially recover the payload.

---

# 🧬 Architecture

```text
                    ┌─────────────────────┐
                    │    Python Source    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Compile        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Marshal        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   LZMA Compression  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    AES-256-GCM      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  ChaCha20-Poly1305  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   zlib Compression  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ SHA-256 XOR Stream  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Base64        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Fragment + Shuffle  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Protected Loader  │
                    └─────────────────────┘
```

The implemented pipeline is:

```text
source
  ↓
compile
  ↓
marshal
  ↓
LZMA
  ↓
AES-256-GCM
  ↓
ChaCha20-Poly1305
  ↓
zlib
  ↓
SHA-256 keystream XOR
  ↓
Base64
```

This ordering is implemented directly in the project.

---

# 🔐 Security Layers

## 01 — Multi-Layer Cryptographic Processing

The payload passes through multiple cryptographic stages:

* AES-256-GCM
* ChaCha20-Poly1305
* HKDF-SHA256 key derivation
* SHA-256 counter-mode XOR transformation
* Random nonces
* Random salt

The project derives separate keys for the AES, ChaCha20 and keystream stages using HKDF.

---

## 02 — XOR-Split Master Key

The master key is not stored as a single obvious value.

Instead, it is split into multiple XOR shares:

```text
                MASTER KEY
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     SHARE 01      SHARE 02     SHARE 03
        │            │            │
        └──────┬─────┴─────┬──────┘
               │           │
               ▼           ▼
             SHARE 04   SHARE 05
                    │
                    ▼
                 SHARE 06
                    │
                    ▼
             XOR Reconstruction
                    │
                    ▼
               MASTER KEY
```

The implementation generates **six shares**, shuffles them, and reconstructs the master key only at runtime.

---

## 03 — Payload Fragmentation

The encoded payload is divided into randomly sized chunks.

The chunks are then shuffled and accompanied by an index map.

```text
Original Payload
──────────────────────────────────────>

       [ A ][ B ][ C ][ D ][ E ]

                 ↓ Shuffle

       [ D ][ A ][ E ][ C ][ B ]

                 ↓

             Index Map

                 ↓

       Runtime Reconstruction
```

This makes the payload harder to identify as one continuous static string.

---

# 🕵️ Anti-Debug Layer

The generated loader contains several runtime checks.

### Detection mechanisms

```text
┌───────────────────────────────┐
│       Runtime Environment     │
├───────────────────────────────┤
│ • sys.gettrace()              │
│ • sys.getprofile()            │
│ • /proc/self/status           │
│ • TracerPid detection         │
│ • sys.monitoring debugger     │
│ • Opaque predicate            │
└───────────────────────────────┘
                 │
                 ▼
          Environment Check
                 │
        ┌────────┴────────┐
        ▼                 ▼
     Clean             Debugged
        │                 │
        ▼                 ▼
     Continue          Exit
```

The loader checks tracing/profiling state, Linux `TracerPid`, Python monitoring state, and an opaque predicate.

---

# 🧪 Self-Tamper Detection

The generated loader contains a self-hash mechanism.

At startup it:

1. Reads its own source.
2. Replaces the embedded hash placeholder.
3. Calculates SHA-256.
4. Compares the result against the expected hash.
5. Terminates if the integrity check fails.

```text
             Loader
                │
                ▼
          Read own file
                │
                ▼
        Normalize hash field
                │
                ▼
            SHA-256
                │
        ┌───────┴───────┐
        ▼               ▼
      Match           Mismatch
        │               │
        ▼               ▼
     Continue           Exit
```

The self-hash verification is implemented in the generated loader.

---

# 🔗 Payload Integrity

Before decryption, the reconstructed Base64 payload is checked against a SHA-256 integrity value.

```python
sha256(payload)
        │
        ▼
   Expected Hash
        │
   ┌────┴────┐
   ▼         ▼
 MATCH     FAIL
   │         │
   ▼         ▼
Continue    Exit
```

This protects against modifications to the embedded payload.

---

# 🖥️ Optional Machine Binding

HPH can optionally bind the generated loader to the machine on which it was created.

The binding material uses:

```text
Hostname
    +
Username
    +
MAC / Node Identifier
```

The resulting information is incorporated into the key-derivation process.

```text
          Machine
             │
     ┌───────┼────────┐
     ▼       ▼        ▼
 Hostname  User   Node ID
     │       │        │
     └───────┼────────┘
             ▼
       Binding Material
             │
             ▼
        HKDF Derivation
```

Machine binding is optional and can be enabled with `--bind`.

> ⚠️ Machine binding makes the output less portable.

---

# 🎲 Build Randomization

Each generated loader receives randomized internal identifiers.

For example:

```text
_ad = randomized
_xor = randomized
_kd = randomized
_mk = randomized
_run = randomized
```

The project generates these identifiers randomly for every build.

This means two builds of the same input can have different internal structures.

---

# 📦 Installation

Clone the repository:

```bash
git clone https://github.com/im-aswajith/HPH.git
cd HPH
```

Install the required dependency:

```bash
pip install cryptography
```

Or, if a `requirements.txt` file is included:

```bash
pip install -r requirements.txt
```

---

# 🚀 Usage

Basic protection:

```bash
python hph.py payload.py
```

Specify an output file:

```bash
python hph.py payload.py -o protected.py
```

Enable machine binding:

```bash
python hph.py payload.py --bind
```

The CLI accepts an input Python file, optionally accepts an output path, and exposes `--bind` for machine-bound protection.

---

# 🧩 Example

### Input

```text
payload.py
```

### Command

```bash
python hph.py payload.py -o protected.py
```

### Output

```text
protected.py
```

The tool reports the generated protection layers:

```text
[+] Hardened protected script written: protected.py
[+] Pipeline : marshal -> LZMA -> AES-256-GCM -> ChaCha20-Poly1305
               -> zlib -> SHA-256 keystream XOR -> base64
[+] Master key XOR-split into 6 obfuscated shares (shuffled)
[+] Payload fragmented into shuffled chunks with index map
[+] Anti-debug probes, payload integrity, self-hash tamper check
[+] Machine binding: OFF
```

These messages correspond to the project's implemented CLI output.

---

# 🗂️ Project Structure

```text
HPH/
│
├── hph.py
├── README.md
├── requirements.txt
├── LICENSE
│
└── examples/
    └── payload.py
```

> Adjust this structure if your repository contains additional files.

---

# 🧠 Design Philosophy

HPH is built around several security-research concepts:

| Layer              | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| Compilation        | Convert source into Python code objects          |
| Marshal            | Serialize the compiled object                    |
| LZMA               | Compress intermediate representation             |
| AES-GCM            | Authenticated encryption                         |
| ChaCha20-Poly1305  | Additional authenticated encryption layer        |
| HKDF               | Derive independent cryptographic keys            |
| XOR Keystream      | Additional transformation layer                  |
| Base64             | Represent binary data as text                    |
| Key Splitting      | Avoid a single obvious master-key representation |
| Fragmentation      | Break payload into shuffled pieces               |
| Anti-Debug         | Detect selected runtime analysis environments    |
| Integrity Hash     | Detect payload modification                      |
| Self-Hash          | Detect loader modification                       |
| Random Identifiers | Reduce deterministic static patterns             |
| Machine Binding    | Optionally restrict execution environment        |

---

# 📊 Protection Pipeline

```text
                    ┌───────────────┐
                    │ Python Source │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    Compile    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    Marshal    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │     LZMA      │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │   AES-256-GCM │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ ChaCha20-P1305│
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │     zlib      │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ SHA-256 XOR   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    Base64     │
                    └───────┬───────┘
                            ↓
                ┌──────────────────────┐
                │ Fragment + Shuffle   │
                └──────────┬───────────┘
                           ↓
                ┌──────────────────────┐
                │  Protected Loader   │
                └──────────────────────┘
```

---

# ⚠️ Important Security Reality

HPH should **not** be considered an unbreakable protection system.

If an attacker controls the execution environment, the protected payload eventually has to be reconstructed and executed in memory.

Therefore:

```text
Static Analysis
      │
      ▼
More Difficult
      │
      ▼
Runtime Analysis
      │
      ▼
Memory Inspection
      │
      ▼
Potential Payload Recovery
```

The project's own documentation explicitly states that the design is intended to make static/AI-assisted reversal more expensive rather than impossible.

---

# 🧪 Research Applications

This project can be useful for studying:

* 🔐 Applied cryptography
* 🧩 Python bytecode internals
* 🛡️ Software protection techniques
* 🔬 Reverse engineering
* 🧠 Static analysis
* 🕵️ Anti-debugging concepts
* 🔎 Malware-analysis methodology
* 🧪 Red-team laboratory research
* 📦 Payload transformation techniques
* 🔒 Integrity and tamper detection

Use it only in systems and environments where you have authorization.

---

# 🛡️ Threat Model

HPH primarily attempts to increase the cost of:

```text
✓ Basic static inspection
✓ Simple string extraction
✓ Straightforward payload discovery
✓ Deterministic pattern matching
✓ Basic debugging
✓ Basic loader modification
```

It does **not** guarantee protection against:

```text
✗ Memory dumps
✗ Full runtime instrumentation
✗ Skilled reverse engineering
✗ Python interpreter instrumentation
✗ Controlled execution environments
✗ Determined human analysis
```

---

# 🧬 Technical Highlights

```text
┌─────────────────────────────────────────────┐
│                 HPH v2                      │
├─────────────────────────────────────────────┤
│                                             │
│  🔐 AES-256-GCM                             │
│  🔐 ChaCha20-Poly1305                       │
│  🔑 HKDF-SHA256                             │
│  🧩 XOR Key Sharing                         │
│  🧱 Payload Fragmentation                   │
│  🕵️ Anti-Debug Checks                       │
│  🛡️ Self-Tamper Detection                  │
│  🔎 Payload Integrity                       │
│  🎲 Randomized Identifiers                  │
│  🖥️ Optional Machine Binding               │
│                                             │
└─────────────────────────────────────────────┘
```

---

# 📈 Development Roadmap

```text
[████████████████████] Core Pipeline       ✓

[████████████████████] Key Splitting       ✓

[████████████████████] Payload Fragmenting ✓

[████████████████████] Anti-Debug          ✓

[████████████████████] Integrity Checks    ✓

[████████████████████] Self-Tamper Check   ✓

[████████████████████] Machine Binding     ✓

[░░░░░░░░░░░░░░░░░░░░] Test Suite           ○

[░░░░░░░░░░░░░░░░░░░░] Benchmarking         ○

[░░░░░░░░░░░░░░░░░░░░] Research Docs        ○
```

---

# 🤝 Contributing

Contributions are welcome for legitimate security research and educational improvements.

Possible areas:

* Better test coverage
* Cross-platform compatibility
* Documentation
* Benchmarking
* Cryptographic design review
* Research experiments
* Defensive analysis tooling

Before submitting changes, please ensure that your contribution is intended for authorized research, education, or defensive security work.

---

# 📜 License

This project is intended for **educational, laboratory, and authorized security research purposes**.

Do not use it to conceal unauthorized malware, evade security controls, compromise systems, or access data without permission.

See the repository's `LICENSE` file for the exact legal terms.

---

# ⚖️ Disclaimer

> **HPH is a security research and educational project.**
>
> The author does not guarantee that generated payloads are secure, undetectable, irreversible, or impossible to analyze.
>
> Users are responsible for ensuring that their use of this project complies with applicable laws, organizational policies, and authorization requirements.
>
> Do not deploy generated protected payloads against systems that you do not own or have explicit permission to test.

---

# 👨‍💻 Author

<div align="center">

### **Aswajith**

Security Research • Python • Cryptography • Reverse Engineering

<br>

<a href="https://github.com/im-aswajith">
  <img src="https://img.shields.io/badge/GitHub-im--aswajith-181717?style=for-the-badge&logo=github" />
</a>

<br><br>

<img src="https://komarev.com/ghpvc/?username=im-aswajith&style=for-the-badge&color=00F7FF&label=PROFILE+VIEWS" />

</div>

---

# ⭐ Support

If this project helped you learn something about:

```text
Cryptography
     +
Python Internals
     +
Reverse Engineering
     +
Software Protection
     =
Security Research
```

consider giving the repository a ⭐.

---

<div align="center">

### 🔐 Build • Break • Analyze • Learn

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=120&section=footer" />

**© 2026 im-aswajith**

</div>

