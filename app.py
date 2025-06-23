import os
import eventlet
eventlet.monkey_patch()  # Must be done before other imports

from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
from config import DevelopmentConfig, ProductionConfig
from extensions import socketio, limiter
from matchmaking import matchmaking_queue
from moderation import is_banned, handle_report
import logging
from logging.handlers import RotatingFileHandler

# Apply eventlet monkey patch
try:
    eventlet.monkey_patch()
except Exception as e:
    print(f"Warning: Could not apply eventlet monkey patch: {e}")

# In-memory stores (will be replaced with Redis in production)
partners = {}  # sid -> partner_sid
sessions = {}  # sid -> {'ip': ip, 'device_id': device_id}

def create_app(config_class=None):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        config_class = ProductionConfig if env == 'production' else DevelopmentConfig
    
    app.config.from_object(config_class)
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/rawchat.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('RawChat startup')

    # Initialize rate limiter
    limiter.init_app(app)
    
    # Configure CORS
    CORS(
        app,
        resources={
            r"/*": {
                "origins": app.config['CORS_ORIGINS'],
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
                "expose_headers": ["Content-Disposition"]
            }
        }
    )
    
    # Initialize Socket.IO
    socketio.init_app(
        app,
        cors_allowed_origins='*',  # Allow all origins for development
        async_mode='eventlet',
        logger=True,
        engineio_logger=True,
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=1e8,  # 100MB
        cookie=None  # Disable cookie for now
    )

    # A simple test route
    @app.route('/')
    def index():
        return "RawChat API is running!"

    # SocketIO event handlers
    @socketio.on('connect')
    def handle_connect(auth):
        sid = request.sid
        ip_address = request.remote_addr
        device_id = auth.get('deviceId') if auth else None

        if not device_id:
            print(f"Client {sid} connected without a deviceId. Disconnecting.")
            return False  # Reject the connection

        # Check if the user is banned
        if is_banned(device_id):
            print(f'Banned user tried to connect: {sid}, IP: {ip_address}, DeviceID: {device_id}')
            socketio.emit('banned', {'reason': 'You are temporarily banned due to reports.'}, room=sid)
            return False  # Reject connection

        print(f'Client connected: {sid}, IP: {ip_address}, DeviceID: {device_id}')
        sessions[sid] = {'ip': ip_address, 'device_id': device_id}

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        print(f'Client disconnected: {sid}')
        # If the user was in a pair, notify the partner
        if sid in partners:
            partner_sid = partners.pop(sid)
            if partner_sid in partners:
                partners.pop(partner_sid)
            socketio.emit('partner_disconnected', room=partner_sid)
        else:
            # If they were waiting, remove them from the queue
            matchmaking_queue.remove_user(sid)
        # Clean up session info
        if sid in sessions:
            del sessions[sid]

    @socketio.on('find_partner')
    def find_partner(data):
        sid = request.sid
        print(f'[DEBUG] Client {sid} is looking for a partner.')
        
        # Remove from any existing partnership
        if sid in partners:
            old_partner = partners[sid]
            if old_partner in partners:
                del partners[old_partner]
            del partners[sid]
            print(f'[DEBUG] Removed old partnership for {sid}')
        
        # Find a new partner
        partner_sid = matchmaking_queue.find_partner(sid)
        print(f'[DEBUG] Matchmaking result for {sid}: partner={partner_sid}')

        if partner_sid and partner_sid != sid:  # Make sure we don't pair with ourselves
            partners[sid] = partner_sid
            partners[partner_sid] = sid
            print(f'[DEBUG] Paired {sid} with {partner_sid}')
            socketio.emit('partner_found', {'partner_id': partner_sid}, room=sid)
            socketio.emit('partner_found', {'partner_id': sid}, room=partner_sid)
        else:
            print(f'[DEBUG] Client {sid} is waiting in the queue. Queue size: {len(matchmaking_queue._queue)}')
            socketio.emit('waiting_for_partner', room=sid)

    @socketio.on('signal')
    def handle_signal(data):
        sid = request.sid
        print(f'[SIGNAL] Received signal from {sid}, type: {data.get("type")}')
        
        if sid in partners:
            partner_sid = partners[sid]
            print(f'[SIGNAL] Forwarding signal to partner {partner_sid}')
            
            # Add 'from' field to identify the sender
            data_with_sender = dict(data)
            data_with_sender['from'] = sid
            
            try:
                socketio.emit('signal', data_with_sender, room=partner_sid)
                print(f'[SIGNAL] Signal forwarded successfully to {partner_sid}')
            except Exception as e:
                print(f'[SIGNAL] Error forwarding signal: {str(e)}')
        else:
            print(f'[SIGNAL] Warning: Client {sid} sent a signal but has no partner. Data: {data}')

    @socketio.on('report_user')
    def handle_user_report(data):
        reporter_sid = request.sid
        if reporter_sid not in partners or reporter_sid not in sessions:
            return  # Ignore report if user is not in a pair or has no session

        offender_sid = partners[reporter_sid]
        offender_info = sessions.get(offender_sid)
        reporter_info = sessions.get(reporter_sid)

        if not offender_info or not reporter_info:
            return # Ignore if session info is missing

        with app.app_context():
            handle_report(
                reporter_id=reporter_info['device_id'],
                offender_id=offender_info['device_id'],
                reason=data.get('reason', 'nudity'),
                ip_address=offender_info['ip'],
                device_id=offender_info['device_id']
            )
        
        socketio.emit('report_received', {'message': 'Your report has been submitted.'}, room=reporter_sid)

    return app



# To run the app
if __name__ == '__main__':
    app = create_app()
    # Note: Use socketio.run for development to enable WebSockets
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
