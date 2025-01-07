# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/fixgw/\_\_init\_\_.py                                        |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/cfg.py                                                 |       72 |       28 |       62 |       13 |     57% |8-10, 23->102, 27, 31, 38, 41-50, 56, 68, 71-84, 88->62, 92-98 |
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
| src/fixgw/database.py                                            |      309 |       38 |       80 |        3 |     89% |46-48, 86-91, 107-108, 141, 170-171, 175-176, 189-190, 202-203, 214, 217-218, 222-223, 235-236, 248-249, 274-275, 286, 317-319, 356->359, 366-367, 424-425 |
| src/fixgw/netfix/QtDb.py                                         |      152 |      152 |       10 |        0 |      0% |    21-242 |
| src/fixgw/netfix/\_\_init\_\_.py                                 |      253 |      207 |       70 |        0 |     14% |26-27, 47-57, 60, 66-81, 84-89, 92-114, 117-177, 182, 185, 188, 192-200, 203-205, 209-229, 234-237, 240-241, 244, 248, 251, 254, 257, 260, 263-276, 279-289, 292-295, 298-304, 307-309, 312-314, 317-331, 334-337, 340-343, 346-348 |
| src/fixgw/netfix/db.py                                           |      434 |      434 |      110 |        0 |      0% |    20-585 |
| src/fixgw/plugin.py                                              |       45 |        5 |        0 |        0 |     89% |29-30, 65, 68, 92 |
| src/fixgw/plugins/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/annunciate.py                                  |      104 |      104 |       46 |        0 |      0% |    22-188 |
| src/fixgw/plugins/canfix/\_\_init\_\_.py                         |       98 |       37 |       30 |        5 |     62% |63-84, 92-101, 107-108, 117, 150-163, 176-177, 179, 182-188 |
| src/fixgw/plugins/canfix/mapping.py                              |      224 |       98 |       98 |       14 |     53% |43-45, 96->98, 104->106, 136-137, 146-147, 167-168, 173-175, 179-194, 199-244, 251, 261, 268-273, 282-297, 312->316, 316->323, 320-321, 324-330, 342-347, 350-376, 385, 394->exit |
| src/fixgw/plugins/command.py                                     |      125 |      125 |       30 |        0 |      0% |    19-183 |
| src/fixgw/plugins/compute.py                                     |      498 |      171 |      288 |       43 |     64% |34-80, 88-135, 146, 151-156, 169, 190-207, 213-224, 235, 237, 253, 260-262, 283, 288-293, 309, 335, 340-345, 361, 388, 391, 404, 405->411, 412, 459, 463, 469, 503-504, 506-507, 509-510, 512-513, 515-516, 538, 540, 542, 544, 546, 552, 612-614, 637, 647, 649, 654, 656, 663, 665, 692-693, 698, 705, 720 |
| src/fixgw/plugins/data\_playback/\_\_init\_\_.py                 |       68 |       68 |       22 |        0 |      0% |      1-95 |
| src/fixgw/plugins/data\_recorder/\_\_init\_\_.py                 |       92 |       92 |       30 |        0 |      0% |     1-172 |
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
| src/fixgw/plugins/megasquirt/\_\_init\_\_.py                     |       36 |       36 |        6 |        0 |      0% |     20-72 |
| src/fixgw/plugins/megasquirt/megasquirt.py                       |       49 |       49 |       18 |        0 |      0% |      2-73 |
| src/fixgw/plugins/megasquirt/tables.py                           |        1 |        1 |        0 |        0 |      0% |         1 |
| src/fixgw/plugins/mgl/\_\_init\_\_.py                            |       40 |       40 |       18 |        0 |      0% |     20-83 |
| src/fixgw/plugins/mgl/rdac.py                                    |      134 |      134 |       64 |        0 |      0% |     2-245 |
| src/fixgw/plugins/mgl/tables.py                                  |        1 |        1 |        0 |        0 |      0% |         1 |
| src/fixgw/plugins/mgl\_serial/\_\_init\_\_.py                    |       89 |       89 |       28 |        0 |      0% |    21-134 |
| src/fixgw/plugins/netfix/\_\_init\_\_.py                         |      421 |      112 |      158 |       27 |     69% |28-29, 78, 88-89, 100-101, 114-121, 127-129, 131-132, 134-135, 140, 145->147, 201, 211-212, 221-222, 226, 238, 241->274, 253->256, 259->262, 265->268, 271->274, 278-280, 316-317, 322-323, 415, 429-431, 439-446, 463-472, 479-494, 497-517, 520-530, 533-535, 538-549, 555->557, 558, 560, 563->565, 566, 569->573, 571->573, 574-576, 578-579, 582-585, 591 |
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
| src/fixgw/plugins/shadin/\_\_init\_\_.py                         |       73 |       73 |       20 |        0 |      0% |    22-118 |
| src/fixgw/plugins/skel.py                                        |       35 |       35 |        6 |        0 |      0% |     24-86 |
| src/fixgw/plugins/stratux/\_\_init\_\_.py                        |       61 |       61 |       12 |        0 |      0% |      1-79 |
| src/fixgw/plugins/stratux/gdl90.py                               |       33 |       33 |       14 |        0 |      0% |      1-49 |
| src/fixgw/plugins/strom\_pi/\_\_init\_\_.py                      |      115 |      115 |       16 |        0 |      0% |    21-164 |
| src/fixgw/plugins/system.py                                      |       93 |       93 |       48 |        0 |      0% |    24-140 |
| src/fixgw/plugins/test.py                                        |       27 |       27 |        2 |        0 |      0% |     19-54 |
| src/fixgw/plugins/xplane/\_\_init\_\_.py                         |       77 |       77 |       30 |        0 |      0% |    21-129 |
| src/fixgw/quorum.py                                              |        5 |        0 |        0 |        0 |    100% |           |
| src/fixgw/server.py                                              |      267 |      267 |      108 |        0 |      0% |    18-461 |
| src/fixgw/status.py                                              |       58 |       40 |       12 |        1 |     27% |31-34, 37-50, 55-60, 65, 69, 75-78, 82, 86-94, 98-100 |
| src/fixgw/version.py                                             |        2 |        2 |        0 |        0 |      0% |       1-3 |
|                                                        **TOTAL** | **6943** | **5695** | **2096** |  **106** | **19%** |           |


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