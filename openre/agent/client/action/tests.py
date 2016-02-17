# -*- coding: utf-8 -*-

from openre.agent.decorators import action, wait
import uuid
from openre.agent.helpers import RPCBrokerProxy, RPCException
from openre.agent.client.helpers import Net
import time

@wait(timeout=10, period=0.5)
def ensure_domain_state(agent, domain_id, expected_state,
                        expected_status='done'):
    """
    Ждем подтверждения от сервера, что у всех доменов появилось нужное
    состояние и статус.
    """
    state = agent.server.domain_state(id=domain_id)
    if not isinstance(expected_state, list):
        expected_state = [expected_state]
    if not isinstance(expected_status, list):
        expected_status = [expected_status]
    if state and state.get('state') in expected_state \
       and state.get('status') in expected_status:
        return True
    return False

def run_test_proxy(agent):
    import os.path
    import tempfile
    import zmq
    ipc_pub_file = os.path.join(
        tempfile.gettempdir(), 'openre-proxy')
    pub = agent.socket(zmq.PUB)
    pub.connect("ipc://%s" % ipc_pub_file)

    sub = agent.socket(zmq.SUB)
    sub.connect('tcp://127.0.0.1:8934')
    sub.setsockopt(zmq.SUBSCRIBE, agent.id.bytes)
    #sub.setsockopt(zmq.SUBSCRIBE, '')

    time.sleep(0.1)
    pub.send_multipart([agent.id.bytes, 'ok'])
    time.sleep(0.1)
    data = sub.recv_multipart()
    assert data == [agent.id.bytes, 'ok']


def run_test_numpy_input(agent):
    D1 = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c1')
    D2 = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c2')
    remote_domain1 = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        D1,
        domain_index=0
    )

    remote_domain2 = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        D2,
        domain_index=1
    )

    config = {
        'layers': [
            {
                'name': 'V1',
                'width': 16,
                'height': 10,
            },
        ],
        'domains': [
            {
                'name': 'D1',
                'id': D1,
                'device'    : {
                    'type': 'IOBaseTesterSimpleSlow',
                    'width': 16,
                    'height': 10,
                },
                'sources': [
                    # [c1 c2]
                    # [c3 c4]
                    {'name': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
            {
                'name': 'D2',
                'id': D2,
                'device'    : {
                    'type': 'IOBaseTesterSimpleCheck',
                },
                'layers'    : [
                    {'name': 'V1', 'input': 'c1', 'shape': [0, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c2', 'shape': [8, 0, 8, 5]},
                    {'name': 'V1', 'input': 'c3', 'shape': [0, 5, 8, 5]},
                    {'name': 'V1', 'input': 'c4', 'shape': [8, 5, 8, 5]},
                ],
            },
        ],
    }
    net = None
    try:
        net = Net(config)
        net.create()
        net.upload_config()
        net.deploy_domains()
        net.deploy_layers()
        net.deploy_neurons()
        net.pre_deploy_synapses()
        net.deploy_synapses()
        net.post_deploy_synapses()
        net.post_deploy()
        time.sleep(1)
        net.run()
        time.sleep(1)
        status1 = agent.server.domain_state(id=D1)
        status2 = agent.server.domain_state(id=D2)
        net.stop()
        d1_stats = remote_domain1.stat.wait()
        d2_stats = remote_domain2.stat.wait()
        for status in [status1, status2]:
            try:
                assert status['status'] == 'running'
            except AssertionError:
                print status
                raise
        assert 'test_io_input' in d2_stats
        assert d2_stats['test_io_input'] > 4
    finally:
        if net:
            net.destroy()
            net.clean()

@action(namespace='client')
def run_tests(agent):
    run_test_proxy(agent)
    agent.connect_server(agent.config['host'], agent.config['port'])
    run_test_numpy_input(agent)

    domain_id = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c1')
    domain = RPCBrokerProxy(
        agent.server_socket, 'broker_proxy',
        domain_id
    )
    try:
        agent.server.domain_start(id=domain_id)
        ensure_domain_state(agent, domain_id, 'blank')
    except RPCException:
        pass
    assert domain.ping.wait() == 'pong'
    assert domain.ping() is None
    assert domain.ping.wait() == 'pong'
    assert domain.ping.no_reply() is None


    agent.server.domain_stop(id=domain_id)

    D1 = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c1')
    D2 = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c2')
    D3 = uuid.UUID('39684e0d-6173-4d41-8efe-add8f24dd2c3')
    remote_domain1 = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        D1,
        domain_index=0
    )

    remote_domain2 = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        D2,
        domain_index=1
    )

    remote_domain3 = RPCBrokerProxy(
        agent.server_socket, 'broker_domain_proxy',
        D3,
        domain_index=2
    )

    config = {
        'layers': [
            {
                'name': 'V1',
                'threshold': 20000,
                'relaxation': 1000,
                'width': 20,
                'height': 20,
                'spike_cost': 11,
                'connect': [
                    {
                        'name': 'V2',
                        'radius': 1,
                        'shift': [0, 0],
                    },
                ],
            },
            {
                'name': 'V2',
                'threshold': 10000,
                'relaxation': 2000,
                'width': 10,
                'height': 10,
                'is_inhibitory': True,
            },
        ],
        'domains': [
            {
                'name'        : 'D1',
                'id': D1,
                'device'    : {
                    'type': 'RandomTest',
                },
                'layers'    : [
                    {'name': 'V1', 'shape': [0, 0, 10, 10]},
                    {'name': 'V1', 'shape': [10, 0, 10, 10]},
                ],
            },
            {
                'name'        : 'D2',
                'id': D2,
                'device'    : {
                    'type': 'RandomTest',
                },
                'layers'    : [
                    {'name': 'V1', 'shape': [10, 10, 10, 10]},
                    {'name': 'V1', 'shape': [0, 10, 10, 10]},
                ],
            },
            {
                'name'        : 'D3',
                'id': D3,
                'device'    : {
                    'type': 'OpenCL',
                },
                'layers'    : [
                    {'name': 'V2'},
                ],
            },
        ],
    }
    net = None
    try:
        net = Net(config)
        net.create()
        net.upload_config()
        net.deploy_domains()
        net.deploy_layers()
        net.deploy_neurons()
        net.pre_deploy_synapses()
        net.deploy_synapses()
        net.post_deploy_synapses()
        net.post_deploy()
        time.sleep(1)
        net.run()
        time.sleep(4)
        status1 = agent.server.domain_state(id=D1)
        status2 = agent.server.domain_state(id=D2)
        status3 = agent.server.domain_state(id=D3)
        net.stop()
        d1_stats = remote_domain1.stat.wait()
        d2_stats = remote_domain2.stat.wait()
        d3_stats = remote_domain3.stat.wait()
        for status in [status1, status2, status3]:
            try:
                assert status['status'] == 'running'
            except AssertionError:
                print status
                raise
        try:
            assert 'spikes_received' in d3_stats
            assert d1_stats['spikes_sent'] + d2_stats['spikes_sent'] \
                    == d3_stats['spikes_received']
            assert d1_stats['spikes_sent_to']['D3'] \
                    + d2_stats['spikes_sent_to']['D3'] \
                    == d3_stats['spikes_received']
        except (AssertionError, KeyError):
            for row in [d1_stats, d2_stats, d3_stats]:
                print row
            raise
    finally:
        if net:
            net.destroy()
            net.clean()
