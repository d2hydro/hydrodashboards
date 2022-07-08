def concat_fews_parameter_ids(parameter_id, qualifier_ids=None):
    if qualifier_ids is None:
        return parameter_id
    else:
        return f"{parameter_id} * {'*'.join(qualifier_ids)}"


def concat_fews_parameter_names(parameter_name, qualifier_names=None):
    if qualifier_names is None:
        return parameter_name
    else:
        return f"{parameter_name} {' '.join(qualifier_names)}"


def split_parameter_id_to_fews(parameter_id):
    components = parameter_id.split("*")
    fews_parameter_id = components[0].strip()
    if len(components) > 1:
        fews_qualifier_ids = [i.strip() for i in components[1:]]
    else:
        fews_qualifier_ids = [""]
    return fews_parameter_id, fews_qualifier_ids
