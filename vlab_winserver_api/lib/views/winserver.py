# -*- coding: UTF-8 -*-
"""
TODO
"""
import ujson
from flask import current_app
from flask_classy import request, route
from vlab_inf_common.views import TaskView
from vlab_inf_common.vmware import vCenter, vim
from vlab_api_common import describe, get_logger, requires, validate_input


from vlab_winserver_api.lib import const


logger = get_logger(__name__, loglevel=const.VLAB_WINSERVER_LOG_LEVEL)


class WinServerView(TaskView):
    """API end point TODO"""
    route_base = '/api/1/inf/winserver'
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
                        }
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


    @requires(verify=False, version=(1,2))
    @describe(post=POST_SCHEMA, delete=DELETE_SCHEMA, get=GET_SCHEMA)
    def get(self, *args, **kwargs):
        """Display the WinServer instances you own"""
        username = kwargs['token']['username']
        resp = {'user' : username}
        task = current_app.celery_app.send_task('winserver.show', [username])
        resp['content'] = {'task-id': task.id}
        return ujson.dumps(resp), 200

    @requires(verify=False, version=(1,2)) # XXX remove verify=False before commit
    @validate_input(schema=POST_SCHEMA)
    def post(self, *args, **kwargs):
        """Create a WinServer"""
        username = kwargs['token']['username']
        resp = {'user' : username}
        body = kwargs['body']
        machine_name = body['name']
        image = body['image']
        network = body['network']
        task = current_app.celery_app.send_task('winserver.create', [username, machine_name, image, network])
        resp['content'] = {'task-id': task.id}
        return ujson.dumps(resp), 200

    @requires(verify=False, version=(1,2)) # XXX remove verify=False before commit
    @validate_input(schema=DELETE_SCHEMA)
    def delete(self, *args, **kwargs):
        """Destroy a WinServer"""
        username = kwargs['token']['username']
        resp = {'user' : username}
        machine_name = kwargs['body']['name']
        task = current_app.celery_app.send_task('winserver.delete', [username, machine_name])
        resp['content'] = {'task-id': task.id}
        return ujson.dumps(resp), 200

    @route('/image', methods=["GET"])
    @requires(verify=False, version=(1,2))
    @describe(get=IMAGES_SCHEMA)
    def image(self, *args, **kwargs):
        """Show available versions of WinServer that can be deployed"""
        username = kwargs['token']['username']
        resp = {'user' : username}
        task = current_app.celery_app.send_task('winserver.image')
        resp['content'] = {'task-id': task.id}
        return ujson.dumps(resp), 200
