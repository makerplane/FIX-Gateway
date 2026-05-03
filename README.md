# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/fixgw/\_\_init\_\_.py                                        |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/cfg.py                                                 |      205 |        0 |      112 |        0 |    100% |           |
| src/fixgw/client/\_\_init\_\_.py                                 |       52 |        6 |       22 |        5 |     85% |35, 82, 94, 95-\>98, 99-101, 109 |
| src/fixgw/client/command.py                                      |      167 |      118 |       52 |        4 |     27% |26-38, 52-83, 89, 93-98, 102-113, 121-148, 174-186, 191-204, 208-215, 219, 223, 226 |
| src/fixgw/client/common.py                                       |       49 |       36 |       24 |        4 |     26% |28-52, 54-60, 63-\>75, 68-72 |
| src/fixgw/client/connection.py                                   |        6 |        2 |        0 |        0 |     67% |     29-30 |
| src/fixgw/client/dbItemDialog.py                                 |      149 |       75 |        6 |        2 |     49% |34-37, 47-58, 61-72, 92-108, 158-196 |
| src/fixgw/client/gui.py                                          |       24 |        8 |        2 |        1 |     65% | 36-44, 51 |
| src/fixgw/client/simulate.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/client/statusModel.py                                  |       44 |        9 |        4 |        1 |     79% |45-\>exit, 51-57, 70, 73 |
| src/fixgw/client/table.py                                        |       66 |       56 |        4 |        0 |     14% |28-32, 37-96, 99-102 |
| src/fixgw/client/ui/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/client/ui/itemDialog\_ui.py                            |       40 |        0 |        0 |        0 |    100% |           |
| src/fixgw/client/ui/main\_ui.py                                  |       53 |       49 |        0 |        0 |      8% |14-60, 63-75 |
| src/fixgw/database.py                                            |      316 |        0 |       82 |        0 |    100% |           |
| src/fixgw/netfix/QtDb.py                                         |      147 |        0 |       10 |        0 |    100% |           |
| src/fixgw/netfix/\_\_init\_\_.py                                 |      250 |        0 |       70 |        0 |    100% |           |
| src/fixgw/netfix/db.py                                           |      434 |        0 |      110 |        0 |    100% |           |
| src/fixgw/plugin.py                                              |       43 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/X728/\_\_init\_\_.py                           |       71 |       71 |       18 |        0 |      0% |    21-109 |
| src/fixgw/plugins/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/annunciate.py                                  |      104 |        0 |       46 |        0 |    100% |           |
| src/fixgw/plugins/canfix/\_\_init\_\_.py                         |      115 |        0 |       30 |        0 |    100% |           |
| src/fixgw/plugins/canfix/mapping.py                              |      262 |        0 |      120 |        0 |    100% |           |
| src/fixgw/plugins/command.py                                     |      125 |        0 |       30 |        0 |    100% |           |
| src/fixgw/plugins/compute.py                                     |      571 |        0 |      308 |        0 |    100% |           |
| src/fixgw/plugins/data\_playback/\_\_init\_\_.py                 |       68 |        0 |       22 |        0 |    100% |           |
| src/fixgw/plugins/data\_recorder/\_\_init\_\_.py                 |       95 |        0 |       30 |        0 |    100% |           |
| src/fixgw/plugins/db\_persister/\_\_init\_\_.py                  |       59 |        0 |        8 |        0 |    100% |           |
| src/fixgw/plugins/demo/\_\_init\_\_.py                           |       66 |        0 |       32 |        2 |     98% |673-\>683, 676-\>674 |
| src/fixgw/plugins/dimmer.py                                      |       10 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/dynon/\_\_init\_\_.py                          |       71 |        0 |       16 |        0 |    100% |           |
| src/fixgw/plugins/fgfs/\_\_init\_\_.py                           |      151 |        0 |       44 |        3 |     98% |88-\>exit, 121-\>119, 127-\>125 |
| src/fixgw/plugins/garmin\_gnx375/\_\_init\_\_.py                 |      103 |        0 |       34 |        0 |    100% |           |
| src/fixgw/plugins/gpsd/\_\_init\_\_.py                           |       55 |        0 |       10 |        0 |    100% |           |
| src/fixgw/plugins/grand\_rapids\_eis/\_\_init\_\_.py             |      154 |        0 |       20 |        1 |     99% |   94-\>43 |
| src/fixgw/plugins/ifly/\_\_init\_\_.py                           |       64 |        0 |       24 |        0 |    100% |           |
| src/fixgw/plugins/mavlink/Mav.py                                 |      310 |        0 |      160 |       32 |     93% |105-\>108, 108-\>115, 115-\>117, 117-\>120, 167-\>170, 177-\>183, 183-\>189, 189-\>exit, 206-\>exit, 211-\>exit, 230-\>237, 237-\>exit, 257-\>270, 270-\>exit, 276-\>exit, 373-\>exit, 394-\>exit, 418-\>exit, 459-\>461, 461-\>471, 468-\>471, 474-\>479, 488-\>exit, 506-\>517, 509-\>506, 517-\>exit, 524-\>exit, 542-\>549, 549-\>552, 557-\>560, 560-\>exit, 565-\>exit |
| src/fixgw/plugins/mavlink/\_\_init\_\_.py                        |       84 |        0 |       12 |        0 |    100% |           |
| src/fixgw/plugins/megasquirt/\_\_init\_\_.py                     |       35 |        0 |        6 |        0 |    100% |           |
| src/fixgw/plugins/megasquirt/megasquirt.py                       |       49 |        0 |       18 |        1 |     99% |   18-\>20 |
| src/fixgw/plugins/megasquirt/tables.py                           |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/mgl/\_\_init\_\_.py                            |       39 |        0 |       18 |        2 |     96% |45-\>47, 49-\>53 |
| src/fixgw/plugins/mgl/rdac.py                                    |      134 |        0 |       64 |        2 |     99% |91-\>100, 169-\>175 |
| src/fixgw/plugins/mgl/tables.py                                  |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/mgl\_serial/\_\_init\_\_.py                    |       89 |        0 |       28 |        0 |    100% |           |
| src/fixgw/plugins/netfix/\_\_init\_\_.py                         |      418 |       10 |      158 |       11 |     96% |140-\>142, 236-\>269, 248-\>251, 254-\>257, 260-\>263, 266-\>269, 317-318, 410, 424-426, 438-441, 573, 577-\>exit, 578-\>exit |
| src/fixgw/plugins/quorum/\_\_init\_\_.py                         |       52 |        0 |       14 |        0 |    100% |           |
| src/fixgw/plugins/rais/\_\_init\_\_.py                           |       47 |        0 |        8 |        0 |    100% |           |
| src/fixgw/plugins/rpi\_bmp085/Adafruit\_BMP/BMP085.py            |      139 |      139 |       12 |        0 |      0% |    22-215 |
| src/fixgw/plugins/rpi\_bmp085/Adafruit\_BMP/\_\_init\_\_.py      |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/rpi\_bmp085/\_\_init\_\_.py                    |       55 |       55 |        6 |        0 |      0% |    24-116 |
| src/fixgw/plugins/rpi\_bno055/Adafruit\_BNO055/BNO055.py         |      351 |      351 |       48 |        0 |      0% |    23-726 |
| src/fixgw/plugins/rpi\_bno055/Adafruit\_BNO055/\_\_init\_\_.py   |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/rpi\_bno055/\_\_init\_\_.py                    |       79 |       79 |       16 |        0 |      0% |    24-138 |
| src/fixgw/plugins/rpi\_button/\_\_init\_\_.py                    |       51 |       51 |       10 |        0 |      0% |    24-116 |
| src/fixgw/plugins/rpi\_mcp3008/Adafruit\_MCP3008/MCP3008.py      |       33 |       33 |        6 |        0 |      0% |     22-96 |
| src/fixgw/plugins/rpi\_mcp3008/Adafruit\_MCP3008/\_\_init\_\_.py |        1 |        1 |        0 |        0 |      0% |         1 |
| src/fixgw/plugins/rpi\_mcp3008/\_\_init\_\_.py                   |       72 |       72 |        8 |        0 |      0% |    24-178 |
| src/fixgw/plugins/rpi\_rotary\_encoder/\_\_init\_\_.py           |       66 |       66 |       16 |        0 |      0% |    24-162 |
| src/fixgw/plugins/rpi\_virtualwire/\_\_init\_\_.py               |       75 |       75 |       12 |        0 |      0% |    24-139 |
| src/fixgw/plugins/rpi\_virtualwire/virtualwire/\_\_init\_\_.py   |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/rpi\_virtualwire/virtualwire/virtualwire.py    |      184 |      184 |       78 |        0 |      0% |    14-376 |
| src/fixgw/plugins/rtl\_433/\_\_init\_\_.py                       |      166 |        0 |       80 |        0 |    100% |           |
| src/fixgw/plugins/shadin/\_\_init\_\_.py                         |       73 |        0 |       20 |        0 |    100% |           |
| src/fixgw/plugins/skel.py                                        |       35 |        0 |        6 |        0 |    100% |           |
| src/fixgw/plugins/stratux/\_\_init\_\_.py                        |       61 |        0 |       12 |        1 |     99% |   48-\>23 |
| src/fixgw/plugins/stratux/gdl90.py                               |       33 |        0 |       14 |        0 |    100% |           |
| src/fixgw/plugins/strom\_pi/\_\_init\_\_.py                      |      116 |        0 |       16 |        3 |     98% |113-\>117, 117-\>131, 118-\>131 |
| src/fixgw/plugins/system.py                                      |       93 |        0 |       48 |        0 |    100% |           |
| src/fixgw/plugins/test.py                                        |       27 |        0 |        2 |        0 |    100% |           |
| src/fixgw/plugins/xplane/\_\_init\_\_.py                         |       86 |        0 |       34 |        2 |     98% |50-\>49, 94-\>113 |
| src/fixgw/quorum.py                                              |        5 |        0 |        0 |        0 |    100% |           |
| src/fixgw/server.py                                              |      265 |        2 |      108 |        1 |     99% |   169-170 |
| src/fixgw/status.py                                              |       63 |        0 |       14 |        0 |    100% |           |
| src/fixgw/version.py                                             |        2 |        0 |        0 |        0 |    100% |           |
| **TOTAL**                                                        | **7580** | **1548** | **2342** |   **78** | **81%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/makerplane/FIX-Gateway/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/makerplane/FIX-Gateway/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fmakerplane%2FFIX-Gateway%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.