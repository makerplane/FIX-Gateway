rdac = {
# msg_id 1
'FF1PC': { 
  'description': 'Fuel flow 1 pulse count',
  'msg_id': 1,
  'bytes': [0,1],
  'type': 'word',
  'min': 0,
  'max': 65536,
  'error': 65536,
  'freq': 4000 },
'FF1PR': {
  'description': 'Fuel flow 1 pulse ratio',
  'msg_id': 1,
  'bytes': [2,3],
  'type': 'word',
  'scale': 0.1,
  'min': 0,
  'max': 1000,
  'error': 65536,
  'freq': 4000 },
'FF2PC': {
  'description': 'Fuel flow 2 pulse count',
  'msg_id': 1,
  'bytes': [4,5],
  'type': 'word',
  'min': 0,
  'max': 65536,
  'error': 65536,
  'freq': 4000},
'FF2PR': {
  'description': 'Fuel flow 2 pulse ratio',
  'msg_id': 1,
  'bytes': [6,7],
  'type': 'word',
  'min': 0,
  'max': 1000,
  'scale': 0.1,
  'error': 65536, 
  'freq': 4000},
# msg_id 2
'TC1': {
  'description': 'TC 1 deg C',
  'msg_id': 2,
  'bytes': [0,1],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC2': {
  'description': 'TC 2 deg C',
  'msg_id': 2,
  'bytes': [2,3],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC3': {
  'description': 'TC 3 deg C',
  'msg_id': 2,
  'bytes': [4,5],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC4': {
  'description': 'TC 4 deg C',
  'msg_id': 2,
  'bytes': [6,7],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
# msg_id 3
'TC5': {
  'description': 'TC 5 deg C',
  'msg_id': 3,
  'bytes': [0,1],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC6': {
  'description': 'TC 6 deg C',
  'msg_id': 3,
  'bytes': [2,3],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC7': {
  'description': 'TC 7 deg C',
  'msg_id': 3,
  'bytes': [4,5],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC8': {
  'description': 'TC 8 deg C',
  'msg_id': 3,
  'bytes': [6,7],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
# msg_id 4
'TC9': {
  'description': 'TC 9 deg C',
  'msg_id': 4,
  'bytes': [0,1],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC10': {
  'description': 'TC 10 deg C',
  'msg_id': 4,
  'bytes': [2,3],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC11': {
  'description': 'TC 11 deg C',
  'msg_id': 4,
  'bytes': [4,5],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
'TC12': {
  'description': 'TC 12 deg C',
  'msg_id': 4,
  'bytes': [6,7],
  'type': 'sint',
  'add': 'RDACTEMP',
  'freq': 500},
# msg_id 5
'OILT': {
  'description': 'Oil temp',
  'msg_id': 5,
  'bytes': [0,1],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
'OILP': {
  'description': 'Oil pressure',
  'msg_id': 5,
  'bytes': [2,3],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
'AUX1': {
  'description': 'Aux 1',
  'msg_id': 5,
  'bytes': [4,5],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
'AUX2': {
  'description': 'Aux 2',
  'msg_id': 5,
  'bytes': [6,7],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
# msg_id 6
'FUELP': {
  'description': 'Fuel Pressure',
  'msg_id': 6,
  'bytes': [0,1],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},	
'COOL': {
  'description': 'Coolant Temp',
  'msg_id': 6,
  'bytes': [2,3],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
'FUELLEVEL1': {
  'description': 'Fuel Level 1',
  'msg_id': 6,
  'bytes': [4,5],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
'FUELLEVEL2': {
  'description': 'Fuel Level 2',
  'msg_id': 6,
  'bytes': [6,7],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 500},
# msg_id 7
'RDACTEMP': {
  'description': 'RDAC Temp, Cold Junction Compensation',
  'msg_id': 7,
  'bytes': [0,1],
  'type': 'sint',
  'freq': 500},
'RDACVOLT': {
  'description': 'RDAC Input Voltage',
  'msg_id': 7,
  'bytes': [2,3],
  'type': 'sint',
  'freq': 500},
###Note special calculation needed for voltage value
#function ToVolts(v: word): string;
#begin
#  result:=IntToStr(round(v/5.73758));
#  if length(result)=1 then result:='0'+result;
#  Insert('.',result,length(result));
#end;


# msg_id 8
'RPM1': {
  'description': 'RPM 1',
  'msg_id': 8,
  'bytes': [0,1],
  'type': 'word',
  'freq': 200},
'RPM2': {
  'description': 'RPM 2',
  'msg_id': 8,
  'bytes': [2,3],
  'type': 'word',
  'freq': 200},
'MAP': {
  'description': 'MAP',
  'msg_id': 8,
  'bytes': [4,5],
  'type': 'word',
  'min': 0,
  'max': 4095,
  'freq': 200}



# msg_id 9
# This is data sent after calibration
# We are not implementing such features

}

