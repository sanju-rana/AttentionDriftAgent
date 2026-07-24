import requests

class APIClient:
    @staticmethod
    def send(payload):
        try:
            response = requests.post(
            "http://localhost:8000/events",
            json=payload,
            timeout=5
            )

            print(f"Status: {response.status_code}")

            try:
                print(response.json())
            except Exception:
                print(response.text)

        except Exception as e:
                print(f"Request failed: {e}")