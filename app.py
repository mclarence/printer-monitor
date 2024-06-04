import asyncio
import configparser
from flask import Flask, render_template
from puresnmp import Client, V2C, PyWrapper

app = Flask(__name__) 
app.config['TEMPLATES_AUTO_RELOAD'] = True

printer_oids = configparser.ConfigParser()
printers = configparser.ConfigParser()

printers.read('printers.ini')
printer_oids.read('printer_oids.ini')

snmp_oid = {}
printers_dict = {}

for section in printer_oids.sections():
    if section not in snmp_oid:
        snmp_oid[section] = {}
        snmp_oid[section]['toner'] = {}
        snmp_oid[section]['drum'] = {}

    for key, value in printer_oids.items(section):
        if key.startswith("toner"):
            if 'toner' not in snmp_oid[section]:
                snmp_oid[section]['toner'] = {}
            
            split = key.split("_")
            snmp_oid[section]['toner'][split[1]] = value
        elif key.startswith("drum"):
            if 'drum' not in snmp_oid[section]:
                snmp_oid[section]['drum'] = {}

            split = key.split("_")
            snmp_oid[section]['drum'][split[1]] = value
        else:
            print("Unrecognized key: " + key)

for section in printers.sections():
    if section not in printers_dict:
        printers_dict[section] = {}

    for key, value in printers.items(section):
        printers_dict[section][key] = value

async def get_toner(ip, model, toner):
   client = PyWrapper(Client(ip, V2C("public")))
   output = await client.get(snmp_oid[model]["toner"][toner])
   return output

async def get_drum(ip, model, colour):
   client = PyWrapper(Client(ip, V2C("public")))
   output = await client.get(snmp_oid[model]["drum"][colour])
   return output

async def get_printer_status(printer):
    hostname = printers[printer]['hostname']
    model = printers[printer]['model']
    toner_coro = [
        get_toner(hostname, model, color) for color in ['c', 'm', 'y', 'k']
    ]

    drum_coro = [
        get_drum(hostname, model, color) for color in ['c', 'm', 'y', 'k']
    ]

    toner_results = await asyncio.gather(*toner_coro)
    drum_results = await asyncio.gather(*drum_coro)

    return {
        "friendly_name": printer,
        "hostname": hostname,
        "toner": dict(zip(['c', 'm', 'y', 'k'], toner_results)),
        "drum": dict(zip(['c', 'm', 'y', 'k'], drum_results))
    }

def get_set_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as e:
        if e.args[0].startswith('There is no current event loop'):
            asyncio.set_event_loop(asyncio.new_event_loop())
            return asyncio.get_event_loop()
        raise e

@app.route('/', methods=['GET'])
def index():
    tasks = [get_printer_status(printer) for printer in printers_dict.keys()]

    printer_statuses = get_set_event_loop().run_until_complete(asyncio.gather(*tasks))
    low_consumables = []

    for printer in printer_statuses:
        for toner in printer['toner']:
            if printer['toner'][toner] < 10:
                low_consumables.append({
                    "printer": printer['friendly_name'],
                    "type": "toner",
                    "color": toner,
                    "level": printer['toner'][toner]
                })

        for drum in printer['drum']:
            if printer['drum'][drum] < 10:
                low_consumables.append({
                    "printer": printer['friendly_name'],
                    "type": "drum",
                    "color": drum,
                    "level": printer['drum'][drum]
                })

    return render_template('index.html', printers=printer_statuses, low_consumables=low_consumables)
