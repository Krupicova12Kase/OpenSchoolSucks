from app import certificate_check, certificates

def test_certificate_check():
    assert certificate_check() == True