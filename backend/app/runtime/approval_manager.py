from uuid import uuid4


class ApprovalManager:
    def __init__(self):
        self.pending: dict[str, dict] = {}

    def request(self, tool: str, target: str, reason: str, amount: int | None = None) -> dict:
        approval = {'id': str(uuid4()), 'tool': tool, 'target': target, 'reason': reason,
                    'amount': amount, 'status': 'PENDING'}
        self.pending[approval['id']] = approval
        return approval

    def resolve(self, approval_id: str, allow: bool) -> dict | None:
        approval = self.pending.pop(approval_id, None)
        if approval:
            approval['status'] = 'ALLOWED_ONCE' if allow else 'DENIED'
        return approval
