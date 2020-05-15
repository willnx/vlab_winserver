# -*- coding: UTF-8 -*-
"""
Defines the RESTful API for managing instances of Microsoft Server
"""
import ujson
from flask import current_app
from flask_classy import request, route, Response
from vlab_inf_common.views import MachineView
from vlab_inf_common.vmware import vCenter, vim
from vlab_inf_common.input_validators import network_config_ok
from vlab_api_common import describe, get_logger, requires, validate_input


from vlab_winserver_api.lib import const


logger = get_logger(__name__, loglevel=const.VLAB_WINSERVER_LOG_LEVEL)


class WinServerView(MachineView):
    """API end point for managing instances of Microsoft Server"""
    route_base = '/api/2/inf/winserver'
    RESOURCE = 'winserver'
    POST_SCHEMA = { "$schema": "http://json-schema.org/draft-04/schema#",
                    "type": "object",
                    "description": "Create a winserver",
                    "properties": {
                        "name": {
                            "description": "The name to give your WinServer instance",
                            "type": "string"
                        },
                        "image": {
                            "description": "The image/version of WinServer to create",
                            "type": "string"
                        },
                        "network": {
                            "description": "The network to hook the WinServer instance up to",
                            "type": "string"
                        },
                        "ip-config": {
                            "description": "Supply to have a static IP configured. Otherwise, obtain a DHCP address",
                            "type": "object",
                            "properties": {
                                "static-ip": {
                                    "description": "The IPv4 address to assign to the VM",
                                    "type": "string"
                                },
                                "default-gateway": {
                                    "description": "The IPv4 address of the network default gateway",
                                    "type": "string",
                                    "default": "192.168.1.1"
                                },
                                "netmask":  {
                                    "description": "The subnet mask for the network",
                                    "type": "string",
                                    "default": "255.255.255.0"
                                },
                                "dns": {
                                    "description": "The IPv4 address(es) of DNS servers",
                                    "type": "array",
                                    "default": ["192.168.1.1"]
                                },
                            },
                        },
                    },
                    "required": ["name", "image", "network"]
                  }
    DELETE_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                     "description": "Destroy a WinServer",
                     "type": "object",
                     "properties": {
                        "name": {
                            "description": "The name of the WinServer instance to destroy",
                            "type": "string"
                        }
                     },
                     "required": ["name"]
                    }
    GET_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                  "description": "Display the WinServer instances you own"
                 }
    IMAGES_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                     "description": "View available versions of WinServer that can be created"
                    }


    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @describe(post=POST_SCHEMA, delete=DELETE_SCHEMA, get=GET_SCHEMA)
    def get(self, *args, **kwargs):
        """Display the WinServer instances you own"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        task = current_app.celery_app.send_task('winserver.show', [username, txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @validate_input(schema=POST_SCHEMA)
    def post(self, *args, **kwargs):
        """Create a WinServer"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        body = kwargs['body']
        machine_name = body['name']
        image = body['image']
        network = '{}_{}'.format(username, body['network'])
        ip_config, error = _get_ip_config(body.get('ip-config', {}))
        if error:
            resp_data['error'] = error
            resp = Response(ujson.dumps(resp_data))
            resp.status_code = 400
        else:
            task = current_app.celery_app.send_task('winserver.create', [username, machine_name, image, network, ip_config, txn_id])
            resp_data['content'] = {'task-id': task.id}
            resp = Response(ujson.dumps(resp_data))
            resp.status_code = 202
            resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @validate_input(schema=DELETE_SCHEMA)
    def delete(self, *args, **kwargs):
        """Destroy a WinServer"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        machine_name = kwargs['body']['name']
        task = current_app.celery_app.send_task('winserver.delete', [username, machine_name, txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @route('/image', methods=["GET"])
    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @describe(get=IMAGES_SCHEMA)
    def image(self, *args, **kwargs):
        """Show available versions of WinServer that can be deployed"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        task = current_app.celery_app.send_task('winserver.image', [txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp


def _get_ip_config(supplied_config):
    """Ensures API defaults are applied to object

    :Returns: Tuple

    :param supplied_config: The API params supplied by the user
    :type supplied_config: Dictionary
    """
    error = ''
    defaults = {'static-ip': '',
                'default-gateway': '192.168.1.1',
                'netmask': '255.255.255.0',
                'dns': ["192.168.1.1"]
               }
    defaults.update(supplied_config)
    if defaults['static-ip']:
        error = network_config_ok(defaults['static-ip'], defaults['default-gateway'], defaults['netmask'])
    return defaults, error
