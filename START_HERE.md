# Start here

1. Install **Docker Desktop** and keep it running in Linux-container mode.
2. Extract this ZIP and open a terminal in the `retail-loss-prevention` folder.
3. Run `python scripts/configure.py` to choose your admin login and generate `.env`.
   - Without Python: copy `.env.example` to `.env`, replace both `replace-with-...` values and the admin email. Use a random secret of at least 32 characters and a password of at least 12 characters.
4. Run `docker compose up --build -d`.
5. Open **http://localhost:8080** and log in.
6. Go to **Stores & cameras**, add a store and camera, then upload and process your footage from **Video library**.

The first build needs internet and several GB of free disk space. The first tracking run downloads YOLO weights. Your video stays on your computer.

This is a working upload/processing/review application. It does not connect directly to a live CCTV feed or create AI accusations. Tracking produces neutral observations; people create and classify cases.

To upload the source to GitHub, follow the **GitHub upload** section in README.md. Do not upload `.env`, private videos or database files. A GitHub repository alone does not host the running backend/database.

For the exact test results and the untested Docker deployment limitation, see docs/verification.md.
