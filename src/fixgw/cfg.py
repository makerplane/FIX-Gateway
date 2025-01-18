import yaml
from yaml.loader import SafeLoader
from io import StringIO
import os
import logging

log = logging.getLogger("cfg")


class MetadataLoader(SafeLoader):
    def __init__(self, stream, filename=None, *args, **kwargs):
        super().__init__(stream, *args, **kwargs)
        self.metadata = {}
        self.filename = filename

    def construct_mapping(self, node, deep=False):
        mapping = {}
        metadata_mapping = {}
        if isinstance(node, yaml.MappingNode):
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=True)
                value = self.construct_object(value_node, deep=True)

                # Store metadata for the key
                key_meta = {
                    "line": key_node.start_mark.line + 1,
                    "column": key_node.start_mark.column + 1,
                    "file": self.filename,
                }

                # Store metadata for the value
                value_meta = {
                    "line": value_node.start_mark.line + 1,
                    "column": value_node.start_mark.column + 1,
                    "file": self.filename,
                }

                # Ensure nested metadata structure
                metadata_mapping[f".__{key}__."] = key_meta
                metadata_mapping[f".__{key}__."]["value_meta"] = value_meta

                if isinstance(value_node, yaml.MappingNode):
                    # Recurse into nested structures
                    nested_mapping, nested_metadata = (
                        self.construct_mapping_with_metadata(value_node)
                    )
                    mapping[key] = nested_mapping
                    metadata_mapping[key] = nested_metadata
                elif isinstance(value_node, yaml.SequenceNode):
                    # Handle lists explicitly
                    list_values = []
                    list_metadata = {}
                    for index, item_node in enumerate(value_node.value):
                        item_value = self.construct_object(item_node, deep=True)
                        list_values.append(item_value)

                        # Derive metadata for list items
                        item_meta = {
                            "line": item_node.start_mark.line + 1,
                            "column": item_node.start_mark.column + 1,
                            "file": self.filename,
                        }

                        if isinstance(item_node, yaml.MappingNode):
                            nested_mapping, nested_metadata = (
                                self.construct_mapping_with_metadata(item_node)
                            )
                            list_metadata[index] = nested_metadata
                            list_metadata[f".__{index}__."] = item_meta
                        else:
                            list_metadata[index] = {
                                **item_meta,
                                "value_meta": item_meta,
                            }
                    mapping[key] = list_values
                    metadata_mapping[key] = list_metadata
                else:
                    mapping[key] = value
        self.metadata.update(metadata_mapping)
        return mapping

    def construct_mapping_with_metadata(self, node):
        previous_metadata = self.metadata
        self.metadata = {}
        mapping = self.construct_mapping(node, deep=True)
        metadata = self.metadata
        self.metadata = previous_metadata
        return mapping, metadata

    def construct_yaml_map(self, node):
        data = super().construct_yaml_map(node)
        data.update(self.construct_mapping(node))
        return data

    def get_data(self):
        return self.construct_document(self.get_single_node())

    def get_metadata(self):
        return self.metadata


# Function to parse YAML and extract data and metadata
def parse_yaml_with_metadata(yaml_string, filename=None):
    if isinstance(yaml_string, str):
        stream = yaml_string
    else:
        stream = yaml_string.read()

    loader = MetadataLoader(stream, filename=filename)
    data = loader.get_data()
    metadata = loader.get_metadata()

    return data, metadata


