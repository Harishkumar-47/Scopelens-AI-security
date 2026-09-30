from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

Provider = Literal['generic', 'mcp', 'oauth', 'aws_iam', 'azure_rbac', 'gcp_iam', 'github']

class AgentInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=500)
    provider: Provider = 'generic'
    permissions: list[str] = Field(default_factory=list, max_length=100)
    manifest: dict[str, Any] | None = None

    @model_validator(mode='after')
    def validate_manifest(self):
        if any(not permission.strip() or len(permission) > 200 for permission in self.permissions):
            raise ValueError('Permissions must be nonempty strings of at most 200 characters')
        if self.manifest is None:
            return self
        key = {'mcp': 'tools', 'oauth': 'scopes', 'azure_rbac': 'actions',
               'gcp_iam': 'permissions', 'github': 'permissions'}.get(self.provider)
        if key:
            entries = self.manifest.get(key, [])
            if not isinstance(entries, list) or len(entries) > 100:
                raise ValueError(f'manifest.{key} must be a list of at most 100 entries')
            if self.provider == 'mcp':
                for tool in entries:
                    if not isinstance(tool, dict) or not isinstance(tool.get('name'), str) or not isinstance(tool.get('capabilities'), list) or not all(isinstance(c, str) for c in tool['capabilities']):
                        raise ValueError('Each MCP tool needs a name and capabilities string list')
            elif not all(isinstance(entry, str) for entry in entries):
                raise ValueError(f'manifest.{key} must contain strings')
        if self.provider == 'aws_iam':
            statements = self.manifest.get('Statement', [])
            statements = [statements] if isinstance(statements, dict) else statements
            if not isinstance(statements, list) or len(statements) > 100:
                raise ValueError('manifest.Statement must be an object or list of at most 100 objects')
            for statement in statements:
                if not isinstance(statement, dict) or statement.get('Effect') not in ('Allow', 'Deny'):
                    raise ValueError('IAM statements need an Allow or Deny Effect')
                actions = statement.get('Action', [])
                if not isinstance(actions, str) and (not isinstance(actions, list) or not all(isinstance(a, str) for a in actions)):
                    raise ValueError('IAM Action must be a string or string list')
        return self

class SimulationInput(BaseModel):
    agent: AgentInput
    remove_permission: str

class ExplanationInput(BaseModel):
    agent: AgentInput
    analysis: dict[str, Any]
