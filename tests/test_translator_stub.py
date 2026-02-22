from itosub.contracts import TranslationRequest
from itosub.nlp.translator.stub import StubTranslator

def test_stub_translator_deterministic():
    tr = StubTranslator()
    out = tr.translate(TranslationRequest(text="Hello world."))
    assert out.provider == "stub"
    assert "Hello world." in out.translated_text
