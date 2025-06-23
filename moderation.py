from datetime import datetime, timedelta
from collections import defaultdict, deque

# In-memory storage
reports = defaultdict(list)  # reported_id -> list of reports
bans = {}  # device_id -> ban_info
report_windows = defaultdict(deque)  # reported_id -> deque of report times

# Configuration for moderation
REPORT_THRESHOLD = 3  # Number of reports to trigger a ban
BAN_DURATION_HOURS = 24
REPORT_WINDOW_HOURS = 24

def is_banned(device_id):
    """Check if a device is currently banned."""
    if device_id in bans:
        if bans[device_id]['expires_at'] > datetime.utcnow():
            return True
        else:
            # Clean up expired bans
            del bans[device_id]
    return False

def create_ban(device_id):
    """Create a new ban for a user."""
    expires_at = datetime.utcnow() + timedelta(hours=BAN_DURATION_HOURS)
    bans[device_id] = {
        'reason': 'Multiple reports received',
        'banned_at': datetime.utcnow(),
        'expires_at': expires_at
    }
    print(f'Banned device {device_id} for {BAN_DURATION_HOURS} hours.')

def handle_report(reporter_id, reported_id, reason=None):
    """Handle a user report and potentially ban the reported user."""
    current_time = datetime.utcnow()
    
    # Add the report
    report = {
        'reporter_id': reporter_id,
        'reported_id': reported_id,
        'reason': reason,
        'created_at': current_time
    }
    reports[reported_id].append(report)
    
    # Track report timing for rate limiting
    report_windows[reported_id].append(current_time)
    
    # Clean up old reports (older than 24 hours)
    cutoff_time = current_time - timedelta(hours=REPORT_WINDOW_HOURS)
    while (report_windows[reported_id] and 
           report_windows[reported_id][0] < cutoff_time):
        report_windows[reported_id].popleft()
    
    # If threshold is reached, ban the user
    if len(report_windows[reported_id]) >= REPORT_THRESHOLD:
        create_ban(reported_id)
        return True
    
    return False
