from itosub.nlp.translator.factory import get_translator

def test_factory_stub_aliases_to_argos():
    tr = get_translator("stub")
    assert tr.name == "argos"


def test_factory_configures_reverse_language_direction():
    tr = get_translator("argos", from_code="ja", to_code="en")
    assert tr.from_code == "ja"
    assert tr.to_code == "en"
