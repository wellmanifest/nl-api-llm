import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).parent))
from nl_api_llm import ApiRegistry, ApiEndpoint, ApiParameter, RestSpec
from semantic_adapter import api_contracts, translate, compile_api


def registry():
    return ApiRegistry('api-registry/v1', '1', [], [ApiEndpoint('inspect', 'media', 'rest', 'Inspect a file', rest=RestSpec('GET', '/files/{name}'), parameters=[ApiParameter('name', 'string', 'path'), ApiParameter('limit', 'integer', 'query', required=False)])])


def test_unicode_and_no_implicit_effects():
    r = registry()
    assert api_contracts(r, {}) == []
    planner = Mock()
    translate(r, 'Ποιο αρχείο; zażółć.svg', planner, {'inspect': ['read']})
    assert planner.translate.call_args.args[0] == 'Ποιο αρχείο; zażółć.svg'
    c = planner.translate.call_args.args[1][0]
    assert c['input_schema']['required'] == ['name']
    assert c['uri'] == 'api://media/inspect/v1'


def test_duplicate_parameters_rejected():
    r = registry(); r.endpoints[0].parameters.append(ApiParameter('name', 'string', 'query'))
    with pytest.raises(ValueError): api_contracts(r, {'inspect': ['read']})


def test_compile_and_fresh_contract():
    runtime = pytest.importorskip("dockuri_nl", reason="Optional shared-runtime integration requires Dockuri 0.5.1")
    from dockuri_nl import eligible_contracts, PROFILE, PlanError
    r = registry(); effects = {'inspect': ['read']}
    c = eligible_contracts(api_contracts(r, effects), ['read'])[0]
    plan = {'schema': PROFILE, 'status': 'ok', 'plan': {'kind': 'call', 'operation': c['uri'], 'arguments': {'name': 'zażółć/$(touch x).svg', 'limit': 3}, 'digest': c['contract_digest']}}
    result = compile_api(r, plan, effects, ['read'])
    assert not result['executed']
    assert result['calls'][0]['request']['path'] == '/files/za%C5%BC%C3%B3%C5%82%C4%87%2F%24%28touch%20x%29.svg'
    assert result['calls'][0]['request']['query'] == {'limit': 3}
    r.endpoints[0].rest.path = '/new/{name}'
    with pytest.raises(PlanError): compile_api(r, plan, effects, ['read'])


def test_clarification_has_no_driver_calls():
    pytest.importorskip("dockuri_nl", reason="Optional shared-runtime integration requires Dockuri 0.5.1")
    from dockuri_nl import PROFILE
    result = compile_api(registry(), {'schema': PROFILE, 'status': 'clarify', 'question': 'Which file?'}, {'inspect': ['read']}, ['read'])
    assert result['calls'] == [] and not result['executed']
