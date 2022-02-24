# Exploring django-esi Endpoints

The builtin Django shell allows you to explore the EVE ESI endpoints via django-esi, making it an easy way to find what methods are available for consumption.

## Prerequisites

Prior to using the Django shell to explore django-esi, you must first [install and configure](https://django-esi.readthedocs.io/en/latest/operations.html) django-esi in the Django project.

## Getting Started

Open up a command line and navigate to the Django folder containing manage.py.

```
C:\path\to\django\app> python manage.py shell
>>> from esi.clients import esi_client_factory
>>> from pprint import pprint
>>> c = esi_client_factory()
>>> pprint(dir( c ))
```

The above commands in the Django shell should show something like this:

```
['Alliance',
 'Assets',
 'Bookmarks',
 'Calendar',
 'Character',
 'Clones',
 'Contacts',
 'Contracts',
 'Corporation',
 'Dogma',
 'Faction_Warfare',
 'Fittings',
 'Fleets',
 'Incursions',
 'Industry',
 'Insurance',
 'Killmails',
 'Location',
 'Loyalty',
 'Mail',
 'Market',
 'Opportunities',
 'Planetary_Interaction',
 'Routes',
 'Search',
 'Skills',
 'Sovereignty',
 'Status',
 'Universe',
 'User_Interface',
 'Wallet',
 'Wars']
 ```

 ## Further Uses

 Once it's working, you can explore further endpoints just by adding to the ```c``` variable.

 ```
 >>> pprint(dir(c.Universe))
['get_universe_ancestries',
 'get_universe_asteroid_belts_asteroid_belt_id',
 'get_universe_bloodlines',
 'get_universe_categories',
 'get_universe_categories_category_id',
 'get_universe_constellations',
 'get_universe_constellations_constellation_id',
 'get_universe_factions',
 'get_universe_graphics',
 'get_universe_graphics_graphic_id',
 'get_universe_groups',
 'get_universe_groups_group_id',
 'get_universe_moons_moon_id',
 'get_universe_planets_planet_id',
 'get_universe_races',
 'get_universe_regions',
 'get_universe_regions_region_id',
 'get_universe_stargates_stargate_id',
 'get_universe_stars_star_id',
 'get_universe_stations_station_id',
 'get_universe_structures',
 'get_universe_structures_structure_id',
 'get_universe_system_jumps',
 'get_universe_system_kills',
 'get_universe_systems',
 'get_universe_systems_system_id',
 'get_universe_types',
 'get_universe_types_type_id',
 'post_universe_ids',
 'post_universe_names']
 ```