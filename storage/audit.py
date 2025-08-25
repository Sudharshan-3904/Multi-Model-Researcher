import os
from datetime import datetime

class AuditLogger:
    def __init__(self, log_file='audit.log'):
        print(f"[audit.py] AuditLogger initialized with log_file={log_file}")
        self.log_file = log_file

    def log_action(self, actor, action, details=None):
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'actor': actor,
            'action': action,
            'details': details or {}
        }
        print(f"[audit.py] Logging action: {entry}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(str(entry) + '\n')
