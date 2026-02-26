from itosub.nlp.translator.factory import get_translator

def test_factory_stub_aliases_to_argos():
    tr = get_translator("stub")
    assert tr.name == "argos"
