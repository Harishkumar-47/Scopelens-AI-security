from dataclasses import dataclass
from app.runtime.resource_classifier import resource_info, sandbox_file

CODING_SCOPE = ('/workspace/github-project/**',)
FINANCE_SCOPE = ('/finance/demo_invoice.json', '/finance/demo_payment_profile.json')
TOOL_DEFINITIONS = {
    'read_file': {'description': 'Read a synthetic sandbox file', 'capability': 'FILE_READ',
                  'risk_level': 'CONTEXTUAL', 'allowed_paths': list(CODING_SCOPE), 'requires_approval': False},
    'demo_send': {'description': 'Send only to an in-memory local demo sink', 'capability': 'EXTERNAL_SEND',
                  'risk_level': 'HIGH', 'allowed_paths': [], 'requires_approval': True},
    'payment.preview': {'description': 'Preview a fake payment', 'capability': 'PAYMENT_CREATE',
                        'risk_level': 'LOW', 'allowed_paths': list(FINANCE_SCOPE), 'requires_approval': False},
    'payment.prepare': {'description': 'Prepare a fake payment', 'capability': 'PAYMENT_CREATE',
                        'risk_level': 'MEDIUM', 'allowed_paths': list(FINANCE_SCOPE), 'requires_approval': False},
    'payment.execute': {'description': 'Simulate a fake payment after one-time approval',
                        'capability': 'PAYMENT_APPROVE', 'risk_level': 'HIGH',
                        'allowed_paths': list(FINANCE_SCOPE), 'requires_approval': True},
}


@dataclass(frozen=True)
class Decision:
    status: str
    severity: str
    reason: str
    classification: str
    out_of_scope: bool


def evaluate(tool: str, target: str, scope: tuple[str, ...], protected: bool,
             source_untrusted: bool = False, payload_classification: str | None = None) -> Decision:
    info = resource_info(target, scope)
    classification = info['classification']
    outside = info['out_of_scope']
    if tool == 'read_file':
        if sandbox_file(target) is None:
            return Decision('BLOCK', 'HIGH', 'Path is not an executable file in the synthetic sandbox.', classification, outside)
        if not protected:
            return Decision('ALLOW', 'CRITICAL' if classification == 'SECRET' and outside else 'INFO',
                            'Unprotected lab mode permits this synthetic sandbox read.', classification, outside)
        if outside and classification in ('SECRET', 'FINANCIAL', 'SYSTEM', 'SENSITIVE'):
            return Decision('BLOCK', 'CRITICAL', f'{classification} resource outside the assigned workspace.', classification, True)
        if outside:
            return Decision('ASK', 'MEDIUM', 'Resource is outside the assigned workspace.', classification, True)
        return Decision('ALLOW', 'INFO', 'File is inside the assigned workspace.', classification, False)
    if tool == 'demo_send':
        if target != 'local-demo-sink':
            return Decision('BLOCK', 'HIGH', 'Only the local demonstration sink exists.', classification, outside)
        if protected and (payload_classification in ('SECRET', 'FINANCIAL', 'SENSITIVE') or source_untrusted):
            return Decision('BLOCK', 'CRITICAL', 'Untrusted content led to an attempted sensitive send.', payload_classification or 'OUT_OF_SCOPE', True)
        if protected:
            return Decision('ASK', 'HIGH', 'Outbound transfer requires approval.', payload_classification or 'NORMAL', False)
        return Decision('ALLOW', 'CRITICAL' if payload_classification == 'SECRET' else 'HIGH',
                        'Unprotected lab mode permits a local simulated send.', payload_classification or 'NORMAL', False)
    if tool == 'payment.preview':
        return Decision('ALLOW', 'INFO', 'Viewing a synthetic payment preview is permitted.', 'FINANCIAL', False)
    if tool == 'payment.prepare':
        return Decision('ALLOW', 'INFO', 'Preparing a synthetic payment does not execute it.', 'FINANCIAL', False)
    if tool == 'payment.execute':
        return Decision('ASK', 'HIGH', 'Every demo payment requires a one-time human approval.', 'FINANCIAL', False)
    return Decision('BLOCK', 'HIGH', 'Unknown tool is not available through the ScopeLens gateway.', classification, outside)
