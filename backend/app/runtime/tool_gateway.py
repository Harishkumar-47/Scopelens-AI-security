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
    elif tool == 'server.delete' and session.scenario != 'server':
        decision = Decision('BLOCK', 'HIGH', 'Server tools are unavailable to this agent.', 'SYSTEM', True)
    elif tool.startswith('payment.') and target not in (
            ('/finance/demo_invoice.json',) if tool == 'payment.preview' else
            ('/finance/demo_payment_profile.json', '/finance/demo_unknown_account.json') if tool == 'payment.execute' else
            ('/finance/demo_payment_profile.json',)):
        decision = Decision('BLOCK', 'HIGH', 'Payment tools are limited to synthetic finance resources.', 'FINANCIAL', True)
    elif tool == 'payment.execute' and not session.payment_prepared:
        decision = Decision('BLOCK', 'HIGH', 'Prepare a demo payment before requesting execution.', 'FINANCIAL', False)
    elif tool == 'payment.execute' and amount != session.payment_prepared['amount']:
        decision = Decision('ASK', 'HIGH',
                            f'The demo bill is ₹{session.payment_prepared["amount"]:,}, but AI requested ₹{amount:,}. Approval is required.',
                            'FINANCIAL', False)
    elif tool == 'payment.execute' and target == '/finance/demo_unknown_account.json':
        decision = Decision('ASK', 'HIGH', 'AI requested an unknown demo account. A person must approve each fake payment.',
                            'FINANCIAL', True)
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
            exposure = decision.classification in ('SECRET', 'SENSITIVE') and decision.out_of_scope
        elif tool == 'demo_send':
            # An in-memory local sink only. No network call and no real destination.
            session.local_sink.append({'classification': session.last_read_classification,
                                       'bytes': len(session.last_read_content.encode()), 'demo_only': True})
            exposure = session.last_read_classification in ('SECRET', 'SENSITIVE')
        elif tool == 'payment.prepare':
            session.payment_prepared = {'amount': amount or 5000, 'demo_only': True}
    name = target.rsplit('/', 1)[-1]
    message = {
        'read_file': f'{session.agent_name} opened {name}' if decision.status == 'ALLOW' else f'{session.agent_name} tried to open {name}',
        'demo_send': f'{session.agent_name} tried to send data to the local demo receiver',
        'payment.preview': 'Payment Helper checked the ₹1,250 demo bill',
        'payment.prepare': 'Payment Helper prepared the ₹1,250 demo bill',
        'payment.execute': f'Payment Helper wants to send ₹{amount:,}' if amount else 'Payment Helper wants to send money',
        'server.delete': 'Server Helper tried to delete demo server settings',
    }.get(tool, f'{session.agent_name} requested {tool}')
    if decision.status == 'BLOCK':
        message += ' · BLOCKED'
    elif decision.status == 'ASK':
        message += ' · ASK ME'
    elif exposure:
        message += ' · DEMO DATA EXPOSED'
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
        payment = {'amount': approval['amount'] or 5000, 'demo_only': True}
        if approval['target'] == '/finance/demo_unknown_account.json':
            payment['beneficiary'] = 'Unknown Demo Account'
        session.demo_payments.append(payment)
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
