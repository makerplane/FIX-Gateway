#  Copyright (c) 2019 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import io
import time
import yaml
import socket
import logging



def test_value_write(plugin,database):
    plugin.sock.sendall("@wALT;2500\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wALT;2500.0;00000\n"
    x = database.read("ALT")
    assert x == (2500.0, False, False, False, False, False)
    status = plugin.pl.get_status()
    assert status['Current Connections'] == 1
    assert status['Connection 0']['Client'][0] == '127.0.0.1'
    assert status['Connection 0']['Messages Received'] == 1
    assert status['Connection 0']['Messages Sent'] == 1


def test_subscription(plugin,database):
    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT\n"
    database.write("ALT", 3000)
    time.sleep(0.01)
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;3000.0;00000\n"
    status = plugin.pl.get_status()
    assert status['Current Connections'] == 1
    assert status['Connection 0']['Client'][0] == '127.0.0.1'
    assert status['Connection 0']['Messages Received'] == 1
    assert status['Connection 0']['Messages Sent'] == 2
    assert status['Connection 0']['Subscriptions'] == 1

def test_multiple_subscription_fail(plugin,database):
    """Test that we receive an error if we try to subscribe to the same
    point again"""
    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT\n"

    database.write("ALT", 3100)
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;3100.0;00000\n"

    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT!002\n"

def test_subscription_invalid_fixid(plugin):
    plugin.sock.sendall("@sNOPE\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sNOPE!001\n"

def test_unsubscribe_invalid_fixid(plugin):
    plugin.sock.sendall("@uNOPE\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@uNOPE!001\n"

def test_unsubscribe(plugin,database):
    plugin.sock.sendall("@sIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sIAS\n"
    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT\n"

    database.write("IAS", 120.0)
    database.write("ALT", 3100)
    res = plugin.sock.recv(1024).decode()
    assert res == "IAS;120.0;00000\nALT;3100.0;00000\n"

    plugin.sock.sendall("@uIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@uIAS\n"

    database.write("IAS", 125.0)
    database.write("ALT", 3200)
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;3200.0;00000\n"

def test_normal_write(plugin,database):
    plugin.sock.sendall("IAS;121.2;0000\n".encode())
    time.sleep(0.1)
    x = database.read("IAS")
    assert x == (121.2, False, False, False, False, False)

    plugin.sock.sendall("IAS;121.3;1000\n".encode())
    time.sleep(0.1)
    x = database.read("IAS")
    assert x == (121.3, True, False, False, False, False)

    plugin.sock.sendall("IAS;121.4;0100\n".encode())
    time.sleep(0.1)
    x = database.read("IAS")
    assert x == (121.4, False, False, True, False, False)

    plugin.sock.sendall("IAS;121.5;0010\n".encode())
    time.sleep(0.1)
    x = database.read("IAS")
    assert x == (121.5, False, False, False, True, False)

    plugin.sock.sendall("IAS;121.6;0001\n".encode())
    time.sleep(0.1)
    x = database.read("IAS")
    assert x == (121.6, False, False, False, False, True)

def test_read(plugin,database):
    database.write("IAS", 105.4)
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;00000\n"

    i = database.get_raw_item("IAS")
    i.annunciate = True
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;10000\n"

    i.bad = True
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;10100\n"

    i.fail = True
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;10110\n"

    i.secfail = True
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;10111\n"


    i.annunciate = False
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;00111\n"

    i.bad = False
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;00011\n"

    i.fail = False
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;00001\n"

    i.secfail = False
    plugin.sock.sendall("@rIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rIAS;105.4;00000\n"


def test_read_errors(plugin,database):
    plugin.sock.sendall("@rJUNKID\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rJUNKID!001\n"

    # Try it with a good key but bad aux
    plugin.sock.sendall("@rOILP1.lowWarned\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rOILP1.lowWarned!001\n"


def test_write_errors(plugin,database):
    plugin.sock.sendall("@wJUNKID;12.8\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wJUNKID!001\n"

    # Try a gibberish value
    plugin.sock.sendall("@wOILP1;43XXX\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wOILP1!003\n"

    # Try with non existent value
    plugin.sock.sendall("@wOILP1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wOILP1!003\n"

    # Try with almost non existent value
    plugin.sock.sendall("@wOILP1;\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wOILP1!003\n"

    # Try it with a good key but bad aux
    plugin.sock.sendall("@wOILP1.lowWarned;12.0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wOILP1.lowWarned!001\n"


def test_value_write_with_subscription(plugin,database):
    """Make sure we don't get a response to a value write on our subscriptions"""
    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT\n"

    plugin.sock.sendall("@sIAS\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sIAS\n"

    # writing both from database should give subscription returns
    database.write("IAS", 135.4)
    database.write("ALT", 4300)
    res = plugin.sock.recv(1024).decode()
    assert res == "IAS;135.4;00000\nALT;4300.0;00000\n"

    # writing over the socket should not create a callback
    plugin.sock.sendall("@wALT;3200\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wALT;3200.0;00000\n"

    database.write("IAS", 132.4)
    res = plugin.sock.recv(1024).decode()
    # we should only get the IAS one
    assert res == "IAS;132.4;00000\n"

    # using a normal write should do the same
    plugin.sock.sendall("ALT;3400;000\n".encode())
    database.write("IAS", 136.4)
    res = plugin.sock.recv(1024).decode()
    assert res == "IAS;136.4;00000\n"


def test_aux_write(plugin,database):
    plugin.sock.sendall("@wOILP1.lowWarn;12.5\n".encode())
    plugin.sock.recv(1024).decode()
    x = database.read("OILP1.lowWarn")
    assert x == 12.5


def test_aux_subscription(plugin,database):
    plugin.sock.sendall("@sOILP1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sOILP1\n"

    database.write("OILP1.lowWarn", 12.5)
    res = plugin.sock.recv(1024).decode()
    assert res == "OILP1.lowWarn;12.5\n"


def test_string_type(plugin):
    plugin.sock.sendall("@wACID;727WB\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wACID;727WB;00000\n"


def test_none_string(plugin,database):
    database.write("ACID", None)
    plugin.sock.sendall("@rACID\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rACID;;00000\n"


def test_list(plugin,database):
    # Get out list from the database and sort it
    db = database.listkeys()
    db.sort()
    # get list from the server, convert to list and sort
    plugin.sock.sendall("@l\n".encode())
    rdb = []
    # Need to loop over multiple responses
    # This is a hack, we should actually verify the headers
    # since they would also inform us
    # when to stop reading
    done = False
    data = ""
    while not done:
        try:
            data = data + plugin.sock.recv(1024).decode()
        except:
            done = True
    lines = data.split("\n")
    for line in lines:
        if len(line) > 4:
            a = line.split(";")
            rdb = rdb + a[2].split(",")

    rdb.sort()
    # join them back into a string and compare.  This is mostly
    # just to make it easy to see if it fails
    assert ",".join(db) == ",".join(rdb)

def test_tol_subscription(plugin):
    start = time.time()
    plugin.sock.sendall("@sROLL\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sROLL\n"

    plugin.sock.sendall("@wROLL;0.5\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wROLL;0.5;00000\n"

    res = plugin.sock.recv(1024).decode()
    assert res == "ROLL;0.5;01000\n"

    elapsed = time.time() - start
    assert elapsed > 0.2

def test_get_report(plugin,database):
    plugin.sock.sendall("@qAOA\n".encode())
    res = plugin.sock.recv(1024).decode()
    i = database.get_raw_item("AOA")
    s = "@qAOA;{};{};{};{};{};{};{}\n".format(
        i.description,
        i.typestring,
        i.min,
        i.max,
        i.units,
        i.tol,
        ",".join(i.aux.keys()),
    )
    assert res == s

def test_min_max(plugin,database):
    i = database.get_raw_item("ALT")
    val = str(i.min - 100)
    plugin.sock.sendall("@wALT;{}\n".format(val).encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wALT;{};00000\n".format(i.min)

    i = database.get_raw_item("ALT")
    val = str(i.max + 100)
    plugin.sock.sendall("@wALT;{}\n".format(val).encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@wALT;{};00000\n".format(i.max)


def test_flags(plugin):
    plugin.sock.sendall("@fALT;a;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;a;1\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;10000\n"

    plugin.sock.sendall("@fALT;a;0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;a;0\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res ==  "@rALT;0.0;00000\n"


    plugin.sock.sendall("@fALT;b;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;b;1\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00100\n"

    plugin.sock.sendall("@fALT;b;0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;b;0\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00000\n"


    plugin.sock.sendall("@fALT;f;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;f;1\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00010\n"

    plugin.sock.sendall("@fALT;f;0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;f;0\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00000\n"


    plugin.sock.sendall("@fALT;s;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;s;1\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00001\n"

    plugin.sock.sendall("@fALT;s;0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;s;0\n"

    plugin.sock.sendall("@rALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@rALT;0.0;00000\n"

    plugin.sock.sendall("@fALT;o;0\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fALT;o;0\n"

def test_subscribe_flags(plugin,database):
    """Test that writing just the flags will trigger a subscription response"""
    plugin.sock.sendall("@sALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@sALT\n"

    i = database.get_raw_item("ALT")
    i.annunciate = True
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;10000\n"

    i.annunciate = False
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00000\n"

    i.bad = True
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00100\n"

    i.bad = False
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00000\n"

    i.fail = True
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00010\n"

    i.fail = False
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00000\n"

    i.secfail = True
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00001\n"

    i.secfail = False
    res = plugin.sock.recv(1024).decode()
    assert res == "ALT;0.0;00000\n"


def test_unknown_command(plugin):
    plugin.sock.sendall("@oALT\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@oALT!004\n"


def test_status_command(plugin):
    plugin.sock.sendall("@xstatus\n".encode())
    res = plugin.sock.recv(1024).decode()
    # This should be improved
    # Not sure how to init the status so we get actual data
    assert '@xstatus;' in res

def test_kill_command(plugin):
    plugin.sock.sendall("@xkill\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == '@xkill\n'

def test_bad_command(plugin):
    plugin.sock.sendall("@xbad\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == '@xbad!001'

def test_set_flag_for_bad_id(plugin):
    plugin.sock.sendall("@fNOPE;a;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == '@fN!001\n'

def test_flag_with_invalid_flag(plugin):
    plugin.sock.sendall("@fALT;n;1\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fA!002\n"

def test_flag_with_invalid_setting(plugin):
    plugin.sock.sendall("@fALT;a;2\n".encode())
    res = plugin.sock.recv(1024).decode()
    assert res == "@fA!003\n"

    # def test_decimal_places(self):
    #     pass

def test_read_non_tuple_fixid(plugin,database):
    database.write("IAS.Min", "20.5")
    plugin.sock.sendall("@rIAS.Min\n".encode())
    res = plugin.sock.recv(1024).decode()
    a = res.split(';')
    assert a[1] == "20.5\n"

def test_send_invalid_value_update(plugin,caplog):
    with caplog.at_level(logging.DEBUG):
        plugin.sock.sendall("IAS;10\n".encode())
        time.sleep(0.1)
        assert 'Bad Frame IAS;10 from 127.0.0.1' in caplog.text
        assert 'Problem with input IAS;10: list index out of range' in caplog.text

def test_send_invalid_value_update2(plugin,caplog):
    with caplog.at_level(logging.DEBUG):
        plugin.sock.sendall("IAS;10;10;10;10;10\n".encode())
        time.sleep(0.1)
        assert 'Bad Frame IAS;10;10;10;10;10 from 127.0.0.1' in caplog.text
        assert 'Problem with input IAS;10;10;10;10;10: string index out of range' in caplog.text        


