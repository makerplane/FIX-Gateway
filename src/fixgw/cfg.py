import yaml
from yaml.loader import SafeLoader
import os
import logging
import re

log = logging.getLogger("cfg")


class MetadataLoader(SafeLoader):
    def __init__(self, stream, filename=None, *args, **kwargs):
        super().__init__(stream, *args, **kwargs)
        self.metadata = {}
        self.filename = filename

    def construct_mapping(self, node, deep=False):
        mapping = {}
        metadata_mapping = {}
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

#    def construct_yaml_map(self, node):
#        data = super().construct_yaml_map(node)
#        data.update(self.construct_mapping(node))
#        return data

    def get_data(self):
        try:
            return self.construct_document(self.get_single_node())
        except:
            return {}
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
    fs, bpath=None, fname=None, cfg=None, cfg_meta=None, bc=None, bcsource=None, preferences=None, metadata=None
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

                if bc is None:
                    bc = []
                if bcsource is None:
                    bcsource='was the first file to load'

                bc.append((fname, bcsource))
                bccount = sum(1 for t in bc if t[0] == fname)
                if bccount > 2 or len(bc) > 500:
                    output = "Include loop detected, Breadcrumbs:\n"
                    bold_start = "==>"
                    bold_end = "<=="
                    count = 0
                    prevcount = 0
                    for cindex,crumb in enumerate(bc):
                        filename=crumb[0]
                        cmessage=crumb[1]
                        if filename == fname:
                            filename = f"{bold_start}{crumb[0]}{bold_end}"
                            count += 1
                        if count > prevcount:
                            prevcount = count
                            if count > 1:
                                cmessage = re.sub(
                                    r"'(.*?)'",
                                    rf"'{bold_start}\1{bold_end}'",
                                    cmessage
                                )
                        output = output + f"{cindex:3} {filename} {cmessage}\n"
                    raise ValueError(output)

            else:
                # Must be a yaml string
                if bpath is None:
                    bpath = os.getcwd()
                fpath = bpath
                if fname is None:
                    fname = bpath + "/<unknown>"
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)
        else:
            # should be a stream
            if hasattr(fs, "read"):  # pragma: no cover
                fname = getattr(fs, "name", "<unknown>")  # Use stream name if it exists
                fpath = os.path.dirname(fname)
                if not bpath:
                    bpath = fpath
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)
    else:
        #when cfg is set fs is always a filename, or at least should be
        fname = fs
        fpath = os.path.dirname(fname)

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
                    raise ValueError(message(f"include in {fname} must be string or array",cfg_meta,key,True))
                # Process include(s)
                for findex, f in enumerate(files):
                    log.debug(f"checking include file '{f}' from key:{key}")
                    # Check if file relative to current file
                    ifile = fpath + "/" + f
                    bcsource = message(f"was referenced",cfg_meta,key,True)
                    if not os.path.exists(ifile):
                        log.debug(f"checking include file '{f}' from key:{key} not found at '{ifile}'")
                        # Use base path
                        ifile = bpath + "/" + f
                    if not os.path.exists(ifile):
                        log.debug(f"checking include file '{f}' from key:{key} not found at '{ifile}'")
                        # Check preferences
                        print(preferences)
                        if preferences is not None and "includes" in preferences:
                            log.debug(f"checking include file '{f}' from key:{key} checking preferences")
                            pfile = preferences["includes"].get(f, False)
                            if pfile is not False:
                                ifile = fpath + "/" + pfile
                                if not os.path.exists(ifile):
                                    ifile = bpath + "/" + pfile
                                    if not os.path.exists(ifile):
                                        if isinstance(val, str):
                                            raise ValueError(message(f"Cannot find include: '{pfile}' from preferences '{val}'",cfg_meta, key, True))
                                        else:
                                            raise ValueError(message(f"Cannot find include: '{pfile}' from preferences '{val[findex]}'",cfg_meta['include'], findex, True))
                                    else:
                                        if not isinstance(val, str):
                                            # May never get here
                                            bcsource = message(f"was referenced",cfg_meta['include'],findex,True)
                        else:
                            if isinstance(val, str):
                                raise ValueError(message(f"Cannot find include: '{f}'", cfg_meta, key, True))
                            else:
                                raise ValueError(message(f"Cannot find include: '{f}'", cfg_meta['include'], findex , True))
                    sub, sub_meta = from_yaml(
                        ifile, bpath, bc=bc, bcsource=bcsource, preferences=preferences, metadata=True
                    )
                    if hasattr(sub, "items"):
                        log.debug(f"Processing items from file '{ifile}' from key:{key}")
                        for k, v in sub.items():
                            new[k] = v
                            new_meta[k] = sub_meta[k]
                            if f".__{k}__." in sub_meta:
                                new_meta[f".__{k}__."] = sub_meta[f".__{k}__."]
                    else:
                        raise Exception(f"Include {val} from {fname} is invalid")
            elif isinstance(val, dict):
                # Here we feed the dict into from_yaml
                # to process any includes that might be in the dict
                
                log.debug(f"Process include with from_yaml, key:{key} val:{val}")
                new_meta[f".__{key}__."] = cfg_meta[f".__{key}__."]
                new[key], new_meta[key] = from_yaml(
                    fs=fname,
                    bpath=bpath,
                    cfg=val,
                    cfg_meta=cfg_meta[key],
                    bc=bc,
                    preferences=preferences,
                    metadata=True,
                )
                #print(new_meta[key])
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
                                if preferences is not None and "includes" in preferences:
                                    pfile = preferences["includes"].get(
                                        l["include"], False
                                    )
                                    if pfile:
                                        ifile = fpath + "/" + pfile
                                        if not os.path.exists(ifile):
                                            ifile = bpath + "/" + pfile
                                            if not os.path.exists(ifile):
                                                raise Exception(
                                                    f"Cannot find include: {f}" #TODO
                                                )
                                else:
                                    raise ValueError(message(f"Cannot find include: '{l['include']}'", cfg_meta, 'include', True )) # TODO
                            # Need to update this for metadata
                            with open(ifile) as cf:
                                litems, cfg_litems = parse_yaml_with_metadata(cf, ifile)
                            if "items" in litems:
                                if litems["items"] is not None:
                                    for ax, a in enumerate(litems["items"]):
                                        new[key].append(a)
                                        new_meta[key] = cfg_litems["items"][ax]
                                        new_meta[f".__{key}__."] = cfg_litems["items"][
                                            ax
                                        ]
                            else:
                                raise Exception(
                                    f"Error in {ifile}\nWhen including list items they need listed under 'items:' in the include file" # TODO
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
                            # This might always happen and nver get to the lse below
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key][
                                f".__{lindex}__."
                            ]
                        else:
                            new_meta[key][f".__{lindex}__."] = cfg_meta[key]

            else:
                # Save existing
                new[key] = val
                new_meta[key] = cfg_meta[f".__{key}__."]
    if metadata is True:
        print("meta")
        return (new, new_meta)
    else:
        print("no meta")
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
            # It is possible this never happens
            return f'{message} on line {key[index]["line"]}, column {key[index]["column"]} in file \'{key[index]["file"]}\''
