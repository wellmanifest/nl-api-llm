"""Optional semantic-v1 adapter; interpretation belongs to the shared runtime."""
from dataclasses import asdict
from hashlib import sha256
import json
from urllib.parse import quote


def api_contracts(registry, effects):
    """Explicit host effects and typed parameters; no phrase patterns consulted."""
    result = []
    for endpoint in registry.endpoints:
        allowed = effects.get(endpoint.id)
        if not allowed:
            continue
        properties, required = {}, []
        for parameter in endpoint.parameters:
            if parameter.name in properties or parameter.type not in ('string', 'integer', 'number', 'boolean', 'array', 'object'):
                raise ValueError('Duplicate parameter or unsupported type')
            schema = {'type': parameter.type, 'description': parameter.description}
            if parameter.enum is not None:
                schema['enum'] = parameter.enum
            properties[parameter.name] = schema
            if parameter.required:
                required.append(parameter.name)
        public = asdict(endpoint)
        digest = sha256(json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result.append({'uri': 'api://' + quote(endpoint.service, safe='') + '/' + quote(endpoint.id, safe='') + '/v1',
                       'desc': endpoint.title + ': ' + endpoint.description, 'status': 'declared',
                       'input_schema': {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False},
                       'output_schema': {}, 'effects': list(allowed), 'digest': digest})
    return result


def translate(registry, text, planner, effects):
    """Inject the common planner; no vendor, weights or rules live in the standard."""
    return planner.translate(text, api_contracts(registry, effects))


def compile_api(registry, result, effects, allowed_effects):
    """Revalidate current contracts and compile inert driver records, never execute."""
    from dockuri_nl import compile_plan, eligible_contracts
    contracts = api_contracts(registry, effects)
    compiled = compile_plan(result, eligible_contracts(contracts, allowed_effects))
    endpoints = {c['uri']: e for c, e in zip(contracts, [e for e in registry.endpoints if effects.get(e.id)])}
    records = []
    for call in compiled['api']:
        endpoint = endpoints[call['uri']]
        record = dict(call, endpoint_id=endpoint.id, protocol=endpoint.protocol)
        if endpoint.protocol == 'rest':
            if endpoint.rest is None:
                raise ValueError('REST binding is required')
            path, query, body, headers = endpoint.rest.path, {}, {}, {}
            for parameter in endpoint.parameters:
                if parameter.name not in call['args']:
                    continue
                value = call['args'][parameter.name]
                if parameter.location == 'path':
                    marker = '{' + parameter.name + '}'
                    if marker not in path or type(value) not in (str, int):
                        raise ValueError('Invalid REST path binding')
                    path = path.replace(marker, quote(str(value), safe=''))
                elif parameter.location in ('query', 'body', 'header'):
                    {'query': query, 'body': body, 'header': headers}[parameter.location][parameter.name] = value
                else:
                    raise ValueError('Unsupported REST parameter location')
            if '{' in path or '}' in path:
                raise ValueError('Unresolved REST path binding')
            record['request'] = {'method': endpoint.rest.method, 'path': path, 'query': query, 'body': body, 'headers': headers}
        # CLI/gRPC/MCP/KVM records retain typed args for an authorized host driver.
        # commandTemplate and executable source are never evaluated here.
        records.append(record)
    return {'status': result['status'], 'calls': records, 'executed': False}
