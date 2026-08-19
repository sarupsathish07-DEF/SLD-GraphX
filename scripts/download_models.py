"""Model acquisition entry point; intentionally has no undeclared downloads yet."""
import json
from pathlib import Path


def main() -> None:
    manifest = json.loads(Path("models/manifest.json").read_text(encoding="utf-8"))
    if manifest["models"]:
        raise SystemExit("Model download adapters have not been implemented yet.")
    raise SystemExit("No model is registered. Add a licensed, checksummed entry first.")


if __name__ == "__main__":
    main()
