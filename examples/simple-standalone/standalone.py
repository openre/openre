from openre import OpenRE
from openre.agent.helpers import from_json
config = None
with open('./config.json') as json_file:
    config = from_json(json_file.read())
net = OpenRE(config)
net.deploy()
net.run()
