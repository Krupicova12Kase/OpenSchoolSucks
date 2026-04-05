import requests
import certifi

response = requests.get("https://is.psjg.cz/student/student-exam-overview",
                        params={
                            "subjectId": "1619",
                            "studentId": "3881"
                        },
                        verify=certifi.where())
print(response.status_code)
print(response.text)
