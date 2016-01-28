# Installation Notes
The installtion has been tested on Fedora 22 and OS X 10.11. 

## Fedora 22 with Python 2.7 or 3.5
 install the packages PyQt4, python3-PyQt4 from default repositories

## OSX 10.11 using Mac Ports Python 3.4
prerequisite: MacPorts

    sudo port selfupdate
    sudo port install python34 py34-pyqt4
    sudo port select --set python python34 

Caveat: pip-3.4 freeze will _not_ list pyqt4. But it is available, though:

    python -c 'import PyQt4'
