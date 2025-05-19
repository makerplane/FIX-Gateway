# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/fixgw/\_\_init\_\_.py                                        |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/cfg.py                                                 |      205 |       15 |      112 |        9 |     89% |213->229, 221-223, 237->234, 240, 271-279, 288->261, 296, 310-316, 341 |
| src/fixgw/client/\_\_init\_\_.py                                 |       41 |       41 |       12 |        0 |      0% |    21-100 |
| src/fixgw/client/command.py                                      |      158 |      158 |       48 |        0 |      0% |    17-216 |
| src/fixgw/client/common.py                                       |       48 |       48 |       24 |        0 |      0% |     21-73 |
| src/fixgw/client/connection.py                                   |        6 |        6 |        0 |        0 |      0% |     20-30 |
| src/fixgw/client/dbItemDialog.py                                 |      149 |      149 |        6 |        0 |      0% |    21-196 |
| src/fixgw/client/gui.py                                          |       22 |       22 |        0 |        0 |      0% |     21-54 |
| src/fixgw/client/simulate.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/client/statusModel.py                                  |       39 |       39 |        4 |        0 |      0% |     18-68 |
| src/fixgw/client/table.py                                        |       66 |       66 |        4 |        0 |      0% |    18-102 |
| src/fixgw/client/ui/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/client/ui/itemDialog\_ui.py                            |       40 |       40 |        0 |        0 |      0% |      9-62 |
| src/fixgw/client/ui/main\_ui.py                                  |       53 |       53 |        0 |        0 |      0% |      9-75 |
| src/fixgw/database.py                                            |      308 |       36 |       80 |        3 |     89% |44-46, 85-89, 105-106, 139, 168-169, 173-174, 187-188, 200-201, 212, 215-216, 220-221, 233-234, 246-247, 272-273, 284, 315-317, 351->354, 361-362, 420 |
| src/fixgw/netfix/QtDb.py                                         |      152 |      152 |       10 |        0 |      0% |    21-242 |
| src/fixgw/netfix/\_\_init\_\_.py                                 |      253 |      207 |       70 |        0 |     14% |26-27, 47-57, 60, 66-81, 84-89, 92-114, 117-177, 182, 185, 188, 192-200, 203-205, 209-229, 234-237, 240-241, 244, 248, 251, 254, 257, 260, 263-276, 279-289, 292-295, 298-304, 307-309, 312-314, 317-331, 334-337, 340-343, 346-348 |
| src/fixgw/netfix/db.py                                           |      434 |      434 |      110 |        0 |      0% |    20-585 |
| src/fixgw/plugin.py                                              |       46 |        4 |        0 |        0 |     91% |29-30, 69, 93 |
| src/fixgw/plugins/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/annunciate.py                                  |      104 |      104 |       46 |        0 |      0% |    22-188 |
| src/fixgw/plugins/canfix/\_\_init\_\_.py                         |      115 |        9 |       30 |        4 |     91% |117-120, 135, 174-187, 197->204, 202-203, 205 |
| src/fixgw/plugins/canfix/mapping.py                              |      262 |       64 |      120 |       10 |     77% |47, 122->124, 215-231, 236-284, 291-292, 310-317, 327-345, 360->364, 364->371, 368-369, 372-378, 394-395, 411, 433, 451, 469 |
| src/fixgw/plugins/command.py                                     |      125 |      125 |       30 |        0 |      0% |    19-183 |
| src/fixgw/plugins/compute.py                                     |      498 |      171 |      288 |       43 |     64% |34-79, 87-133, 144, 148-153, 166, 187-201, 207-216, 227, 229, 243, 250-252, 273, 277-282, 298, 324, 328-333, 349, 376, 378, 391, 392->398, 399, 446, 450, 456, 490-491, 493-494, 496-497, 499-500, 502-503, 525, 527, 529, 531, 533, 539, 599-601, 624, 634, 636, 641, 643, 650, 652, 679-680, 685, 692, 707 |
| src/fixgw/plugins/data\_playback/\_\_init\_\_.py                 |       68 |       68 |       22 |        0 |      0% |      1-95 |
| src/fixgw/plugins/data\_recorder/\_\_init\_\_.py                 |       93 |       93 |       32 |        0 |      0% |     1-176 |
| src/fixgw/plugins/db\_persister/\_\_init\_\_.py                  |       58 |       58 |        8 |        0 |      0% |    22-115 |
| src/fixgw/plugins/demo/\_\_init\_\_.py                           |       66 |       66 |       32 |        0 |      0% |    26-709 |
| src/fixgw/plugins/dimmer.py                                      |       10 |       10 |        0 |        0 |      0% |     22-37 |
| src/fixgw/plugins/dynon/\_\_init\_\_.py                          |       72 |       72 |       18 |        0 |      0% |    21-123 |
| src/fixgw/plugins/fgfs/\_\_init\_\_.py                           |      151 |      151 |       44 |        0 |      0% |    19-238 |
| src/fixgw/plugins/gpsd/\_\_init\_\_.py                           |       55 |       55 |       10 |        0 |      0% |     21-88 |
| src/fixgw/plugins/grand\_rapids\_eis/\_\_init\_\_.py             |      154 |      154 |       20 |        0 |      0% |    22-192 |
| src/fixgw/plugins/ifly/\_\_init\_\_.py                           |       64 |       64 |       24 |        0 |      0% |    18-136 |
| src/fixgw/plugins/mavlink/Mav.py                                 |      310 |      310 |      160 |        0 |      0% |    18-639 |
| src/fixgw/plugins/mavlink/\_\_init\_\_.py                        |       84 |       84 |       12 |        0 |      0% |    28-138 |
| src/fixgw/plugins/megasquirt/\_\_init\_\_.py                     |       35 |       35 |        6 |        0 |      0% |     20-72 |
| src/fixgw/plugins/megasquirt/megasquirt.py                       |       49 |       49 |       18 |        0 |      0% |      2-73 |
| src/fixgw/plugins/megasquirt/tables.py                           |        1 |        1 |        0 |        0 |      0% |         1 |
| src/fixgw/plugins/mgl/\_\_init\_\_.py                            |       39 |       39 |       18 |        0 |      0% |     20-83 |
| src/fixgw/plugins/mgl/rdac.py                                    |      134 |      134 |       64 |        0 |      0% |     2-245 |
| src/fixgw/plugins/mgl/tables.py                                  |        1 |        1 |        0 |        0 |      0% |         1 |
| src/fixgw/plugins/mgl\_serial/\_\_init\_\_.py                    |       89 |       89 |       28 |        0 |      0% |    21-134 |
| src/fixgw/plugins/netfix/\_\_init\_\_.py                         |      421 |       74 |      158 |       20 |     78% |28-29, 77, 87-88, 144->146, 240->273, 252->255, 258->261, 264->267, 270->273, 315-316, 321-322, 414, 428-430, 442-445, 477-492, 495-515, 518-528, 531-533, 536-547, 553->555, 556, 558, 561->563, 564, 567->571, 569->571, 572-574, 576-577, 580-583 |
| src/fixgw/plugins/quorum/\_\_init\_\_.py                         |       52 |       52 |       14 |        0 |      0% |    27-111 |
| src/fixgw/plugins/rais/\_\_init\_\_.py                           |       47 |       47 |        8 |        0 |      0% |     23-80 |
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
| src/fixgw/plugins/shadin/\_\_init\_\_.py                         |       73 |       73 |       20 |        0 |      0% |    22-118 |
| src/fixgw/plugins/skel.py                                        |       35 |       35 |        6 |        0 |      0% |     24-86 |
| src/fixgw/plugins/stratux/\_\_init\_\_.py                        |       61 |       61 |       12 |        0 |      0% |      1-79 |
| src/fixgw/plugins/stratux/gdl90.py                               |       33 |       33 |       14 |        0 |      0% |      1-49 |
| src/fixgw/plugins/strom\_pi/\_\_init\_\_.py                      |      115 |      115 |       16 |        0 |      0% |    21-164 |
| src/fixgw/plugins/system.py                                      |       93 |       93 |       48 |        0 |      0% |    24-140 |
| src/fixgw/plugins/test.py                                        |       27 |       27 |        2 |        0 |      0% |     19-54 |
| src/fixgw/plugins/xplane/\_\_init\_\_.py                         |       77 |       33 |       30 |        3 |     50% |49->48, 68-83, 86-110, 113, 127, 129 |
| src/fixgw/quorum.py                                              |        5 |        0 |        0 |        0 |    100% |           |
| src/fixgw/server.py                                              |      267 |      224 |      108 |        1 |     13% |23-24, 66-73, 80-124, 128, 143-376, 380-407, 411-460, 465-466 |
| src/fixgw/status.py                                              |       63 |        0 |       14 |        0 |    100% |           |
| src/fixgw/version.py                                             |        2 |        0 |        0 |        0 |    100% |           |
|                                                        **TOTAL** | **7301** | **5449** | **2252** |   **93** | **26%** |           |


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