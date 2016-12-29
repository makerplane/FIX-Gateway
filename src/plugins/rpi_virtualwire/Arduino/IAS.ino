/*
    Takes an input on the arduino pro from analog input 3
    and outputs it using 433mhz tranceiver
 */
#include <VirtualWire.h>
#include <Thermistor.h>
Thermistor temp(4);
#define A_INPUT A3
#undef int
#undef abs
#undef double
#undef float
#undef round
float airspeed_kn;
float oat;
char ias_String[24];
char oat_String[24];
char msg[27];
int initval;
const char *ias_Name = "ias=";
const char *oat_Name = "oat=";

void setup () {
  pinMode(13,OUTPUT);
  pinMode(3,OUTPUT);
  digitalWrite(3,HIGH);
  analogReference (DEFAULT);    // or EXTERNAL or INTERNAL
  for (int i = 0; i < 8; i++)
    analogRead (A_INPUT), delay (120);
  initval = 0;
  for (int i = 0; i < 8; i++)
    initval += analogRead (A_INPUT), delay (120);
  initval = (initval >> 3) + 1;
  vw_set_ptt_inverted(true);
  vw_set_tx_pin(2);
  vw_setup(2000);	 // Bits per sec
}

void loop () {
#define ABSOLUTE_0_KELVIN 273.16f
#define PRESSURE_SEA_LEVEL 101325.0f
  int currval = 0;
  for (int i = 0; i < 8; i++)
    currval += analogRead (A_INPUT), delay (10);
  currval >>= 3;
  if (currval < initval)
    currval = initval;
  float pitotpressure = 5000.0f * ((currval - initval) / 1024.0f) + PRESSURE_SEA_LEVEL;    // differential pressure in Pa, 1 V/kPa, max 3920 Pa
  float ambientpressure = PRESSURE_SEA_LEVEL;
  float temperature = 20.0f + ABSOLUTE_0_KELVIN;
  float airspeed_ms = get_air_speed (pitotpressure, ambientpressure, temperature);  // speed in m/s
  airspeed_kn = airspeed_ms * 3600 / 1852.0;  // convert to knots
  oat = temp.getTemp();
  send_Data ();
  }

  float get_air_speed (float frontpressure, float externalpressure, float temperature)
{
#define UNIVERSAL_GAS_CONSTANT 8.3144621f
#define DRY_AIR_MOLAR_MASS 0.0289644f

  float density = (externalpressure * DRY_AIR_MOLAR_MASS) / (temperature * UNIVERSAL_GAS_CONSTANT);
  return sqrt ((2 * (frontpressure - externalpressure)) / density);
}

/* ********************** 433 mhz interface ********************** */

void send_Data()
{
  digitalWrite(13,HIGH);
  dtostrf(airspeed_kn, 5, 1, ias_String);
  dtostrf(oat, 4, 1,oat_String);
  //Combining to one string
  sprintf(msg, "%s, %s", ias_String, oat_String);
  vw_send((uint8_t *)msg, strlen(msg));
  vw_wait_tx();
  digitalWrite(13,LOW);
}

