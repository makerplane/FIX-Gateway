# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/fixgw/\_\_init\_\_.py                        |        1 |        0 |        0 |        0 |    100% |           |
| src/fixgw/cfg.py                                 |      205 |       15 |      112 |        9 |     89% |213-\>229, 221-223, 237-\>234, 240, 271-279, 288-\>261, 296, 310-316, 341 |
| src/fixgw/database.py                            |      317 |        0 |       82 |        0 |    100% |           |
| src/fixgw/netfix/\_\_init\_\_.py                 |      253 |      207 |       70 |        0 |     14% |26-27, 47-57, 60, 66-81, 84-89, 92-114, 117-177, 182, 185, 188, 192-200, 203-205, 209-229, 234-237, 240-241, 244, 248, 251, 254, 257, 260, 263-276, 279-289, 292-295, 298-304, 307-309, 312-314, 317-331, 334-337, 340-343, 346-348 |
| src/fixgw/plugin.py                              |       46 |        4 |        0 |        0 |     91% |29-30, 69, 93 |
| src/fixgw/plugins/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| src/fixgw/plugins/annunciate.py                  |      104 |       22 |       46 |       12 |     77% |42, 50, 61, 71-72, 86, 93, 100-101, 117-118, 122, 135-\>143, 138, 143-\>151, 146, 157-166 |
| src/fixgw/plugins/canfix/\_\_init\_\_.py         |      115 |        9 |       30 |        4 |     91% |117-120, 135, 174-187, 197-\>204, 202-203, 205 |
| src/fixgw/plugins/canfix/mapping.py              |      262 |       64 |      120 |       10 |     77% |47, 122-\>124, 215-231, 236-284, 291-292, 310-317, 327-345, 360-\>364, 364-\>371, 368-369, 372-378, 394-395, 411, 433, 451, 469 |
| src/fixgw/plugins/compute.py                     |      574 |      177 |      310 |       49 |     66% |35-80, 88-134, 145, 149-154, 167, 188-202, 208-217, 228, 230, 244, 251-253, 274, 278-283, 299, 325, 329-334, 350, 377, 379, 392, 393-\>399, 400, 447, 451, 457, 491-492, 494-495, 497-498, 500-501, 503-504, 526, 528, 530, 532, 534, 540, 600-602, 625, 635, 637, 642, 644, 651, 653, 707, 709, 720, 722, 726, 744, 787-788, 793, 800, 815 |
| src/fixgw/plugins/dynon/\_\_init\_\_.py          |       72 |       24 |       18 |        2 |     60% |39-56, 59, 96, 97-\>100, 108-110, 113, 116-120, 123 |
| src/fixgw/plugins/garmin\_gnx375/\_\_init\_\_.py |      103 |       49 |       34 |        4 |     48% |79-117, 120, 127-135, 142-\>144, 144-\>exit, 154-\>exit, 163, 179-181, 184, 187-191, 194 |
| src/fixgw/plugins/netfix/\_\_init\_\_.py         |      421 |       74 |      158 |       20 |     78% |28-29, 77, 87-88, 144-\>146, 240-\>273, 252-\>255, 258-\>261, 264-\>267, 270-\>273, 315-316, 321-322, 414, 428-430, 442-445, 477-492, 495-515, 518-528, 531-533, 536-547, 553-\>555, 556, 558, 561-\>563, 564, 567-\>571, 569-\>571, 572-574, 576-577, 580-583 |
| src/fixgw/plugins/rtl\_433/\_\_init\_\_.py       |      166 |        0 |       80 |        0 |    100% |           |
| src/fixgw/plugins/stratux/\_\_init\_\_.py        |       61 |       45 |       12 |        0 |     22% |12-19, 23-55, 58, 63-65, 69, 72-76, 79 |
| src/fixgw/plugins/stratux/gdl90.py               |       33 |        1 |       14 |        1 |     96% |        36 |
| src/fixgw/plugins/xplane/\_\_init\_\_.py         |       77 |       33 |       30 |        3 |     50% |49-\>48, 68-83, 86-110, 113, 127, 129 |
| src/fixgw/quorum.py                              |        5 |        0 |        0 |        0 |    100% |           |
| src/fixgw/server.py                              |      267 |      183 |      108 |        1 |     28% |143-376, 380-407, 411-460, 465-466 |
| src/fixgw/status.py                              |       63 |       44 |       14 |        2 |     27% |24-25, 32-34, 37-53, 59-68, 72, 78-81, 86, 92-100, 104-106 |
| **TOTAL**                                        | **3145** |  **951** | **1238** |  **117** | **68%** |           |


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