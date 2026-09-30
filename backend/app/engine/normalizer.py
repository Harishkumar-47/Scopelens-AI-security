from app.models import AgentInput
from app.providers.generic import GenericAdapter
from app.providers.mcp import MCPAdapter
from app.providers.oauth import OAuthAdapter
from app.providers.aws_iam import AWSIAMAdapter
from app.providers.azure_rbac import AzureRBACAdapter
from app.providers.gcp_iam import GCPIAMAdapter
from app.providers.github import GitHubAdapter

ADAPTERS = {'generic': GenericAdapter(), 'mcp': MCPAdapter(), 'oauth': OAuthAdapter(),
            'aws_iam': AWSIAMAdapter(), 'azure_rbac': AzureRBACAdapter(),
            'gcp_iam': GCPIAMAdapter(), 'github': GitHubAdapter()}

CAPABILITIES = {
    'DATA_READ_PUBLIC', 'DATA_READ_INTERNAL', 'DATA_READ_SENSITIVE', 'DATA_WRITE', 'DATA_DELETE',
    'FILE_READ', 'FILE_WRITE', 'FILE_DELETE', 'EXTERNAL_SEND', 'INTERNAL_SEND', 'CODE_READ',
    'CODE_WRITE', 'EXECUTE_COMMAND', 'EXECUTE_CODE', 'CREDENTIAL_READ', 'SECRET_READ',
    'CI_TRIGGER', 'DEPLOY', 'CLOUD_READ', 'CLOUD_WRITE', 'CLOUD_ADMIN', 'IDENTITY_READ',
    'IDENTITY_WRITE', 'PAYMENT_CREATE', 'PAYMENT_APPROVE', 'ADMIN', 'NETWORK_READ',
    'NETWORK_CHANGE', 'TOOL_INVOKE'
}

MAPPING = {
    'customer.read': 'DATA_READ_SENSITIVE', 'customer_db.read': 'DATA_READ_SENSITIVE',
    'customer_db.delete': 'DATA_DELETE', 'drive.read': 'FILE_READ', 'drive.readonly': 'FILE_READ',
    'gmail.send': 'EXTERNAL_SEND', 'gmail.read': 'DATA_READ_INTERNAL',
    'email.send_external': 'EXTERNAL_SEND', 'email.send_internal': 'INTERNAL_SEND',
    'ticket.create': 'DATA_WRITE', 'github.read': 'CODE_READ',
    'github.contents.read': 'CODE_READ', 'github.contents.write': 'CODE_WRITE',
    'github.write': 'CODE_WRITE', 'github.actions.trigger': 'CI_TRIGGER',
    'aws.secretsmanager.getsecretvalue': 'SECRET_READ', 'secretsmanager:getsecretvalue': 'SECRET_READ',
    'aws.iam.*': 'CLOUD_ADMIN', 'cloud.deploy': 'DEPLOY', 'shell.execute': 'EXECUTE_COMMAND',
    'payments.create': 'PAYMENT_CREATE', 'payments.approve': 'PAYMENT_APPROVE',
    'invoice.read': 'DATA_READ_INTERNAL', 's3:getobject': 'DATA_READ_INTERNAL',
    'lambda:updatefunctioncode': 'CODE_WRITE', 'codebuild:startbuild': 'CI_TRIGGER',
    'cloudformation:updatestack': 'DEPLOY', 'microsoft.graph.mail.send': 'EXTERNAL_SEND',
    'storage.objects.get': 'DATA_READ_INTERNAL', 'compute.instances.setmetadata': 'CLOUD_WRITE',
    'microsoft.authorization/roleassignments/write': 'CLOUD_ADMIN'
}

def normalize(agent: AgentInput) -> list[dict]:
    result = []
    for permission in ADAPTERS[agent.provider].permissions(agent):
        key = permission.lower()
        capability = MAPPING.get(key)
        if not capability and permission in CAPABILITIES:
            capability = permission
        if not capability and key.startswith('mcp.'):
            candidate = permission.rsplit('.', 1)[-1]
            capability = candidate if candidate in CAPABILITIES else None
        if not capability and key.startswith('iam:'):
            capability = 'CLOUD_ADMIN'
        if capability:
            result.append({'permission': permission, 'capability': capability, 'provider': agent.provider})
        else:
            result.append({'permission': permission, 'capability': None, 'provider': agent.provider})
    return result
