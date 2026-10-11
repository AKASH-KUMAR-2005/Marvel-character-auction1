# Marvel Character Auction Battle — Quick Start (Hindi)

1. Python 3.10+ और Node.js 18+ इंस्टॉल करें।
2. Backend चलाएँ:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\\Scripts\\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   python app.py
   ```
3. दूसरे terminal में frontend चलाएँ:
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   npm run dev
   ```
4. Browser में `http://127.0.0.1:5173` खोलें।
5. Live AI के लिए `backend/.env` में अपना `OPENAI_API_KEY` डालें। API key frontend में कभी न रखें। Key न होने पर भी SQLite local catalog से game खेल सकते हैं और battle report local fallback के रूप में मिलेगा।

विस्तृत endpoints, rules, tests और licensing notes के लिए `README.md` देखें।
