# RawChat Backend

This is the backend for RawChat, a real-time chat application using Flask, Flask-SocketIO, and Eventlet.

## Features

- Real-time chat with WebSockets
- Matchmaking queue for pairing users
- Moderation and user reporting
- Rate limiting and CORS support

## Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd rawchat-backend
   ```
2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set environment variables:**
   - Create a `.env` file in the root directory with the following (example):
     ```env
     SECRET_KEY=your-secret-key
     CORS_ORIGINS=*
     LOG_LEVEL=INFO
     ```

## Running the Server

```bash
python app.py
```

The server will run on `http://0.0.0.0:5001` by default.

## Project Structure

- `app.py` - Main application entry point
- `config.py` - Configuration classes
- `extensions.py` - Flask extensions setup
- `matchmaking.py` - Matchmaking queue logic
- `moderation.py` - Moderation and reporting logic
- `requirements.txt` - Python dependencies
- `logs/` - Log files (ignored by git)

## Notes

- **Do not commit sensitive data** (e.g., real secret keys) to the repository.
- The `logs/` directory and `.env` files are excluded from version control via `.gitignore`.

## License

MIT
