"""Verify that PyTorch can use the GTX 1080 Ti (Pascal, sm_61) in fp32.

Run: uv run python scripts/check_gpu.py
"""

from __future__ import annotations

import sys

import torch


def main() -> int:
    print(f"torch          {torch.__version__}")
    print(f"built for CUDA {torch.version.cuda}")
    if not torch.cuda.is_available():
        print("FAIL: CUDA not available (CPU-only torch build or driver problem)")
        return 1

    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 2**30
    print(f"device         {name}")
    print(f"capability     sm_{cap[0]}{cap[1]}")
    print(f"VRAM           {vram:.1f} GiB")
    print(f"arch list      {' '.join(torch.cuda.get_arch_list())}")

    # The real test: a kernel must actually run ("no kernel image" errors surface here).
    try:
        a = torch.randn(2048, 768, device="cuda")
        b = a @ a.T
        torch.cuda.synchronize()
        ok = torch.allclose(b.diagonal(), (a * a).sum(dim=1), rtol=1e-3, atol=1e-2)
    except RuntimeError as e:
        print(f"FAIL: kernel did not run: {e}")
        return 1
    if not ok:
        print("FAIL: fp32 matmul result mismatch")
        return 1

    print("OK: fp32 matmul ran on GPU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
