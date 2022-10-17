#!/usr/bin/python3

# https://dbus.freedesktop.org/doc/dbus-python/tutorial.html
# https://github.com/GNOME/mutter/blob/b5f99bd12ebc483e682e39c8126a1b51772bc67d/data/dbus-interfaces/org.gnome.Mutter.DisplayConfig.xml
# https://ask.fedoraproject.org/t/change-scaling-resolution-of-primary-monitor-from-bash-terminal/19892

import dbus
bus = dbus.SessionBus()

ON_SCALE = 1.5
OFF_SCALE = 1.0

display_config_well_known_name = "org.gnome.Mutter.DisplayConfig"
display_config_object_path = "/org/gnome/Mutter/DisplayConfig"

display_config_proxy = bus.get_object(display_config_well_known_name, display_config_object_path)
display_config_interface = dbus.Interface(display_config_proxy, dbus_interface=display_config_well_known_name)

serial, physical_monitors, logical_monitors, properties = display_config_interface.GetCurrentState()

updated_logical_monitors=[]
primary_resolution=(0,0)
new_scale=1.0
# Primary monitor needs to be first
sorted_logical_monitors = sorted(logical_monitors, key=lambda monitor: not monitor[4])

for i, (x, y, scale, transform, primary, linked_monitors_info, props) in enumerate(sorted_logical_monitors):
    if primary == 1:
        scale = ON_SCALE if (scale == OFF_SCALE) else OFF_SCALE # toggle scaling between user set scaling for the primary monitor
        new_scale = scale
    physical_monitors_config = []
    for linked_monitor_connector, linked_monitor_vendor, linked_monitor_product, linked_monitor_serial in linked_monitors_info:
        for monitor_info, monitor_modes, monitor_properties in physical_monitors:
            monitor_connector, monitor_vendor, monitor_product, monitor_serial = monitor_info
            if linked_monitor_connector == monitor_connector:
                for mode_id, mode_width, mode_height, mode_refresh, mode_preferred_scale, mode_supported_scales, mode_properties in monitor_modes:
                    if mode_properties.get("is-current", False): # ( mode_properties provides is-current, is-preferred, is-interlaced, and more)
                        physical_monitors_config.append(dbus.Struct([monitor_connector, mode_id, {}]))
                        if scale not in mode_supported_scales:
                            print("Error: " + monitor_properties.get("display-name") + " doesn't support that scaling value! (" + str(scale) + ")")
                        elif primary == 1:
                            print("Setting scaling of: " + monitor_properties.get("display-name") + " to " + str(scale) + "!")
                            # Save our primary monitor's resolution for later
                            primary_resolution = (mode_width, mode_height)
    # TODO: if we adjust scaling, the adjacent x and y values are no longer guaranteed to be the same.
    # Recalculate them (properly), and any other monitors that are affected by the co-ordinate change.
    if primary == 0:
        x = primary_resolution[0] / new_scale
    updated_logical_monitor_struct = dbus.Struct([dbus.Int32(x), dbus.Int32(y), dbus.Double(scale), dbus.UInt32(transform), dbus.Boolean(primary), physical_monitors_config])
    updated_logical_monitors.append(updated_logical_monitor_struct)

properties_to_apply = { "layout_mode": properties.get("layout-mode")}
method = 1 # 2 means show a prompt before applying settings; 1 means instantly apply settings without prompt
display_config_interface.ApplyMonitorsConfig(dbus.UInt32(serial), dbus.UInt32(method), updated_logical_monitors, properties_to_apply)
