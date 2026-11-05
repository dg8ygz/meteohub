"""Compare plugin payloads with native raw records without losing decimal units."""
def raw_tenths(value):
 digits=value.lstrip('-')
 return int(value) if len(digits)>1 and digits.startswith('0') else 10*int(value)

def normalize_record(line,raw=False):
 parts=line.split();name=parts[1] if raw else parts[0];values=parts[2:] if raw else parts[1:]
 if name.startswith('wind'):v=[int(values[0])%360,int(values[1]),int(values[2])]
 elif name.startswith('rain'):v=[raw_tenths(values[0]),int(values[2])] if raw else [int(x) for x in values[:2]]
 elif name.startswith('uv'):v=[raw_tenths(values[0]) if raw else int(values[0])]
 elif name.startswith('sol'):v=[int(values[0])]
 else:v=[int(x) for x in values]
 return (name,*v)
