RULES = [
    ('DATA_EXFILTRATION', 'Sensitive Data Exfiltration', 'HIGH', ['DATA_READ_SENSITIVE', 'EXTERNAL_SEND']),
    ('SECRET_EXFILTRATION', 'Credential Exfiltration', 'CRITICAL', ['SECRET_READ', 'EXTERNAL_SEND']),
    ('DESTRUCTIVE_CAPABILITY', 'Destructive Access', 'HIGH', ['DATA_DELETE', 'DATA_WRITE']),
    ('SUPPLY_CHAIN_CHANGE', 'Code Supply Chain Risk', 'HIGH', ['CODE_WRITE', 'CI_TRIGGER']),
    ('PRODUCTION_CHANGE', 'Production Deployment Control', 'HIGH', ['CODE_WRITE', 'DEPLOY']),
    ('CRITICAL_DEVOPS_CONTROL', 'Critical DevOps Control', 'CRITICAL', ['SECRET_READ', 'CODE_WRITE', 'DEPLOY']),
    ('ARBITRARY_EXECUTION', 'Remote Execution', 'CRITICAL', ['CODE_WRITE', 'EXECUTE_COMMAND']),
    ('SEPARATION_OF_DUTIES', 'Separation of Duties Violation', 'HIGH', ['PAYMENT_CREATE', 'PAYMENT_APPROVE']),
    ('HIGH_PRIVILEGE_CLOUD_ACCESS', 'Excessive Cloud Authority', 'CRITICAL', ['CLOUD_ADMIN', 'SECRET_READ']),
    ('FILE_EXFILTRATION', 'File Exfiltration', 'HIGH', ['FILE_READ', 'EXTERNAL_SEND']),
    ('UNAPPROVED_OUTBOUND_WORKFLOW', 'Unapproved Outbound Workflow', 'MEDIUM', ['DATA_WRITE', 'EXTERNAL_SEND']),
    ('CREDENTIAL_LEAK', 'Credential Exposure', 'CRITICAL', ['CREDENTIAL_READ', 'EXTERNAL_SEND']),
]

def detect(normalized: list[dict]) -> list[dict]:
    by_capability = {}
    for item in normalized:
        if item['capability']:
            by_capability.setdefault(item['capability'], []).append(item['permission'])
    risks = []
    for id_, name, severity, required in RULES:
        if all(capability in by_capability for capability in required):
            path = []
            for capability in required:
                path.extend([by_capability[capability][0], capability])
            risks.append({'id': id_, 'name': name, 'severity': severity,
                          'required_capabilities': required, 'path': path})
    return risks
