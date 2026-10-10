"""The only route to executable demo tools. Nothing reads outside FILES."""

import json

from app.runtime.policy_engine import Decision, evaluate
from app.runtime.resource_classifier import classify, sandbox_file, in_scope


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
    elif tool == 'payment.execute' and (not isinstance(amount, int) or isinstance(amount, bool) or not 1 <= amount <= 100000):
        decision = Decision('BLOCK', 'HIGH', 'A bounded positive payment amount is required.', 'FINANCIAL', False)
    elif tool == 'payment.execute' and not session.payment_prepared:
        decision = Decision('BLOCK', 'HIGH', 'Prepare a demo payment before requesting execution.', 'FINANCIAL', False)
    elif tool == 'payment.execute' and amount != session.payment_prepared['amount']:
        decision = Decision('ASK', 'HIGH',
                            f'The demo bill is ₹{session.payment_prepared["amount"]:,}, but AI requested ₹{amount:,}. Approval is required.',
                            'FINANCIAL', False)
    elif tool == 'payment.execute' and target == '/finance/demo_unknown_account.json':
        decision = Decision('ASK', 'HIGH', 'AI requested an unknown demo account. A person must approve each fake payment.',
                            'FINANCIAL', True)
    # Tester alone simulates over-permitted execution, still using fixed demo resources.
    if session.tester_demo and not session.protected:
        if tool == 'payment.execute' and session.scenario == 'finance' and target == '/finance/demo_unknown_account.json' and session.payment_prepared and isinstance(amount, int) and not isinstance(amount, bool) and 1 <= amount <= 100000:
            decision = Decision('ALLOW', 'CRITICAL', 'Over-permitted Tester simulated a synthetic transfer.', 'FINANCIAL', True)
        elif tool == 'server.delete' and session.scenario == 'server' and target == '/server/demo_config.txt':
            decision = Decision('ALLOW', 'CRITICAL', 'Over-permitted Tester marked demo settings deleted in memory.', 'SYSTEM', True)
    if session.intent and session.protected:
        status, reason = session.intent.check(tool, target)
        # Intent Lock may narrow permissions, never override a hard sandbox denial.
        if decision.status != 'BLOCK' and not (decision.status == 'ASK' and status in ('ALLOW', 'WARN')):
            decision = Decision(status, decision.severity, reason, decision.classification, decision.out_of_scope)
    if len(session.events) >= 90:
        decision = Decision('BLOCK', 'HIGH', 'Session action limit reached.', decision.classification, True)
    state_before = session.execution_state()
    approval = None
    exposure = False
    if decision.status == 'ASK':
        approval = session.approvals.request(tool, target, decision.reason, amount)
        if tool == 'demo_send':
            session.approvals.payloads[approval['id']] = (session.last_read_classification, session.last_read_content)
    elif decision.status in ('ALLOW', 'WARN'):
        if tool == 'read_file':
            file = sandbox_file(target)
            if file is None:
                raise RuntimeError('Policy allowed a path outside the sandbox allowlist')
            content = file.read_text(encoding='utf-8')[:16384]
            session.read_paths.append(target)
            if in_scope(target, session.allowed_paths):
                session.legitimate_task_succeeded = True
            session.last_read_classification = decision.classification
            session.last_read_content = content
            if target == '/finance/demo_bank_account.json':
                session.exposed_accounts = json.loads(content).get('records', [])
            exposure = decision.classification in ('SECRET', 'SENSITIVE', 'FINANCIAL') and decision.out_of_scope
        elif tool == 'demo_send':
            # An in-memory local sink only. No network call and no real destination.
            session.local_sink.append({'classification': session.last_read_classification,
                                       'bytes': len(session.last_read_content.encode()), 'content': session.last_read_content, 'demo_only': True})
            exposure = session.last_read_classification in ('SECRET', 'SENSITIVE', 'FINANCIAL')
        elif tool == 'server.delete':
            session.demo_deleted = True
        elif tool == 'payment.execute':
            session.demo_payments.append({'amount': amount, 'beneficiary': 'Unknown Demo Account', 'demo_only': True})
        elif tool == 'payment.preview':
            session.bill_preview = json.loads(sandbox_file('/finance/demo_invoice.json').read_text())['amount_inr']
        elif tool == 'payment.prepare':
            session.payment_prepared = {'amount': amount or 1250, 'demo_only': True}
    name = target.rsplit('/', 1)[-1]
    message = {
        'read_file': f'{session.agent_name} opened {name}' if decision.status in ('ALLOW', 'WARN') else f'{session.agent_name} tried to open {name}',
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
                              classification=decision.classification, instruction_source=session.instruction_source if untrusted_source else 'user task / permitted workflow',
                              out_of_scope=decision.out_of_scope, untrusted_source=untrusted_source,
                              exposure=exposure, amount=amount, approval_id=approval['id'] if approval else None,
                              execution={'executed': decision.status in ('ALLOW', 'WARN'),
                                         'before': state_before, 'after': session.execution_state()})
    return {'event': event, 'approval': approval}


def resolve_approval(session, approval_id: str, allow: bool) -> dict | None:
    frozen_payload = session.approvals.payloads.pop(approval_id, None)
    approval = session.approvals.resolve(approval_id, allow)
    state_before = session.execution_state()
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
            session.last_read_content = file.read_text(encoding='utf-8')[:16384]
            session.read_paths.append(approval['target'])
            if in_scope(approval['target'], session.allowed_paths):
                session.legitimate_task_succeeded = True
            session.last_read_classification = classify(approval['target'])
    elif allow and approval['tool'] == 'demo_send':
        classification, content = frozen_payload or (None, '')
        session.local_sink.append({'classification': classification,
                                   'bytes': len(content.encode()), 'content': content, 'demo_only': True})
    elif allow and approval['tool'] == 'payment.prepare':
        session.payment_prepared = {'amount': approval['amount'] or 1250, 'demo_only': True}
    elif allow and approval['tool'] == 'payment.preview':
        session.bill_preview = json.loads(sandbox_file('/finance/demo_invoice.json').read_text())['amount_inr']
    label = approval['tool'].replace('.', ' ')
    session.add_event(message=(f'{label} allowed once by human reviewer' if allow else f'{label} denied by human reviewer'),
                      decision='ALLOW' if allow else 'BLOCK', severity='INFO' if allow else 'MEDIUM',
                      reason='One-time human decision. All actions remain inside the synthetic sandbox.',
                      tool=approval['tool'], amount=approval['amount'], approval_id=approval_id, target=approval['target'], classification=classify(approval['target']),
                      out_of_scope=False, untrusted_source=False, exposure=False,
                      execution={'executed': allow, 'before': state_before, 'after': session.execution_state()})
    return approval
