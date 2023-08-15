import argparse

import apypie
import jinja2
import yaml

EXPECTED_TYPE_MAP = {
    'array': 'list',
    'hash': 'dict',
    'numeric': 'int',
    'boolean': 'bool',
    'string': 'str',
}

SKIP_PARAMS = (
    'location_id',
    'organization_id',
    'location_ids',
    'organization_ids',
)

SKIP_PARAMS_INFO = (
    'location_id',
    'organization_id',
    'search',
    'order',
    'page',
    'per_page',
)

def map_expected_type(expected):
    return EXPECTED_TYPE_MAP.get(expected, 'str')

def resource_capitalized(resource):
    return "".join([r.capitalize() for r in resource.split('_')])

def resource_module_name(resource, prefix='Foreman', suffix='Module'):
    capitalized_resource = resource_capitalized(resource)
    return f"{prefix}{capitalized_resource}{suffix}"

def info_module_name(resource, prefix='Foreman'):
    return resource_module_name(resource, prefix, 'Info')

def process_param(param, skip_list):
    if param.params:
        for p in param.params:
            yield from process_param(p, skip_list)
    elif not param.name in skip_list:
        if param.name.endswith('_id'):
            param_type = 'entity'
            param_doc_type = 'str'
            param_name = param.name.removesuffix('_id')
        elif param.name.endswith('_ids'):
            param_type = 'entity_list'
            param_doc_type = 'list'
            param_name = param.name.removesuffix('_ids')
        else:
            param_type = map_expected_type(param.expected_type)
            param_doc_type = param_type
            param_name = param.name
        python = f"{param_name}=dict(required={param.required}, type='{param_type}'),"
        doc = {param_name: {'description': [param.description.strip()], 'type': param_doc_type, 'required': param.required}}
        yield (python,doc)

def process_params(resource, server, module_type='resource'):
    if module_type == 'resource':
        action = 'create'
        skip_list = SKIP_PARAMS
    elif module_type == 'info':
        action = 'index'
        skip_list = SKIP_PARAMS_INFO
    else:
        raise Exception(f"unknown {module_type}")
    api = apypie.Api(uri=server, verify_ssl=False, api_version=2)
    for p in api.resource(resource).action(action).params:
        yield from process_param(p, skip_list)

def main():
    parser = argparse.ArgumentParser(prog='apinsible')
    parser.add_argument('resource')
    parser.add_argument('--server', default='http://localhost:3000')
    parser.add_argument('--type', default='resource', choices=['resource', 'info'])
    args = parser.parse_args()

    resource = args.resource
    if args.type == 'info':
        base_class = 'ForemanInfoAnsibleModule'
        module_name = info_module_name(resource)
    else:
        base_class = 'ForemanTaxonomicEntityAnsibleModule'
        module_name = resource_module_name(resource)

    inflector = apypie.inflector.Inflector()
    resource_pluralized = inflector.pluralize(resource)

    options = process_params(resource_pluralized, args.server, args.type)
    code = []
    docs = {}
    for (python,doc) in options:
        code.append(python)
        docs.update(doc)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
    template = env.get_template("module.py.j2")
    context = {
        'resource': resource,
        'resource_capitalized': resource_capitalized(resource),
        'resource_pluralized': resource_pluralized,
        'code': code,
        'docs': yaml.dump(docs, default_flow_style=False),
        'module_name': module_name,
        'base_class': base_class,
        'module_type': args.type,
    }
    print(template.render(context))


if __name__ == '__main__':
    main()
