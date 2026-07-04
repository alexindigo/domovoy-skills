---
name: llama-server-install
description: Guide for building, installing, and setting up llama-server as a systemd service. Covers GPU-specific build flags, driver dependencies, parallelism tuning, runtime environment, and troubleshooting. Use when setting up llama.cpp inference server on a new machine. Delegates PKGBUILD safety to aur-build, model download to hf-model-download, and opencode config to configure-local-models.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: models
  related: [aur-build, aur-install, hf-model-download, configure-local-models]
---

# llama-server Install

Build and set up llama.cpp's `llama-server` for local inference. This skill
covers the entire pipeline from driver prerequisites through systemd service,
delegating to existing skills for PKGBUILD safety review, installation, model
downloads, and opencode configuration.

## Delegation map

```
llama-server-install           ← YOU ARE HERE
  ├── aur-build                PKGBUILD safety review, dependency gate
  ├── aur-install              pacman -U installation
  ├── hf-model-download        downloading GGUF model files
  └── configure-local-models   wiring models into opencode.jsonc
```

---

## 1. Pre-requisites: GPU drivers

Choose your GPU vendor. Only install what's needed for your hardware.

### Intel Arc (SYCL backend — best performance)

```bash
# GPU driver (provides Level Zero + OpenCL kernel driver)
sudo pacman -S intel-compute-runtime

# SYCL compiler + runtime libraries
sudo pacman -S intel-oneapi-toolkit    # ~9 GB, full stack
```

**Alternative:** `intel-deep-learning-essentials` (AUR, smaller subset) —
conflicts with the full toolkit. Pick one.

### Intel Arc (Vulkan backend — lighter, ~40% slower than SYCL)

```bash
# Vulkan driver + loader
sudo pacman -S intel-compute-runtime vulkan-intel vulkan-icd-loader
```

llama.cpp's Vulkan backend needs no extra toolkit. Good for limited disk space
or avoiding the oneAPI install.

### NVIDIA (CUDA backend)

```bash
sudo pacman -S cuda
```

llama.cpp built with `-DGGML_CUDA=ON`.

### AMD (ROCm backend)

```bash
sudo pacman -S rocm-hip-sdk rocm-opencl-sdk
```

llama.cpp built with `-DGGML_HIP=ON`.

### CPU-only (no GPU)

No extra packages. Build with `-DGGML_CUDA=OFF -DGGML_SYCL=OFF` (default).
Slower but runs anywhere.

---

## 2. Building

**Load the `aur-build` skill and follow its PKGBUILD review process.** That
skill handles safety checks, dependency validation, and the mandatory approval
gate. The rest of this section covers llama-server-specific cmake flags and
gotchas.

### Cloning

```bash
mkdir -p ~/aur && cd ~/aur
git clone <aur-repo-url> llama.cpp-<variant>
```

Common AUR packages:
- `llama.cpp-sycl` — Intel Arc SYCL
- `llama.cpp-sycl-f16` — SYCL with F16 math (faster on Battlemage)
- `llama.cpp-cuda` — NVIDIA CUDA
- `llama.cpp-vulkan` — Vulkan (vendor-neutral)
- `llama.cpp` — CPU only
- `llama.cpp-git` — CPU only, latest git

### Build flags by GPU

These go in `build()` in the PKGBUILD's cmake options:

| GPU | Required flags | Notes |
|-----|---------------|-------|
| Intel Arc SYCL | `-DGGML_SYCL=ON -DGGML_SYCL_F16=ON -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx` | Needs `source /opt/intel/oneapi/setvars.sh` before cmake |
| Intel Arc Vulkan | `-DGGML_VULKAN=ON` | No extra compiler needed |
| NVIDIA CUDA | `-DGGML_CUDA=ON` | Needs CUDA toolkit in PATH |
| AMD ROCm | `-DGGML_HIP=ON -DCMAKE_C_COMPILER=hipcc` | Needs ROCm installed |
| CPU | (none, default) | Works out of the box |

### Known gotchas

#### `-DLLAMA_BUILD_UI=OFF` — avoid npm/Vite memory blowup

By default, `llama-server` builds and embeds a Vue.js web UI. This triggers
`npm install` + `npm run build` during cmake, pulling in ~800 MB of
`node_modules` and running Vite/Rollup — easily consuming several GB of RAM.

Set this flag to skip the npm build entirely:

```cmake
-DLLAMA_BUILD_UI=OFF
```

The server still compiles and serves the JSON API at `/v1/*` endpoints. The
browser UI at `/` returns 404s. If you want the UI, use
`-DLLAMA_USE_PREBUILT_UI=ON` instead (downloads pre-built assets from HuggingFace
— no npm involved).

#### Cap parallelism — `-j8` instead of `-j`

SYCL template compilation with `icpx` is memory-intensive. Each template
instantiation for `ggml-sycl` (dozens of quantization format × kernel
combinations) can use 2–4 GB of RAM. On a 16+ core machine, `-j$(nproc)` can
push the system into swap and trigger OOM kills.

```bash
# Instead of:
cmake --build build --config Release -j

# Use:
cmake --build build --config Release -j8
```

Adjust the number based on your system RAM. Rule of thumb: `-j(N/2)` where N =
total threads, or `-j8` for machines with ≤ 32 GB RAM. CUDA builds with `nvcc`
don't have this problem — `-j` is safe there.

