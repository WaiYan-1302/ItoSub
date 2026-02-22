from __future__ import annotations
from .base import Translator
from itosub.contracts import TranslationRequest, TranslationResult

class ArgosTranslator(Translator):
    def __init__(self, from_code: str = "en", to_code: str = "ja", auto_install: bool = True):
        self.from_code = from_code
        self.to_code = to_code
        self.auto_install = auto_install
        self._ready = False

    @property
    def name(self) -> str:
        return "argos"

    def _ensure_ready(self) -> None:
        if self._ready:
            return

        import argostranslate.package
        import argostranslate.translate

        installed = argostranslate.translate.get_installed_languages()
        have_from = any(l.code == self.from_code for l in installed)
        have_to = any(l.code == self.to_code for l in installed)

        if not (have_from and have_to):
            if not self.auto_install:
                raise RuntimeError("Argos model not installed and auto_install=False")

            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()

            pkg = None
            for p in available:
                if p.from_code == self.from_code and p.to_code == self.to_code:
                    pkg = p
                    break
            if pkg is None:
                raise RuntimeError(f"No Argos package found for {self.from_code}->{self.to_code}")

            path = pkg.download()
            argostranslate.package.install_from_path(path)

        self._ready = True

    def translate(self, req: TranslationRequest) -> TranslationResult:
        self._ensure_ready()
        import argostranslate.translate
        ja = argostranslate.translate.translate(req.text, self.from_code, self.to_code)
        return TranslationResult(source_text=req.text, translated_text=ja, provider=self.name)