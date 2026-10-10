"""Developer policy, independent of model text. Delegation can only narrow access."""
from pydantic import BaseModel, Field, ConfigDict, model_validator
from pathlib import PurePosixPath
from app.runtime.resource_classifier import in_scope

class IntentLock(BaseModel):
    model_config = ConfigDict(extra='forbid')
    job: str = Field(min_length=1, max_length=500)
    tools: list[str] = Field(default_factory=lambda: ['read_file'], max_length=10)
    resources: list[str] = Field(default_factory=list, max_length=30)
    forbidden: list[str] = Field(default_factory=list, max_length=30)
    approval_tools: list[str] = Field(default_factory=list, max_length=10)
    warn_tools: list[str] = Field(default_factory=list, max_length=10)
    delegates: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode='after')
    def bounded_rules(self):
        for values in (self.tools, self.resources, self.forbidden, self.approval_tools, self.warn_tools, self.delegates):
            if any(not value or len(value) > 300 for value in values):
                raise ValueError('Policy entries must contain 1–300 characters')
        for path in self.resources + self.forbidden:
            if '\\' in path or '..' in PurePosixPath(path).parts or '?' in path or ('*' in path and not path.endswith('/**')):
                raise ValueError('Use exact resource paths or trailing /** without traversal')
        return self

    def check(self, tool: str, target: str) -> tuple[str, str]:
        if tool not in self.tools:
            return 'BLOCK', 'Intent Lock: tool is not granted.'
        if tool in self.forbidden or in_scope(target, tuple(self.forbidden)):
            return 'BLOCK', 'Intent Lock: action or resource is forbidden.'
        if not in_scope(target, tuple(self.resources)):
            return 'BLOCK', 'Intent Lock: resource is outside the job boundary.'
        if tool in self.approval_tools:
            return 'ASK', 'Intent Lock: explicit human approval is required.'
        if tool in self.warn_tools:
            return 'WARN', 'Intent Lock: permitted action requires an audit warning.'
        return 'ALLOW', 'Intent Lock: tool and resource are granted for this job.'

    def delegate(self, name: str, child: 'IntentLock') -> 'IntentLock':
        if name not in self.delegates:
            raise ValueError('Agent is not an authorized delegate')
        if not set(child.tools) <= set(self.tools):
            raise ValueError('Delegate cannot gain tools')
        for resource in child.resources:
            if not in_scope(resource, tuple(self.resources)):
                raise ValueError('Delegate cannot gain resources')
        # Inherited restrictions cannot be relaxed, including at further delegation.
        return child.model_copy(update={
            'forbidden': list(set(self.forbidden + child.forbidden)),
            'approval_tools': list(set(self.approval_tools + child.approval_tools)),
            'warn_tools': list(set(self.warn_tools + child.warn_tools)),
            'delegates': [n for n in child.delegates if n in self.delegates],
        })
