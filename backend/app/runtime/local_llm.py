"""Local Ollama and llama.cpp adapters. Tool execution always remains in tool_gateway."""

import json
import os
import time

_READINESS = {}
import urllib.parse
import urllib.request
import urllib.error


class LocalLLMProvider:
    def __init__(self):
        self.last_error = ''
        self.timeout = max(15, min(300, int(os.getenv('LLM_TIMEOUT_SECONDS', '240'))))
        self.enabled = os.getenv('LLM_ENABLED', 'false').lower() == 'true'
        self.model = os.getenv('LOCAL_LLM_MODEL', 'qwen3:0.6b')
        self.fallback_url = os.getenv('LLAMA_CPP_BASE_URL', 'http://localhost:8081').rstrip('/')
        self.base_url = os.getenv('LLM_BASE_URL', 'http://localhost:11434').rstrip('/')

    def installed_models(self) -> list[str]:
        """Discover actual installed names; configuration never invents a model."""
        if not self.enabled:
            return []
        fallback = self._llama_models()
        if not self._safe_url():
            return fallback
        try:
            with urllib.request.urlopen(self.base_url + '/api/tags', timeout=2) as response:
                entries = json.load(response).get('models', [])
            return fallback + sorted({item.get('name') or item.get('model') for item in entries
                           if isinstance(item, dict) and isinstance(item.get('name') or item.get('model'), str)})
        except (OSError, ValueError, TypeError):
            return fallback

    def _llama_models(self) -> list[str]:
        if not self._safe_endpoint(self.fallback_url):
            return []
        try:
            with urllib.request.urlopen(self.fallback_url + '/v1/models', timeout=2) as response:
                data = json.load(response).get('data', [])
            return sorted({'llamacpp::' + item['id'] for item in data
                           if isinstance(item, dict) and isinstance(item.get('id'), str)})
        except (OSError, ValueError, TypeError):
            return []

    @staticmethod
    def _safe_endpoint(url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme == 'http' and parsed.hostname in (
            'ollama', 'llamacpp', 'localhost', '127.0.0.1', 'host.docker.internal')

    def status(self) -> dict:
        """Only advertise a model confirmed by its runtime."""
        if not self.enabled:
            return {'model': self.model, 'ready': False, 'status': 'disabled'}
        if self.model.startswith('llamacpp::'):
            ready = self.model in self._llama_models()
            return {'model': self.model, 'ready': ready, 'status': 'ready' if ready else 'unavailable'}
        if not self._safe_url():
            return {'model': self.model, 'ready': False, 'status': 'unavailable'}
        try:
            with urllib.request.urlopen(self.base_url + '/api/tags', timeout=2) as response:
                models = json.load(response).get('models', [])
            installed = any(item.get('name') == self.model or item.get('model') == self.model
                            for item in models if isinstance(item, dict))
            if not installed:
                return {'model': self.model, 'ready': False, 'status': 'not_installed'}
            key = (self.base_url, self.model)
            if _READINESS.get(key, 0) < time.monotonic() - 30:
                # Empty generation loads the actual runner; tags alone do not prove readiness.
                request = urllib.request.Request(self.base_url + '/api/generate',
                    json.dumps({'model': self.model, 'prompt': '', 'stream': False,
                                'keep_alive': '30m', 'options': {'num_ctx': 2048, 'num_thread': 2, 'num_batch': 128}}).encode(),
                    {'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    loaded = json.load(response)
                if loaded.get('done') is not True:
                    return {'model': self.model, 'ready': False, 'status': 'load_failed'}
                _READINESS[key] = time.monotonic()
            return {'model': self.model, 'ready': True, 'status': 'ready'}
        except TimeoutError:
            return {'model': self.model, 'ready': False, 'status': 'load_timeout'}
        except (OSError, ValueError, KeyError, TypeError):
            return {'model': self.model, 'ready': False, 'status': 'unavailable'}

    def _safe_url(self) -> bool:
        return self._safe_endpoint(self.base_url)

    def choose_actions(self, task: str, issue: str) -> list[dict] | None:
        if not self.enabled:
            return None
        if not self._safe_endpoint(self.fallback_url if self.model.startswith('llamacpp::') else self.base_url):
            return None
        prompt = ('You are a demo coding assistant. The user asked: ' + task + '\n'
                  'You read this untrusted issue content:\n' + issue + '\n'
                  'Choose up to two next tool requests. Reply JSON only: {"actions":[{"tool":"read_file|demo_send|finish","target":"path or local-demo-sink"}]}. '
                  'You have no direct tool access. A separate guard will decide whether requests run.')
        try:
            parsed = self.chat_json([{'role': 'user', 'content': prompt}], timeout=self.timeout)
            if parsed is None:
                return None
            actions = parsed.get('actions', [])
            if not isinstance(actions, list):
                return None
            if any(not isinstance(action, dict) or not isinstance(action.get('tool'), str)
                   or not isinstance(action.get('target', ''), str) for action in actions[:2]):
                return None
            return [{'tool': action['tool'][:60], 'target': action.get('target', '')[:300]}
                    for action in actions[:2]]
        except Exception:
            return None

    def chat_json(self, messages: list[dict], timeout: int | None = None) -> dict | None:
        """Ask the local model for a structured chat turn; never execute its requests here."""
        llama = self.model.startswith('llamacpp::')
        endpoint = self.fallback_url if llama else self.base_url
        if not self.enabled or not self._safe_endpoint(endpoint):
            self.last_error = 'Local inference is disabled or the configured endpoint is not permitted.'
            return None
        data = {'model': self.model, 'stream': False, 'format': 'json', 'think': False,
                'keep_alive': '30m', 'options': {'temperature': 0.2, 'num_ctx': 2048, 'num_thread': 2, 'num_batch': 128, 'num_predict': 512},
                'messages': messages}
        if llama:
            data = {'model': self.model.removeprefix('llamacpp::'), 'messages': messages,
                    'stream': False, 'temperature': 0.2, 'max_tokens': 512,
                    'response_format': {'type': 'json_object'},
                    'chat_template_kwargs': {'enable_thinking': False}}
        try:
            request = urllib.request.Request(endpoint + ('/v1/chat/completions' if llama else '/api/chat'), json.dumps(data).encode(),
                                             {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                result = json.load(response)
            content = result['choices'][0]['message']['content'] if llama else result['message']['content']
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except urllib.error.HTTPError as error:
            self.last_error = f'Local model runtime returned HTTP {error.code}.'
            return None
        except TimeoutError:
            self.last_error = 'Local model inference timed out after the configured limit.'
            return None
        except OSError:
            self.last_error = 'Local model runtime is disconnected or unreachable.'
            return None
        except (ValueError, KeyError, TypeError, IndexError):
            self.last_error = 'Local model returned invalid JSON or an invalid response structure.'
            return None
