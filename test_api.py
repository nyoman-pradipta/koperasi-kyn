import requests

url = "https://koperasi-684nrc0cv-nyomanpradipta.vercel.app/api/reminders/log?schedule_id=1&member_id=1&loan_id=1&phone=628123456789"
resp = requests.post(url)
print("Status:", resp.status_code)
print("Response:", resp.text)
