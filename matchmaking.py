from collections import deque
import logging

logger = logging.getLogger(__name__)

class MatchmakingQueue:
    """A simple in-memory queue for matching chat partners."""
    def __init__(self):
        self._queue = deque()
        self._debug = False  # Set to False for production

    def add_user(self, sid):
        """Add a user's session ID to the queue if not already present."""
        if sid not in self._queue:
            self._queue.append(sid)
            if self._debug:
                logger.debug(f'[MATCHMAKING] Added user {sid} to queue. Queue size: {len(self._queue)}')
        else:
            if self._debug:
                logger.debug(f'[MATCHMAKING] User {sid} already in queue')

    def remove_user(self, sid):
        """Remove a user's session ID from the queue if they exist."""
        try:
            self._queue.remove(sid)
            if self._debug:
                logger.debug(f'[MATCHMAKING] Removed user {sid} from queue. Queue size: {len(self._queue)}')
        except ValueError:
            if self._debug:
                logger.debug(f'[MATCHMAKING] User {sid} not found in queue')

    def find_partner(self, sid):
        """Try to find a partner for the given user.

        If a partner is found, both users are removed from the queue and the
        partner's SID is returned. Otherwise, the user is added to the queue
        and None is returned.
        """
        if sid in self._queue:
            self._queue.remove(sid)
            if self._debug:
                logger.debug(f'[MATCHMAKING] Removed {sid} from queue (duplicate find_partner call)')

        if len(self._queue) > 0:
            # Partner found
            partner_sid = self._queue.popleft()
            if partner_sid == sid:
                if self._debug:
                    logger.error(f'[MATCHMAKING] Found self as partner: {sid}')
                self.add_user(sid)  # Put back in queue
                return None
            
            if self._debug:
                logger.info(f'[MATCHMAKING] Matched {sid} with {partner_sid}. Queue size: {len(self._queue)}')
            return partner_sid
        else:
            # No partner found, add user to queue
            self.add_user(sid)
            if self._debug:
                logger.info(f'[MATCHMAKING] No partner found for {sid}. Added to queue. Queue size: {len(self._queue)}')
            return None

    def __len__(self):
        return len(self._queue)

# A single instance of the queue to be used by the application
matchmaking_queue = MatchmakingQueue()
