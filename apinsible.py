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

def map_expected_type(expected):
    return EXPECTED_TYPE_MAP.get(expected, 'str')

def resource_capitalized(resource):
    return "".join([r.capitalize() for r in resource.split('_')])

def module_name(resource, prefix='Foreman', suffix='Module'):
    capitalized_resource = resource_capitalized(resource)
    return f"{prefix}{capitalized_resource}{suffix}"

def process_param(param):
    if param.params:
        for p in param.params:
            yield from process_param(p)
    elif not param.name in SKIP_PARAMS:
        if param.name.endswith('_id'):
            param_type = 'entity'
            param_name = param.name.removesuffix('_id')
        elif param.name.endswith('_ids'):
            param_type = 'entity_list'
            param_name = param.name.removesuffix('_ids')
        else:
            param_type = map_expected_type(param.expected_type)
            param_name = param.name
        python = f"{param_name}=dict(required={param.required}, type='{param_type}'),"
        doc = {param_name: {'description': [param.description.strip()], 'type': param_type, 'required': param.required}}
        yield (python,doc)

def process_params(resource, server):
    api = apypie.Api(uri=server, verify_ssl=False, api_version=2)
    for p in api.resource(resource).action('create').params:
        yield from process_param(p)

def main():
    parser = argparse.ArgumentParser(prog='apinsible')
    parser.add_argument('resource')
    parser.add_argument('--server', default='http://localhost:3000')
    args = parser.parse_args()

    resource = args.resource

    inflector = apypie.inflector.Inflector()
    resource_pluralized = inflector.pluralize(resource)

    options = process_params(resource_pluralized, args.server)
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
        'module_name': module_name(resource),
    }
    print(template.render(context))


if __name__ == '__main__':
    main()
