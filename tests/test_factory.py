from itosub.nlp.translator.factory import get_translator

def test_factory_stub():
    tr = get_translator("stub")
    assert tr.name == "stub"