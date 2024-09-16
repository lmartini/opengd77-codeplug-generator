# opengd77-codeplug-generator

Codeplug Generator for OpenGD77 CPS

This program will generate .CSV files to import into an opengd77 codeplug using the openGD77 CPS.
I created this program to make it easier for travelers to load all the repeaters along their route into a codeplug with minimal effort.
It is recommended that the csv "Append" function be used to append the new channels and zones to an existing codeplug. Also make sure you use the latest CPS version.

How does this work?

When you run the codeplug generator, it will talk to radioid.net to fetch all repeater details for one or more target areas defined by  city/state/country. It will then lookup the repeater location in brandmeister.network which is very slow due to the lack of APIs. If the location is not found, or the repeater is not a BM repeater, it will use map data from radioid.com instead. 

This will allow you to set the "sort by distance" option on your openGD77 radio, and if the position is currently set by GPS , it will be very convenient to quickly find a local repeater.

The program includes Brandmeister, TGIF, ADN, and DMR+ network by default.

You must have a TG list named after those default networks or the TG list in the channel will be blank and you will have trouble using it.
You should have the following Tg lists defined before importing the generated codeplug into your CPS:
BM
TGIF
ADN
DMR-PLUS

Additionally if you use the --additional-networks option to select some additional regional network you must create a corresponding TG list with the same name in all capital letters.

codeplug_generator.py --help 
prints  a brief self-explanatory help text. 

Note that any location containing spaces must be in " quotes or escaped. 

Ex: 

codeplug_generator.py --channel_number 500 --states "New Hampshire",Vermont,"New York",Massachusetts,Connecticut,"New Jersey" --additional-networks NEDECN

Of course you can specify "new york" as new\ york or "New york"  all the same.

WARNING:
The output of this program is only as good as the data in the radioid database!
There are a lot of inconsistent data issues in the radioid database. Check your channel frequency before transmitting.

The program will print out what network it is skipping, and a brief summary at the end.

It will also download the map.json file form radioid.net only once every 24h.

I anticipate a lot of data issues, and over time the APIs will break.
I will update the program as time permits.

Enjoy!
73's
Luca
VE2WKR/W0

