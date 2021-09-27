# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.server import user_permission
import socket
import json
import logging
import os
import re
import threading
import time

import asyncio
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

#https://github.com/albertogeniola/MerossIot/blob/0.4.X.X/examples/toggle.py

class merossmartplugPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.StartupPlugin,
):
    def __init__(self):
        self._logger = logging.getLogger("octoprint.plugins.merosssmartplug")
        self._merosssmartplug_logger = logging.getLogger(
            "octoprint.plugins.merosssmartplug.debug"
        )

    def init(self):
        email = self._settings.get(["email"])
        password = self._settings.get(["password"])

		# Setup the HTTP client API from user-password
        http_api_client = MerossHttpClient.async_from_user_password(email, password)

		# Setup and start the device manager
        manager = MerossManager(http_client=http_api_client)
        manager.async_init()

    # ~~ StartupPlugin mixin

    def on_startup(self, host, port):
        # setup customized logger
        from octoprint.logging.handlers import CleaningTimedRotatingFileHandler

        merosssmartplug_logging_handler = CleaningTimedRotatingFileHandler(
            self._settings.get_plugin_logfile_path(postfix="debug"),
            when="D",
            backupCount=3,
        )
        merosssmartplug_logging_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        )
        merosssmartplug_logging_handler.setLevel(logging.DEBUG)

        self._merosssmartplug_logger.addHandler(merosssmartplug_logging_handler)
        self._merosssmartplug_logger.setLevel(
            logging.DEBUG
            if self._settings.get_boolean(["debug_logging"])
            else logging.INFO
        )
        self._merosssmartplug_logger.propagate = False
        self.init()

    def on_after_startup(self):
        self._logger.info("MerossSmartplug loaded!")

    # ~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            debug_logging=False,
            email="",
            password="",
            arrSmartplugs=[
                {
                    "label": "",
                    "icon": "icon-bolt",
                    "displayWarning": True,
                    "warnPrinting": False,
                    "gcodeEnabled": False,
                    "gcodeOnDelay": 0,
                    "gcodeOffDelay": 0,
                    "autoConnect": True,
                    "autoConnectDelay": 10.0,
                    "autoDisconnect": True,
                    "autoDisconnectDelay": 0,
                    "sysCmdOn": False,
                    "sysRunCmdOn": "",
                    "sysCmdOnDelay": 0,
                    "sysCmdOff": False,
                    "sysRunCmdOff": "",
                    "sysCmdOffDelay": 0,
                    "currentState": "unknown",
                    "btnColor": "#808080",
                    "useCountdownRules": False,
                    "countdownOnDelay": 0,
                    "countdownOffDelay": 0,
                }
            ],
            pollingInterval=15,
            pollingEnabled=False,
        )

    def get_settings_restricted_paths(self):
        return dict(
            admin=[
                [
                    "arrSmartplugs",
                ],
            ]
        )

    def on_settings_save(self, data):
        old_debug_logging = self._settings.get_boolean(["debug_logging"])

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        new_debug_logging = self._settings.get_boolean(["debug_logging"])
        if old_debug_logging != new_debug_logging:
            if new_debug_logging:
                self._merosssmartplug_logger.setLevel(logging.DEBUG)
            else:
                self._merosssmartplug_logger.setLevel(logging.INFO)
        self.init()

    def get_settings_version(self):
        return 4

    def on_settings_migrate(self, target, current=None):
        if current is None or current < self.get_settings_version():
            # Reset plug settings to defaults.
            self._logger.debug("Resetting arrSmartplugs for merosssmartplug settings.")
            self._settings.set(
                ["arrSmartplugs"], self.get_settings_defaults()["arrSmartplugs"]
            )

    # ~~ AssetPlugin mixin

    def get_assets(self):
        return dict(js=["jsmerosssmartplug.js"], css=["css/merosssmartplug.css"])

    # ~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=True),
            dict(type="settings", custom_bindings=True),
        ]

    # ~~ SimpleApiPlugin mixin

    def turn_on(self, pluglabel):
        self._merosssmartplug_logger.debug("Turning on %s." % pluglabel)
        if self.is_turned_on(pluglabel=pluglabel):
            self._merosssmartplug_logger.debug("Plug %s already turned on" % pluglabel)
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(currentState="on", label=pluglabel)
            )
            return
        plug = self.plug_search(
            self._settings.get(["arrSmartplugs"]), "label", pluglabel
        )
        self._merosssmartplug_logger.debug(plug)
        if plug["useCountdownRules"]:
            chk = self.sendCommand(
                "countdown", plug["label"], int(plug["countdownOnDelay"])
            )
        else:
            chk = self.sendCommand("on", plug["label"])

        if chk is not False:
            self.check_status(plug["label"], chk)
            if plug["autoConnect"]:
                c = threading.Timer(
                    int(plug["autoConnectDelay"]), self._printer.connect
                )
                c.start()
            if plug["sysCmdOn"]:
                t = threading.Timer(
                    int(plug["sysCmdOnDelay"]), os.system, args=[plug["sysRunCmdOn"]]
                )
                t.start()
        else:
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(currentState="unknown", label=pluglabel)
            )

    def turn_off(self, pluglabel):
        self._merosssmartplug_logger.debug("Turning off %s." % pluglabel)
        if not self.is_turned_on(pluglabel=pluglabel):
            self._merosssmartplug_logger.debug("Plug %s already turned off" % pluglabel)
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(currentState="off", label=pluglabel)
            )
            return
        plug = self.plug_search(
            self._settings.get(["arrSmartplugs"]), "label", pluglabel
        )
        self._merosssmartplug_logger.debug(plug)
        if plug["useCountdownRules"]:
            chk = self.sendCommand(
                "countdown", plug["label"], int(plug["countdownOffDelay"])
            )

        if plug["sysCmdOff"]:
            t = threading.Timer(
                int(plug["sysCmdOffDelay"]), os.system, args=[plug["sysRunCmdOff"]]
            )
            t.start()
        if plug["autoDisconnect"]:
            self._printer.disconnect()
            time.sleep(int(plug["autoDisconnectDelay"]))

        if not plug["useCountdownRules"]:
            chk = self.sendCommand("off", plug["label"])

        if chk is not False:
            self.check_status(plug["label"], chk)
        else:
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(currentState="unknown", label=pluglabel)
            )

    def check_status(self, pluglabel, resp=None):
        self._merosssmartplug_logger.debug("Checking status of %s." % pluglabel)
        if pluglabel != "":
            response = resp or self.sendCommand("info", pluglabel)
            if response is False:
                self._plugin_manager.send_plugin_message(
                    self._identifier, dict(currentState="unknown", label=pluglabel)
                )
            else:
                self._plugin_manager.send_plugin_message(
                    self._identifier,
                    dict(
                        currentState=(
                            "on" if self.is_turned_on(response, pluglabel) else "off"
                        ),
                        label=pluglabel,
                    ),
                )

    def is_turned_on(self, data=None, pluglabel=None):
        if data is None and pluglabel:
            data = self.sendCommand("info", pluglabel)

        return data

    def get_api_commands(self):
        return dict(turnOn=["label"], turnOff=["label"], checkStatus=["label"])

    def on_api_command(self, command, data):
        if not user_permission.can():
            from flask import make_response

            return make_response("Insufficient rights", 403)

        if command == "turnOn":
            self.turn_on("{label}".format(**data))
        elif command == "turnOff":
            self.turn_off("{label}".format(**data))
        elif command == "checkStatus":
            self.check_status("{label}".format(**data))

    # ~~ Utilities

    def plug_search(self, lst, key, value):
        for item in lst:
            if item[key] == value:
                return item

    def sendCommand(self, cmd, pluglabel, args=None, tries=1):
        self._merosssmartplug_logger.debug("Sending command: %s to %s" % (cmd, pluglabel))
        plug = self.plug_search(
            self._settings.get(["arrSmartplugs"]), "label", pluglabel
        )

		# Retrieve all the MSS210 devices that are registered on this account
        manager.async_device_discovery()
        for dev in manager.find_devices(device_type="mss210"): #<---------
            if dev.get_name() == pluglabel:
                device = dev
                break
        else:
            return False

        commands = {
            "info": ("state", None),
            "on": ("turn_on", None),
            "off": ("turn_off", None),
            "countdown": ("set_timer", None),
        }

        try:
            command, arg = commands[cmd]
            func = getattr(device, command, None)
            if not func:
                self._merosssmartplug_logger.debug("No such command '%s'" % command)
                return False
            if args:
                func(args)
            elif arg is not None:
                func(arg, plug["slot"])
            else:
                func()
            time.sleep(0.5)
            ret = device.state()
            self._merosssmartplug_logger.debug("Status: %s" % str(ret))
            return ret
        except:
            self._merosssmartplug_logger.debug(
                "Something went wrong while running the command"
            )
            return False

    # ~~ Gcode processing hook

    def gcode_turn_off(self, plug):
        if plug["warnPrinting"] and self._printer.is_printing():
            self._logger.info(
                "Not powering off %s because printer is printing." % plug["label"]
            )
        else:
            self.turn_off(plug["label"])

    def processGCODE(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode:
            if cmd.startswith("M80"):
                name = re.sub(r"^M80\s?", "", cmd)
                self._merosssmartplug_logger.debug(
                    "Received M80 command, attempting power on of %s." % name
                )
                plug = self.plug_search(
                   self._settings.get(["arrSmartplugs"]), "label", name
                )
                self._merosssmartplug_logger.debug(plug)
                if plug["gcodeEnabled"]:
                    t = threading.Timer(
                        int(plug["gcodeOnDelay"]), self.turn_on, args=[plug["label"]]
                    )
                    t.start()
                return
            elif cmd.startswith("M81"):
                name = re.sub(r"^M81\s?", "", cmd)
                self._merosssmartplug_logger.debug(
                    "Received M81 command, attempting power off of %s." % name
                )
                plug = self.plug_search(
                    self._settings.get(["arrSmartplugs"]), "label", name
                )
                self._merosssmartplug_logger.debug(plug)
                if plug["gcodeEnabled"]:
                    t = threading.Timer(
                        int(plug["gcodeOffDelay"]), self.gcode_turn_off, args=[plug]
                    )
                    t.start()
                return
            else:
                return

        elif cmd.startswith("@MEROSSON"): #<---------
            name = re.sub(r"^@MEROSSON\s?", "", cmd)
            self._merosssmartplug_logger.debug(
                "Received @MEROSSON command, attempting power on of %s." % name
            )
            plug = self.plug_search(
                self._settings.get(["arrSmartplugs"]), "label", name
            )
            self._merosssmartplug_logger.debug(plug)
            if plug["gcodeEnabled"]:
                t = threading.Timer(
                    int(plug["gcodeOnDelay"]), self.turn_on, args=[plug["label"]]
                )
                t.start()
            return None
        elif cmd.startswith("@MEROSSOFF"):
            name = re.sub(r"^@MEROSSOFF\s?", "", cmd)
            self._merosssmartplug_logger.debug(
                "Received MEROSSOFF command, attempting power off of %s." % name
            )
            plug = self.plug_search(
                self._settings.get(["arrSmartplugs"]), "label", name
            )
            self._merosssmartplug_logger.debug(plug)
            if plug["gcodeEnabled"]:
                t = threading.Timer(
                    int(plug["gcodeOffDelay"]), self.gcode_turn_off, args=[plug]
                )
                t.start()
            return None

    # ~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            merosssmartplug=dict(
                displayName="Meross Smartplug",
                displayVersion=self._plugin_version,
                # version check: github repository
                type="github_release",
                user="thelemax",
                repo="OctoPrint-MerossSmartplug",
                current=self._plugin_version,
                # update method: pip
                pip="https://github.com/thelemax/OctoPrint-MerossSmartplug/archive/{target_version}.zip",
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Meross Smartplug"
__plugin_version__ = "0.0.1"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = merosssmartplugPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.processGCODE,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
    }
