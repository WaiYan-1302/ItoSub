# tests/test_postprocess_en.py
from itosub.nlp.postprocess_en import normalize_en

def test_normalize_en_am_time():
    assert normalize_en("at 1.30 a.m.") == "at 1:30 a.m."