#### `intel-compute-runtime` is separate from `intel-oneapi-toolkit`

The full oneAPI toolkit provides the SYCL compiler (`icx`/`icpx`) and runtime
libraries (`libsycl.so`, `libdnnl.so`), but NOT the GPU kernel driver. The
driver is a separate package:

```bash
sudo pacman -S intel-compute-runtime
```

Without it, `llama-server --list-devices` throws a SYCL runtime exception and
crashes with a backtrace through `ggml_backend_sycl_reg()`.

#### `libdnnl.so.3` not found at runtime

llama-server built with SYCL links against `libdnnl.so.3` from the oneAPI
toolkit. The binary's RPATH doesn't include the oneAPI library directory, so
it fails with:

```
llama-server: error while loading shared libraries: libdnnl.so.3: cannot open shared object file
```

**Fix:** Source the oneAPI environment before running:

```bash
source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1 || true
llama-server ...
```

Or set it in the systemd service unit (see section 5).

---

## 3. Installing

**Load the `aur-install` skill and follow its procedure.** That skill handles
`pacman -U`, conflict checks, and post-install verification.

For non-AUR builds (manual `cmake --build` → `cmake --install`):

```bash
sudo cmake --install build --prefix /usr/local
```

---

## 4. GPU detection verification

After installation, verify the GPU is reachable:

```bash
# Source oneAPI env (Intel Arc only):
source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1 || true
export ONEAPI_DEVICE_SELECTOR=level_zero:0

# List available devices:
llama-server --list-devices
```

Expected output (Intel Arc example):
```
Available devices:
  SYCL0: Intel(R) Arc(TM) Pro B50 Graphics (16304 MiB, 12000 MiB free)
```

**Common failures:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `libdnnl.so.3: cannot open` | oneAPI env not sourced | `source /opt/intel/oneapi/setvars.sh` |
| `No device of requested type` | `intel-compute-runtime` missing | `sudo pacman -S intel-compute-runtime` |
| Crash in `ggml_backend_sycl_reg()` | GPU driver missing or Level Zero loader can't find device | Check `ls /dev/dri/`, install `intel-compute-runtime` |
| `ONEAPI_DEVICE_SELECTOR` not recognized | setvars.sh not sourced before export | Source setvars.sh first (it sets env vars for device selection) |

---

## 5. Runtime environment

### Intel Arc — oneAPI environment

The oneAPI `setvars.sh` script sets `LD_LIBRARY_PATH` and other env vars needed
by the SYCL runtime:

```bash
source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1 || true
export ONEAPI_DEVICE_SELECTOR=level_zero:0
```

- `--force` — suppress warnings about already-sourced components
- `ONEAPI_DEVICE_SELECTOR` — select the first Intel GPU via Level Zero backend
- Redirect to `/dev/null` — keep output clean; errors still visible

### Other GPU backends

No special runtime environment needed for CUDA, Vulkan, or CPU.

---

## 6. Systemd service

Create a user-scoped systemd service so llama-server starts automatically.

`~/.config/systemd/user/llama-server.service`:

```ini
[Unit]
Description=llama.cpp inference server
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash -c 'source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1 || true; export ONEAPI_DEVICE_SELECTOR=level_zero:0; exec llama-server --port 8080 --models-dir %h/models --n-gpu-layers 99 --ctx-size 98304'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

**For non-Intel GPUs** (CUDA, Vulkan, CPU), use a simpler ExecStart without
the setvars preamble:

```ini
ExecStart=llama-server --port 8080 --models-dir %h/models --n-gpu-layers 99 --ctx-size 98304
```

Then enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now llama-server.service
```

Verify:

```bash
systemctl --user status llama-server.service --no-pager -l
curl http://localhost:8080/v1/models
```

---

## 7. Post-install: models + opencode config

### Download models

**Load the `hf-model-download` skill.** It handles filename discovery, curl
downloads with resume, and token handling.

Create the model directory and verify:

```bash
mkdir -p ~/models
ls ~/models/*.gguf  # should show downloaded files
```

### Configure opencode

**Load the `configure-local-models` skill.** It discovers models from the
running llama-server API and writes the `opencode.jsonc` provider config with
per-agent routing (build/plan/explore).

---

## 8. Troubleshooting

| Problem | Root cause | Solution |
|---------|-----------|----------|
| Build hangs or OOM at 30% | icpx too many parallel template instantiations | Reduce `-j` flag (see section 2) |
| Build runs npm install/node_modules/Vite | `-DLLAMA_BUILD_UI=ON` (default) | Add `-DLLAMA_BUILD_UI=OFF` |
| `libdnnl.so.3` not found | RPATH doesn't include oneAPI lib dir | Source setvars.sh before running |
| `--list-devices` crashes | GPU driver missing | `sudo pacman -S intel-compute-runtime` |
| `ONEAPI_DEVICE_SELECTOR` has no effect | Var set before setvars.sh | Source setvars.sh first |
| `llama-server` can't find models | `--models-dir` path wrong | Check path, verify `.gguf` files exist |
| `curl localhost:8080/v1/models` fails | Server not running or wrong port | `systemctl --user status llama-server.service` |
