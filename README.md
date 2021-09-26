# OctoPrint-MerossSmartplug

Work based on OctoPrint-TPLinkSmartplug and python-tuya. This plugin controlls Meross-based SmartPlugs.

##  Screenshots
![screenshot](screenshot.png)

![screenshot](settings.png)

![screenshot](plugeditor.png)

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/thelemax/OctoPrint-MerossSmartplug/archive/master.zip


## Configuration

Once installed go into settings and enter the ip address for your Meross Smartplug device. Adjust additional settings as needed.

## Settings Explained
- **IP**
  - IP or hostname of plug to control. For strip devices use the format `<ip>/<0 based socket index>`, ie 192.168.0.2/0 would control the first socket in the strip.
- **Label**
  - Label to use for title attribute on hover over button in navbar.
- **Icon Class**
  - Class name from [fontawesome](https://fontawesome.com/v3.2.1/icons/) to use for icon on button.
- **Warning Prompt**
  - Always warn when checked.
- **Warn While Printing**
  - Will only warn when printer is printing.
- **On with Upload**
  - When checked, this will allow connected slicers to power on the device when uploading a file.  This requires OctoPrint 1.4.1rc or higher, and does not currently support uploading through the web browser.
- **Use Countdown Timers**
  - Uses the plug's built in countdown timer rule to postpone the power on/off by configured delay in seconds.
- **GCODE Trigger**
  - When checked this will enable the processing of M80 and M81 commands from gcode to power on/off plug.  Syntax for gcode command is M80/M81 followed by hostname/ip.  For example if your plug is 192.168.1.2 your gcode command would be **M80 192.168.1.2**
  - Added with version 0.9.5 you can now use the custom gcode commands `@TPLINKON` and `@TPLINKOFF` followed by the IP address of the plug.  This option will only work for plugs with GCODE processing enabled.  For example if your plug is 192.168.1.2 your gcode command would be **@TPLINKON 192.168.1.2**
- **Auto Connect**
  - Automatically connect to printer after plug is powered on.
  - Will wait for number of seconds configured in **Auto Connect Delay** setting prior to attempting connection to printer.
- **Auto Disconnect**
  - Automatically disconnect printer prior to powering off the plug.
  - Will wait for number of seconds configured in **Auto Disconnect Delay** prior to powering off the plug.
- **Run System Command After On**
  - When checked will run system command configured in **System Command On** setting after a delay in seconds configured in **System Command On Delay**.
- **Run System Command Before Off**
  - When checked will run system command configured in **System Command Off** setting after a delay in seconds configured in **System Command Off Delay**.
  
## Most recent changelog

**[1.0.1](https://github.com/jneilliii/OctoPrint-TPLinkSmartplug/releases/tag/1.0.0)** (04/15/2021)

* fix issue introduced with last update that prevented adding new plugs.

### [All releases](https://github.com/jneilliii/OctoPrint-TPLinkSmartplug/releases)

## Get Help

If you experience issues with this plugin or need assistance please use the issue tracker by clicking issues above.

### Additional Plugins

Check out my other plugins [here](https://plugins.octoprint.org/by_author/#jneilliii)

## Support jneilliii Efforts
Most of the code used in this plugin has been written by [jneilliii](https://github.com/jneilliii) so if you want to support someone, you can support his work.

