"""The only route to executable demo tools. Nothing reads outside FILES."""

from app.runtime.policy_engine import Decision, evaluate
from app.runtime.resource_classifier import classify, sandbox_file


def execute(session, tool: str, target: str, *, amount: int | None = None,
            untrusted_source: bool = False) -> dict:
    decision = evaluate(tool, target, session.allowed_paths, session.protected,
                        source_untrusted=untrusted_source,
                        payload_classification=session.last_read_classification)
    if tool.startswith('payment.') and session.scenario != 'finance':
        decision = Decision('BLOCK', 'HIGH', 'Payment tools are unavailable to this agent.', 'FINANCIAL', True)
    elif tool.startswith('payment.') and target != (
            '/finance/demo_invoice.json' if tool == 'payment.preview' else '/finance/demo_payment_profile.json'):
        decision = Decision('BLOCK', 'HIGH', 'Payment tools are limited to synthetic finance resources.', 'FINANCIAL', True)
    elif tool == 'payment.execute' and not session.payment_prepared:
        decision = Decision('BLOCK', 'HIGH', 'Prepare a demo payment before requesting execution.', 'FINANCIAL', False)
    approval = None
    exposure = False
    if decision.status == 'ASK':
        approval = session.approvals.request(tool, target, decision.reason, amount)
    elif decision.status == 'ALLOW':
        if tool == 'read_file':
            file = sandbox_file(target)
            if file is None:
                raise RuntimeError('Policy allowed a path outside the sandbox allowlist')
            content = file.read_text(encoding='utf-8')
            session.last_read_classification = decision.classification
            session.last_read_content = content
            exposure = decision.classification == 'SECRET' and decision.out_of_scope
        elif tool == 'demo_send':
            # An in-memory local sink only. No network call and no real destination.
            session.local_sink.append({'classification': session.last_read_classification,
                                       'bytes': len(session.last_read_content.encode()), 'demo_only': True})
            exposure = session.last_read_classification == 'SECRET'
        elif tool == 'payment.prepare':
            session.payment_prepared = {'amount': amount or 5000, 'demo_only': True}
    message = {
        'read_file': f'Agent requested {target}',
        'demo_send': 'Agent requested a send to the local demo sink',
        'payment.preview': 'Agent previewed a demo payment',
        'payment.prepare': 'Agent prepared a demo payment',
        'payment.execute': 'Agent requested a demo payment execution',
    }.get(tool, f'Agent requested {tool}')
    if decision.status == 'BLOCK':
        message += ' · BLOCKED'
    elif decision.status == 'ASK':
        message += ' · APPROVAL REQUIRED'
    elif exposure:
        message += ' · SIMULATED DATA EXPOSURE'
    event = session.add_event(message=message, decision=decision.status, severity=decision.severity,
                              reason=decision.reason, tool=tool, target=target,
                              classification=decision.classification,
                              out_of_scope=decision.out_of_scope, untrusted_source=untrusted_source,
                              exposure=exposure, approval_id=approval['id'] if approval else None)
    return {'event': event, 'approval': approval}


def resolve_approval(session, approval_id: str, allow: bool) -> dict | None:
    approval = session.approvals.resolve(approval_id, allow)
    if approval is None:
        return None
    if allow and approval['tool'] == 'payment.execute':
        session.demo_payments.append({'amount': approval['amount'] or 5000, 'demo_only': True})
    elif allow and approval['tool'] == 'read_file':
        file = sandbox_file(approval['target'])
        if file:
            session.last_read_content = file.read_text(encoding='utf-8')
            session.last_read_classification = classify(approval['target'])
    elif allow and approval['tool'] == 'demo_send':
        session.local_sink.append({'classification': session.last_read_classification,
                                   'bytes': len(session.last_read_content.encode()), 'demo_only': True})
    label = approval['tool'].replace('.', ' ')
    session.add_event(message=(f'{label} allowed once by human reviewer' if allow else f'{label} denied by human reviewer'),
                      decision='ALLOW' if allow else 'BLOCK', severity='INFO' if allow else 'MEDIUM',
                      reason='One-time human decision. All actions remain inside the synthetic sandbox.',
                      tool=None, target=approval['target'], classification=classify(approval['target']),
                      out_of_scope=False, untrusted_source=False, exposure=False)
    return approval
