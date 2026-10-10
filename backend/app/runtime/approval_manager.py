from uuid import uuid4
import time


class ApprovalManager:
    def __init__(self):
        self.pending: dict[str, dict] = {}
        self.payloads: dict[str, tuple] = {}

    def request(self, tool: str, target: str, reason: str, amount: int | None = None) -> dict:
        approval = {'id': str(uuid4()), 'tool': tool, 'target': target, 'reason': reason,
                    'amount': amount, 'status': 'PENDING', 'expires_at': time.time() + 120}
        self.pending[approval['id']] = approval
        return approval

    def resolve(self, approval_id: str, allow: bool) -> dict | None:
        approval = self.pending.pop(approval_id, None)
        if approval and approval['expires_at'] > time.time():
            approval['status'] = 'ALLOWED_ONCE' if allow else 'DENIED'
            return approval
        return None
