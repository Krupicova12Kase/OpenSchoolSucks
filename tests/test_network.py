from app import certificates, certificates_list, certificate_chain
import requests
from os import path

def test_certificate_check():
    certificate = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'certificates', certificate_chain)
    certificates(cert_list=certificates_list)
    try:
        response = requests.get("https://is.psjg.cz", verify=certificate)
        assert response.status_code == 200
        assert True, "Certificate is valid and connection is successful."
    except requests.exceptions.SSLError as e:
        assert False, f"SSL Error: {e}"
    except Exception as e:
        assert False, f"Unexpected error: {e}"