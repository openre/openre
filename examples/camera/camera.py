from openre import OpenRE
from openre.agent.helpers import from_json
import logging
logging.basicConfig(
    format='%(levelname)s:%(message)s',
    level='DEBUG'
)

def main():
    config = None
    with open('./session.json') as json_file:
        config = from_json(json_file.read())
    net = OpenRE(config)
    net.deploy()
    net.run()

if __name__ == '__main__':
    main()
