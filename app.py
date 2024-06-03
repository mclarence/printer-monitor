import asyncio
import configparser
from flask import Flask, render_template
from puresnmp import Client, V2C, PyWrapper

app = Flask(__name__) 
app.config['TEMPLATES_AUTO_RELOAD'] = True

printer_oids = configparser.ConfigParser()
printer_oids.read('printer_oids.ini')

snmp_oid = {}

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

printers = configparser.ConfigParser()
printers.read('printers.ini')

printers_dict = {}

for section in printers.sections():
    if section not in printers_dict:
        printers_dict[section] = {}

    for key, value in printers.items(section):
        printers_dict[section][key] = value
        print(key, value)

print(printers_dict)
print(snmp_oid)

async def get_toner(ip, model, toner):
   client = PyWrapper(Client(ip, V2C("public")))
   output = await client.get(snmp_oid[model]["toner"][toner])
   return output

async def get_drum(ip, model, colour):
   client = PyWrapper(Client(ip, V2C("public")))
   output = await client.get(snmp_oid[model]["drum"][colour])
   return output

@app.route('/')
def index():
    printer_statuses = {}

    for section in printers.sections():
        printer_status = {
            "hostname": printers[section]['hostname'],
            "toner": {
                "c": asyncio.run(get_toner(printers[section]['hostname'], printers[section]['model'], "c")),
                "m": asyncio.run(get_toner(printers[section]['hostname'], printers[section]['model'], "m")),
                "y": asyncio.run(get_toner(printers[section]['hostname'], printers[section]['model'], "y")),
                "k": asyncio.run(get_toner(printers[section]['hostname'], printers[section]['model'], "k"))
            },
            "drum": {
                "c": asyncio.run(get_drum(printers[section]['hostname'], printers[section]['model'], "c")),
                "m": asyncio.run(get_drum(printers[section]['hostname'], printers[section]['model'], "m")),
                "y": asyncio.run(get_drum(printers[section]['hostname'], printers[section]['model'], "y")),
                "k": asyncio.run(get_drum(printers[section]['hostname'], printers[section]['model'], "k"))
            }
        }

        printer_statuses[section] = printer_status

    return render_template('index.html', printers=printer_statuses)
