
To build the snap just run the command `snapcraft` from the root of the repo.

To install it use the command:
snap install fixgateway_0.3_amd64.snap --dangerous

dangerous is needed becuase the package is not signed, this would not be needed if we get a developer account and added the snap to the store.
<br>
The config files are in:
```
~/snap/fixgateway/current/.makerplane/fixgw/config/
```

snaps run in a container so are isolated, one needs to grant access to special devices.
To grant access to the can-bus:
```
snap connect fixgateway:can-bus snapd
```

IF you need to access a serial port you should enable a feature that makes this possible:
```
sudo snap set system experimental.hotplug=true
sudo systemctl restart snapd
```

Then you can list serial port slots/plugs:
```
snap interface serial-port --attrs
```

Then make the connection:
```
snap connect fixgateway:serial-port snapd:plug
```

If you have spi or i2c devices you might need to make connections for those too.
<br>

To run the server:
```
fixgateway.server
```

To run the client:
```
fixgateway.client
```

