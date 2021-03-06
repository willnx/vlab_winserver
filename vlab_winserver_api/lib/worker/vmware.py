# -*- coding: UTF-8 -*-
"""Business logic for backend worker tasks"""
import time
import random
import os.path
from celery.utils.log import get_task_logger
from vlab_inf_common.vmware import vCenter, Ova, vim, virtual_machine, consume_task

from vlab_winserver_api.lib import const


logger = get_task_logger(__name__)
logger.setLevel(const.VLAB_WINSERVER_LOG_LEVEL.upper())


def show_winserver(username):
    """Obtain basic information about WinServer

    :Returns: Dictionary

    :param username: The user requesting info about their WinServer
    :type username: String
    """
    winserver_vms = {}
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        winserver_vms = {}
        for vm in folder.childEntity:
            info = virtual_machine.get_info(vcenter, vm, username)
            if info['meta']['component'] == 'WinServer':
                winserver_vms[vm.name] = info
    return winserver_vms


def delete_winserver(username, machine_name, logger):
    """Unregister and destroy a user's WinServer

    :Returns: None

    :param username: The user who wants to delete their jumpbox
    :type username: String

    :param machine_name: The name of the VM to delete
    :type machine_name: String

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        for entity in folder.childEntity:
            if entity.name == machine_name:
                info = virtual_machine.get_info(vcenter, entity, username)
                if info['meta']['component'] == 'WinServer':
                    logger.debug('powering off VM')
                    virtual_machine.power(entity, state='off')
                    delete_task = entity.Destroy_Task()
                    logger.debug('blocking while VM is being destroyed')
                    consume_task(delete_task)
                    break
        else:
            raise ValueError('No {} named {} found'.format('winserver', machine_name))


def create_winserver(username, machine_name, image, network, ip_config, logger):
    """Deploy a new instance of WinServer

    :Returns: Dictionary

    :param username: The name of the user who wants to create a new WinServer
    :type username: String

    :param machine_name: The name of the new instance of WinServer
    :type machine_name: String

    :param image: The image/version of WinServer to create
    :type image: String

    :param network: The name of the network to connect the new WinServer instance up to
    :type network: String

    :param ip_config: The IPv4 network configuration for the WinServer instance
    :type ip_config: Dictionary

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER,
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        image_name = convert_name(image)
        logger.info(image_name)
        try:
            ova = Ova(os.path.join(const.VLAB_WINSERVER_IMAGES_DIR, image_name))
        except FileNotFoundError:
            error = 'Invalid version of Windows Server supplied: {}'.format(image)
            raise ValueError(error)
        try:
            network_map = vim.OvfManager.NetworkMapping()
            network_map.name = ova.networks[0]
            try:
                network_map.network = vcenter.networks[network]
            except KeyError:
                raise ValueError('No such network named {}'.format(network))
            the_vm = virtual_machine.deploy_from_ova(vcenter, ova, [network_map],
                                                     username, machine_name, logger)
        finally:
            ova.close()
        if ip_config['static-ip']:
            # Hack - The VM will walk through the C:\unattend.xml answer file
            # and then reboot. We wont have valid login creds until after the
            # reboot. Trying to *notice* the reboot is a race condition nightmare
            time.sleep(300)
            virtual_machine.config_static_ip(vcenter,
                                             the_vm,
                                             ip_config['static-ip'],
                                             ip_config['default-gateway'],
                                             ip_config['netmask'],
                                             ip_config['dns'],
                                             user='Administrator',
                                             password='a',
                                             logger=logger,
                                             os='windows')
        meta_data = {'component' : "WinServer",
                     'created': time.time(),
                     'version': image,
                     'configured': False,
                     'generation': 1,
                    }
        virtual_machine.set_meta(the_vm, meta_data)
        info = virtual_machine.get_info(vcenter, the_vm, username, ensure_ip=True)
        return {the_vm.name: info}


def list_images():
    """Obtain a list of available versions of WinServer that can be created

    :Returns: List
    """
    images = os.listdir(const.VLAB_WINSERVER_IMAGES_DIR)
    images = [convert_name(x, to_version=True) for x in images]
    return images


def convert_name(name, to_version=False):
    """This function centralizes converting between the name of the OVA, and the
    version of software it contains.

    The naming convention of the OVA files is ``WinServer-<version>.ova`` i.e. WinServer-2012R2.ova

    :param name: The thing to covert
    :type name: String

    :param to_version: Set to True to covert the name of an OVA to the version
    :type to_version: Boolean
    """
    if to_version:
        return name.split('-')[-1].replace('.ova', '')
    else:
        return 'WinServer-{}.ova'.format(name)


def update_network(username, machine_name, new_network):
    """Implements the VM network update

    :param username: The name of the user who owns the virtual machine
    :type username: String

    :param machine_name: The name of the virtual machine
    :type machine_name: String

    :param new_network: The name of the new network to connect the VM to
    :type new_network: String
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        for entity in folder.childEntity:
            if entity.name == machine_name:
                info = virtual_machine.get_info(vcenter, entity, username)
                if info['meta']['component'] == 'WinServer':
                    the_vm = entity
                    break
        else:
            error = 'No Windows Server named {} found'.format(machine_name)
            raise ValueError(error)

        try:
            network = vcenter.networks[new_network]
        except KeyError:
            error = 'No VM named {} found'.format(machine_name)
            raise ValueError(error)
        else:
            virtual_machine.change_network(the_vm, network)
