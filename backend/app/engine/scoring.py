WEIGHTS = {'DATA_READ_SENSITIVE': 15, 'FILE_READ': 5, 'EXTERNAL_SEND': 15,
           'DATA_WRITE': 8, 'SECRET_READ': 25, 'CODE_WRITE': 15,
           'EXECUTE_COMMAND': 20, 'DEPLOY': 20, 'ADMIN': 25, 'CLOUD_ADMIN': 25,
           'DATA_DELETE': 15, 'PAYMENT_CREATE': 8, 'PAYMENT_APPROVE': 8,
           'CI_TRIGGER': 8, 'CREDENTIAL_READ': 20}
RISK_WEIGHTS = {'DATA_EXFILTRATION': 30, 'SECRET_EXFILTRATION': 35,
                'DESTRUCTIVE_CAPABILITY': 25, 'SUPPLY_CHAIN_CHANGE': 20,
                'PRODUCTION_CHANGE': 20, 'CRITICAL_DEVOPS_CONTROL': 35,
                'ARBITRARY_EXECUTION': 35, 'SEPARATION_OF_DUTIES': 30,
                'HIGH_PRIVILEGE_CLOUD_ACCESS': 35, 'FILE_EXFILTRATION': 3,
                'CREDENTIAL_LEAK': 35}

def score(capabilities: list[str], risks: list[dict]) -> tuple[int, str]:
    value = min(100, sum(WEIGHTS.get(c, 0) for c in set(capabilities)) +
                sum(RISK_WEIGHTS.get(r['id'], 0) for r in risks))
    severity = 'CRITICAL' if value >= 80 else 'HIGH' if value >= 60 else 'MEDIUM' if value >= 30 else 'LOW'
    return value, severity
