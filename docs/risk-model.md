# Risk model

ScopeLens Exposure Score is a transparent, prototype-specific 0–100 score. It is not an industry standard. Each unique capability adds a fixed weight and each detected combination adds a fixed weight; the total is capped at 100. LOW: 0–29, MEDIUM: 30–59, HIGH: 60–79, CRITICAL: 80–100.

The 12 deterministic rules cover sensitive data exfiltration, secret exfiltration, destructive data access, supply chain changes, production changes, critical DevOps control, remote execution, payment separation of duties, cloud authority, file exfiltration, unapproved outbound workflows, and credential leakage. The exact rule inputs and weights are in `backend/app/engine/risk_engine.py` and `scoring.py`.

The Support Agent score is 76 from 15 sensitive read + 5 file read + 15 external send + 8 data write + 30 sensitive exfiltration + 3 file exfiltration. The third outbound workflow chain has no additional score weight. Removing external send yields 28 and removes all three chains.

This is a capability combination model. It does not claim exploitability, actual data movement, or complete provider authorization semantics. Unknown permissions are displayed and require manual review.
