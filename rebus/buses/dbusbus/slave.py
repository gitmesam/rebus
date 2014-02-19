import os
import dbus
import dbus.glib
from dbus.mainloop.glib import DBusGMainLoop
import dbus.service
import gobject
from rebus.bus import Bus
from rebus.descriptor import Descriptor

import logging
log = logging.getLogger("rebus.bus.dbus")


gobject.threads_init()
dbus.glib.init_threads()
DBusGMainLoop(set_as_default=True)


@Bus.register
class DBus(Bus):
    _name_ = "dbus"
    _desc_ = "Use DBus to exchange messages by connecting to REbus master"
    def __init__(self, busaddr=None):
        Bus.__init__(self)
        self.bus = dbus.SessionBus() if busaddr is None else dbus.bus.BusConnection(busaddr)
        self.rebus = self.bus.get_object("com.airbus.rebus.bus", "/bus")

    def join(self, name, domain="default", callback=None):
        self.objpath = os.path.join("/agent", name)
        self.obj = dbus.service.Object(self.bus, self.objpath)
        self.well_known_name = dbus.service.BusName("com.airbus.rebus.agent.%s" % name, self.bus)
        self.agent_id = "%s-%s" % (name, self.bus.get_unique_name())

        self.iface = dbus.Interface(self.rebus, "com.airbus.rebus.bus")
        self.iface.register(domain, self.objpath)

        log.info("Agent %s registered with id %s on domain %s" 
                 % (name, self.agent_id, domain))
        
        if callback:
            self.callback = callback
            self.bus.add_signal_receiver(self.callback_wrapper,
                                         dbus_interface="com.airbus.rebus.bus",
                                         signal_name="new_descriptor")
        return self.agent_id
    def mainloop(self):
        gobject.MainLoop().run()

    def lock(self, agent_id, lockid, selector):
        return self.iface.lock(lockid, selector)
    def get(self, agent_id, selector):
        return Descriptor.unserialize(str(self.iface.get(selector)))
    def push(self, agent_id, selector, descriptor):
        return self.iface.push(agent_id, selector, descriptor.serialize())
    def get_selectors(self, agent_id, selector_filter):
        return self.iface.get_selectors(selector)

    def callback_wrapper(self, sender_id, domain, selector):
        if sender_id != self.agent_id:
            self.callback(sender_id, domain, selector)