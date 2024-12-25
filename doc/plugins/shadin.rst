====================
Shadin Plugin
====================

Implements Shadin protocol. Currently only decodes fuel related messages supported by FC-10 fuel computer

If your messages start with letter 'Z', try to change the protocol on your unit to Shadin Generic, or modify the plugin.

Example data
------------
GA---
GB---
GC---
GD ----
GE ----
GF --
GG --
GH---
GI---
GJ --
GK ---
GL---
GM0000
GN00000
GO0000
GP00000
GQ000
GR051

Protocol description
--------------------
SHADIN “G” FORMAT
<STX> GA012<CR><LF> GB345<CR><LF> GC678<CR><LF> GD<+/->9012<CR><LF> GE<+/->3456<CR><LF> GF<+/->78<CR><LF> GG<+/->90<CR><LF> GH123<CR><LF> GI456<CR><LF> GJ<+/->78<CR><LF> GK<+/->901<CR><LF> GL234<CR><LF> GM5678<CR><LF>† GN90123<CR><LF>† GO4567<CR><LF> GP89012<CR><LF> GQ001<CR><LF>
GR6789.0<CR><LF>† Ga<+/->1234<CR><LF> Gb56.78<CR><LF> G*901<CR><LF> <ETX>
"GA" (ASCII characters); "012" represents indicated Air Speed (knots)
"GB" (ASCII characters); "345" represents true Air Speed (knots)
"GC" (ASCII characters); "678" represents Mach Speed (thousandths)
"GD" (ASCII characters); sign; "9012" represents pressure altitude (tens of feet) "GE" (ASCII characters); sign; "3456" represents density altitude (tens of feet) "GF" (ASCII characters); sign; "78" represents outside air temperature (Celsius) "GG" (ASCII characters); sign; "90" represents true air temperature (Celsius) "GH" (ASCII characters); "123" represents wind direction (degrees from north) "GI" (ASCII characters); "456" represents wind speed (knots)
"GJ" (ASCII characters); sign; "78" represents rate of turn (degrees per second)
"GK" (ASCII characters); sign; "901" represents vertical speed (tens of ft/minute)
"GL" (ASCII characters); "234" represents heading (degrees from north)
"GM" (ASCII characters); "5678" represents fuel flow, right (Twin only) (tenths gallons/hour) "GN" (ASCII characters); "90123" represents fuel used, right (Twin only) (tenths gallons) "GO" (ASCII characters); "4567" represents fuel flow, left (or Single) (tenths gallons/hour) "GP" (ASCII characters); "89012" represents fuel used, left (or Single) (tenths gallons)
"GQ" (ASCII characters); "001" represents error log/reason indicator (001 = temp. sensor error, 000 = no errors)
"GR" (ASCII characters); "6789.0" represents fuel remaining (gallons)
"Ga" (ASCII characters); sign; "12.34" represents barometric corrected altitude (tens of feet) "Gb" (ASCII characters); "56.78" represents current barometric pressure setting (inches Hg) "G*" (ASCII characters); "901" represents checksum
Where:
<STX> start-transmit character (0x02)
<CR> carriage-return character (0x0d)
<LF> line-feed character (0x0a)
<+/-> sign indicator (0x2b["+"] or 0x2d["-"]) <ETX> end-transmit character (0x03)
