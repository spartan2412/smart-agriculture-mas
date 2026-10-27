from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collect_crida_ccp_evidence import build_document_url, extract_pdf_evidence


def test_ccp_document_url_uses_official_state_district_structure():
    assert (
        build_document_url("PB", "Ludhiana", "1.7.pdf")
        == "https://icar-crida.res.in/CCP/PB/Ludhiana/1.7.pdf"
    )


def test_crop_keyword_check_uses_extracted_pdf_text(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage("Paddy is the principal kharif crop in 2008-09.")]

    monkeypatch.setattr("scripts.collect_crida_ccp_evidence.PdfReader", FakeReader)
    pages, characters, keyword_found, periods = extract_pdf_evidence(b"not used", "rice")

    assert pages == 1
    assert characters > 0
    assert keyword_found is True
    assert periods == "2008-09"


def test_chickpea_match_accepts_standalone_gram_but_not_green_or_black_gram(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage("Rabi crops: Gram, green gram and black gram in 2008-09.")]

    monkeypatch.setattr("scripts.collect_crida_ccp_evidence.PdfReader", FakeReader)
    assert extract_pdf_evidence(b"not used", "chickpea")[2] is True

    class OnlyOtherGramsReader:
        def __init__(self, _stream):
            self.pages = [FakePage("Kharif pulses are green gram and black gram in 2008-09.")]

    monkeypatch.setattr("scripts.collect_crida_ccp_evidence.PdfReader", OnlyOtherGramsReader)
    assert extract_pdf_evidence(b"not used", "chickpea")[2] is False
