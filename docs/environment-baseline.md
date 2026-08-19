# Environment baseline

Captured 2026-08-19 before Bootstrap 0 implementation.

| Item | Observed value |
| --- | --- |
| OS / shell | Windows 11 build 26200 / PowerShell 7.6.4 |
| CPU | Intel Core Ultra 9 285H, 16 logical processors |
| RAM | 31.5 GiB |
| GPU | Intel Arc 140T visible to Windows (shared-memory reporting) |
| C: free space | 13.8 GiB at capture |
| Git | 2.52.0.windows.1 |
| Python candidates | 3.14 and 3.10; project selects 3.10 for broad CV/OCR compatibility |
| Node / npm | Node 26.4.0 / npm 11.17.0 |
| pnpm | Bundled fallback available; npm selected for the single frontend package |
| Docker | Not found; not required |

Base Python dependencies are installed in `.venv-sldgraphx`. OCR and detector runtimes are deliberately deferred until their platform compatibility is smoke-tested.
