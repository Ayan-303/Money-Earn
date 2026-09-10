# Money Earn

A working local Flask + SQLite prototype with:
- Register/login
- 3 task submissions
- Admin approval before coins are credited
- VIP 1–5 membership payment submissions
- Easypaisa details: Abid Afzal / 03034201512
- Withdrawal requests
- Referral code tracking
- Admin panel

## Run
1. Install Python 3.
2. In this folder:
   pip install -r requirements.txt
   python app.py
3. Open http://127.0.0.1:5000

## Admin demo
Phone: 03000000000
Password: admin123

Change the admin password and SECRET_KEY before public deployment.

## Important
This app intentionally does not promise guaranteed returns. VIP membership payments do not automatically generate cash rewards. Task rewards should only be funded by genuine advertiser/sponsor revenue.


## Deployment
See DEPLOY.md. Production entrypoint: `gunicorn app:app`.