def from_yaml(
    fs, bpath=None, cfg=None, cfg_meta=None, bc=None, preferences=None, metadata=None
):
    if not cfg:
        if isinstance(fs, str):
            # Must be a string of yaml or a filename
            if os.path.isfile(fs):
                # It is a filename
                fname = fs
                fpath = os.path.dirname(fname)
                if not bpath:
                    bpath = fpath
                with open(fs) as cf:
                    cfg, cfg_meta = parse_yaml_with_metadata(cf, fname)
            else:
                # Must be a yaml string
                if not bpath:
                    bpath = os.getcwd()
                fpath = bpath
                fname = bpath + "/<unknown>"
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)
        else:
            # should be a stream
            if hasattr(fs, "read"):
                fname = getattr(fs, "name", "<unknown>")  # Use stream name if it exists
                fpath = os.path.dirname(fname)
                if not bpath:
                    bpath = fpath
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)

    if isinstance(fs, str):
        fname = fs
        fpath = os.path.dirname(fname)

    if bc is None:
        bc = []
    bc.append(fname)
    if len(bc) > 500:
        import pprint

        raise Exception(
            f"{pprint.pformat(bc)}\nPotential loop detected inside yaml includes, the breadcrumbs above might help detect where the issue is"
        )

    new_meta = {}
    new = {}
    if hasattr(cfg, "items"):
        for key, val in cfg.items():
            if key == "include":
                if isinstance(val, str):
                    files = [val]
                elif isinstance(val, list):
                    files = val
                else:
                    raise Exception(f"#include in {fname} must be string or array")
                # Process include(s)
                for f in files:
                    log.debug(f"checking include file '{f}' from key:{key}")
                    # Check if file relative to current file
                    ifile = fpath + "/" + f
                    if not os.path.exists(ifile):
                        # Use base path
                        ifile = bpath + "/" + f
                    if not os.path.exists(ifile):
                        # Check preferences
                        if "includes" in preferences:
                            pfile = preferences["includes"].get(f, False)
                            if pfile:
                                ifile = fpath + "/" + pfile
                                if not os.path.exists(ifile):
                                    ifile = bpath + "/" + pfile
                                    if not os.path.exists(ifile):
                                        raise Exception(f"Cannot find include: {f}")
                        else:
                            raise Exception(f"Cannot find include: {f}")
                    sub, sub_meta = from_yaml(
                        ifile, bpath, bc=bc, preferences=preferences, metadata=True
                    )
                    if hasattr(sub, "items"):
                        for k, v in sub.items():
                            new[k] = v
                    else:
                        raise Exception(f"Include {val} from {fname} is invalid")
            elif isinstance(val, dict):
                new[key], new_meta[key] = from_yaml(
                    fs=fname,
                    bpath=bpath,
                    cfg=val,
                    cfg_meta=cfg_meta,
                    bc=bc,
                    preferences=preferences,
                    metadata=True,
                )
            elif isinstance(val, list):
                new[key] = []
                new_meta[key] = {}
                # Included array elements
                for lindex, l in enumerate(val):
                    if isinstance(l, dict):
                        if "include" in l:
                            ifile = fpath + "/" + l["include"]
                            if not os.path.exists(ifile):
                                # Use base path
                                ifile = bpath + "/" + l["include"]
                            if not os.path.exists(ifile):
                                # Check preferences
                                if "includes" in preferences:
                                    pfile = preferences["includes"].get(
                                        l["include"], False
                                    )
                                    if pfile:
                                        ifile = fpath + "/" + pfile
                                        if not os.path.exists(ifile):
                                            ifile = bpath + "/" + pfile
                                            if not os.path.exists(ifile):
                                                raise Exception(
                                                    f"Cannot find include: {f}"
                                                )
                                else:
                                    raise Exception(f"Cannot find include: {f}")
                            # Need to update this for metadata
                            with open(ifile) as cf:
                                litems, cfg_litems = parse_yaml_with_metadata(cf, ifile)
                            if "items" in litems:
                                if litems["items"] != None:
                                    for ax, a in enumerate(litems["items"]):
                                        new[key].append(a)
                                        new_meta[key] = cfg_litems["items"][ax]
                                        new_meta[f".__{key}__."] = cfg_litems["items"][
                                            ax
                                        ]
                            else:
                                raise Exception(
                                    f"Error in {ifile}\nWhen including list items they need listed under 'items:' in the include file"
                                )
                        else:
                            new[key].append(l)
                            new_meta[key][lindex] = cfg_meta[key][lindex]
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key][
                                f".__{lindex}__."
                            ]
                    else:
                        new[key].append(l)
                        if lindex in cfg_meta[key]:
                            new_meta[key][lindex] = cfg_meta[key][lindex]
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key][lindex]
                        elif f".__{lindex}__." in cfg_meta[key]:
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key][
                                f".__{lindex}__."
                            ]
                        else:
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key]

            else:
                # Save existing
                new[key] = val
                new_meta[key] = cfg_meta[f".__{key}__."]
    if metadata:
        return (new, new_meta)
    else:
        return new


def message(message, key, index, value=None):
    if value:
        if f".__{index}__." in key:
            return f'{message} on line {key[f".__{index}__."]["value_meta"]["line"]}, column {key[f".__{index}__."]["value_meta"]["column"]} in file \'{key[f".__{index}__."]["value_meta"]["file"]}\''
        else:
            return f'{message} on line {key[index]["value_meta"]["line"]}, column {key[index]["value_meta"]["column"]} in file \'{key[index]["value_meta"]["file"]}\''
    else:
        if f".__{index}__." in key:
            return f'{message} on line {key[f".__{index}__."]["line"]}, column {key[f".__{index}__."]["column"]} in file \'{key[f".__{index}__."]["file"]}\''
        else:
            return f'{message} on line {key[index]["line"]}, column {key[index]["column"]} in file \'{key[index]["file"]}\''
