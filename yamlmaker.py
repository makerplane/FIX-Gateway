
import yaml

f = open("fixgw/config/default.db")

variables = {}
state = "var"
entries = []

for line in f:
    sline = line.strip()
    if sline and sline[0] != '#':  # Skip blank lines and comments
        entry = sline.split(":")
        if entry[0][:3] == "---":
            state = "db"
            #print("Database Variables: " + str(variables))
            continue
        if state == "var":
            v = entry[0].split('=')
            variables[v[0].strip().lower()] = int(v[1].strip())
        if state == "db":
            #Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data
            x = sline.split(':')
            d = {}
            d["aa_key"] = x[0].strip()
            d["bb_description"] = x[1].strip()
            d["cc_type"] = x[2].strip()
            if d["cc_type"] == 'int':
                d["dd_min"] = int(x[3])
            elif d["cc_type"] == 'float':
                d["dd_min"] = float(x[3])
            if d["cc_type"] == 'int':
                d["ee_max"] = int(x[4])
            elif d["cc_type"] == 'float':
                d["ee_max"] = float(x[4])

            #d["ee_max"] = x[4].strip().replace("'","")
            if x[5].strip():
                d["ff_units"] = x[5].strip()
            if d["cc_type"] == 'int':
                d["gg_initial"] = int(x[6])
            elif d["cc_type"] == 'float':
                d["gg_initial"] = float(x[6])
            #d["gg_initial"] = x[6].strip().replace("'","")
            try:
                d["hh_tol"] = int(x[7].strip()) #.strip().replace("'","")
            except:
                pass
            if x[8].split(",") != ['']:
                d["ii_aux"] = x[8].split(",")
            entries.append(d)

f.close()

output = {}
output["variables"] = variables
output["entries"] = entries

yy = yaml.dump(output, default_flow_style=False)
yy = yy.replace('aa_', '')
yy = yy.replace('bb_', '')
yy = yy.replace('cc_', '')
yy = yy.replace('dd_', '')
yy = yy.replace('ee_', '')
yy = yy.replace('ff_', '')
yy = yy.replace('gg_', '')
yy = yy.replace('hh_', '')
yy = yy.replace('ii_', '')

print(yy)
