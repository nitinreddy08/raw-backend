from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Using in-memory storage for rate limiting
)

def init_extensions(app):
    """Initialize Flask extensions with the application."""
    socketio.init_app(app)
    limiter.init_app(app)
