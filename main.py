#!/usr/bin/python3

import ovh
from tinydb import TinyDB, Query
from os.path import join, dirname
from time import strftime
from requests import get
from re import search
from sys import argv

DB = join(dirname(argv[0]), "config.json")

# Création de la base de donnée TinyDB

config = TinyDB(DB, sort_keys=True, indent=4, separators=(',', ': '))

q = Query()
c_ovh = config.table("ovh")
s_ovh = c_ovh.count(q.credentials.exists())

# Création du fichier de configuration

if s_ovh < 1:
    c_ovh.insert({"credentials": {
        "application_key": "",
        "application_secret": "",
        "consumer_key": "",
        "endpoint":"ovh-eu",
    }, "domain": {
        "ids": {},
        "name": "",
        "subdomain": [],
        "update": "",
    }})
elif s_ovh > 1:
    exit()

# Controle des paramètres

errors = 0
credentials = c_ovh.get(q.credentials.exists())["credentials"]
domain = c_ovh.get(q.domain.exists())["domain"]
if not credentials["endpoint"]:
    print("Please fill in the 'ovh/credentials/endpoint' variable")
    errors += 1
if not credentials["application_key"]:
    print("Please fill in the 'ovh/credentials/application_key' variable")
    errors += 1
if not credentials["application_secret"]:
    print("Please fill in the 'ovh/credentials/application_secret' variable")
    errors += 1
if not credentials["consumer_key"]:
    print("Please fill in the 'ovh/credentials/consumer_key' variable")
    errors += 1
if not domain["name"]:
    print("Please fill in the 'ovh/domain/name' variable")
    errors += 1
if errors > 0:
    print(f"Configure the '{DB}' file")
    exit()

# Authentification sur l'API d'OVH

client = ovh.Client(
    endpoint = credentials["endpoint"],
    application_key = credentials["application_key"],
    application_secret = credentials["application_secret"],
    consumer_key = credentials["consumer_key"]
)

# Récupération de la zone DNS

if "ids" not in domain or not domain["ids"]:
    for sub in domain["subdomain"]:
        result = client.get(f"/domain/zone/{domain['name']}/record",
            fieldType="A",
            subDomain=sub,
        )
        if len(result) == 0:
            break
        domain["ids"][result[0]] = ""
    c_ovh.update({"domain": domain}, q.domain.exists())

# Récupération de l'IP publique

req = get("http://monip.org")
current_addr = search(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", req.text).group(0)

# Mise à jour de la zone DNS

edited = False
for id, addr in domain["ids"].items():
    if not domain["ids"][id]:
        result = client.get(f"/domain/zone/{domain['name']}/record/{id}")
        domain["ids"][id] = result["target"]
    if current_addr and domain["ids"][id] != current_addr:
        result = client.put(f"/domain/zone/{domain['name']}/record/{id}",
            target=current_addr
        )
        print(f"{id}: {domain['ids'][id]} -> {current_addr}")
        domain["ids"][id] = current_addr
        edited = True

if edited:
    domain["update"] = strftime("%d/%m/%Y %H:%M")
c_ovh.update({"domain": domain}, q.domain.exists())
