import json
import os
import urllib.request
from app.models import AgentInput

def fallback(analysis: dict) -> dict:
    risks = analysis.get('risks', [])
    if not risks:
        return {'summary': 'No configured risk chain was detected.', 'why_it_matters': 'Review unknown permissions and provider-specific semantics separately.',
                'purpose_alignment': 'Check the permission alignment list against the agent purpose.',
                'recommendation': 'Keep only the permissions needed for the core task.', 'source': 'deterministic-template'}
    top = risks[0]
    return {'summary': f"{top['name']} is possible with the current permissions.",
            'why_it_matters': f"The combination of {', '.join(top['required_capabilities'])} creates this path.",
            'purpose_alignment': 'Review whether each permission is needed for the stated purpose.',
            'recommendation': f"Consider removing {analysis.get('recommendations', [{}])[0].get('permission', top['path'][-2])} and simulate the result.",
            'source': 'deterministic-template'}

def explain(agent: AgentInput, analysis: dict) -> dict:
    result = fallback(analysis)
    if os.getenv('AI_ENABLED', 'false').lower() != 'true':
        return result
    provider = os.getenv('AI_PROVIDER', '').lower()
    prompt = json.dumps({'purpose': agent.purpose, 'permissions': agent.permissions,
                         'capabilities': analysis.get('capabilities', []), 'risks': analysis.get('risks', []),
                         'instruction': 'Explain only the supplied deterministic findings. Return JSON with summary, why_it_matters, purpose_alignment, recommendation. Do not invent capabilities or severity.'})
    try:
        if provider == 'openai' and os.getenv('OPENAI_API_KEY'):
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {'Authorization': f"Bearer {os.environ['OPENAI_API_KEY']}"}
            payload = {'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'), 'messages': [{'role': 'user', 'content': prompt}], 'response_format': {'type': 'json_object'}}
            extract = lambda data: json.loads(data['choices'][0]['message']['content'])
        elif provider == 'gemini' and os.getenv('GEMINI_API_KEY'):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}:generateContent?key={os.environ['GEMINI_API_KEY']}"
            headers = {}
            payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json'}}
            extract = lambda data: json.loads(data['candidates'][0]['content']['parts'][0]['text'])
        else:
            return result
        request = urllib.request.Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json', **headers})
        with urllib.request.urlopen(request, timeout=6) as response:
            parsed = extract(json.load(response))
        if all(isinstance(parsed.get(k), str) for k in ('summary', 'why_it_matters', 'purpose_alignment', 'recommendation')):
            return {k: parsed[k] for k in ('summary', 'why_it_matters', 'purpose_alignment', 'recommendation')} | {'source': provider}
    except Exception:
        pass
    return result
