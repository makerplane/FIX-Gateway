import yaml
import os


class MetadataLoader(yaml.SafeLoader):
    def __init__(self, stream, filename=None):
        super().__init__(stream)
        self.filename = filename
        self._metadata_store = {}

    def construct_mapping(self, node, deep=False):
        """Override the default mapping constructor to include metadata."""
        mapping = super().construct_mapping(node, deep=deep)
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if isinstance(key, str):
                self._metadata_store[key] = {
                    'line': key_node.start_mark.line + 1,
                    'column': key_node.start_mark.column + 1,
                    'filename': self.filename
                }
        return mapping

    def construct_scalar(self, node):
        """Override scalar constructor to include metadata."""
        value = super().construct_scalar(node)
        metadata = {
            'line': node.start_mark.line + 1,
            'column': node.start_mark.column + 1,
            'filename': self.filename
        }
        self._metadata_store[value] = metadata
        return value

# Function to parse YAML and extract data and metadata
def parse_yaml_with_metadata(yaml_string, filename=None):
    if isinstance(yaml_string, str):
        stream = yaml_string
    else:
        stream = yaml_string.read()

    loader = MetadataLoader(stream, filename=filename)
    data = loader.get_single_data()
    metadata = loader._metadata_store
    return data, metadata



def from_yaml(fs, bpath=None, cfg=None, bc=None, preferences=None, metadata=None):
    fname = None
    fpath = None
    if bc is None:
        bc = []
    bc.append(fname)
    if len(bc) > 500:
        import pprint

        raise Exception(
            f"{pprint.pformat(bc)}\nPotential loop detected inside yaml includes, the breadcrumbs above might help detect where the issue is"
        )
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
                fname = bpath + '/<unknown>'
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)
        else:
            # should be a stream
            if hasattr(fs, 'read'):
                fname = getattr(fs, 'name', '<unknown>')  # Use stream name if it exists
                fpath = os.path.dirname(fname)
                if not bpath:
                    bpath = fpath
                cfg, cfg_meta = parse_yaml_with_metadata(fs, fname)

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
                    sub = from_yaml(ifile, bpath, bc=bc, preferences=preferences)
                    if hasattr(sub, "items"):
                        for k, v in sub.items():
                            new[k] = v
                    else:
                        raise Exception(f"Include {val} from {fname} is invalid")
            elif isinstance(val, dict):
                new[key] = from_yaml(fname, bpath, val, bc=bc, preferences=preferences)
            elif isinstance(val, list):
                new[key] = []
                # Included array elements
                for l in val:
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
                            with open(ifile) as cf:
                                litems = yaml.safe_load(cf)
                            if "items" in litems:
                                if litems["items"] != None:
                                    for a in litems["items"]:
                                        new[key].append(a)
                            else:
                                raise Exception(
                                    f"Error in {ifile}\nWhen including list items they need listed under 'items:' in the include file"
                                )
                        else:
                            new[key].append(l)
                    else:
                        new[key].append(l)
            else:
                # Save existing
                new[key] = val
    if metadata:
        return (new, new_meta)
    else:
        return new
