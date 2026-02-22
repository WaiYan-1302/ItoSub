from __future__ import annotations
import argparse
from itosub.contracts import TranslationRequest
from itosub.nlp.translator.factory import get_translator

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to UTF-8 text file (English). Use - for stdin.")
    ap.add_argument("--provider", default=None, help="stub | argos (or set ITOSUB_TRANSLATOR)")
    args = ap.parse_args()

    if args.input == "-":
        text = input().strip()
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()

    tr = get_translator(args.provider)
    res = tr.translate(TranslationRequest(text=text))

    print(f"[provider] {res.provider}")
    print("---- EN ----")
    print(res.source_text)
    print("---- JA ----")
    print(res.translated_text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())