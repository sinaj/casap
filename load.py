import os
import subprocess
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import CoordTransform, SpatialReference
from django.db import transaction
from casap.models import Location
import re

'''
for loading and formatting OpenStreet maps data (buildings and places of interest)

IMPORTANT!!!!!!!!!!
first verify mapping fields and layer numbers wanted by running getMapModelInfo.py script
and visually inspecting output file named 'OSMmapModelInfo.txt'
MAKE SURE LAYER NUMBERS FOR gis.osm_pois_a_free_1, AND gis.osm_buildings_a_free_1 ARE CORRECTLY LABELLED

get updated download for Alberta shape file from: http://download.geofabrik.de/north-america/canada.html
to run script: 
python manage.py shell
import load
load.run()
'''

# change this for different area's data folders
OSMdatafilename = 'alberta-latest-free.shp'
data_mapping = {
    'name' : 'osm_id',
    'description' : 'name',
    'fence' : 'MULTIPOLYGON',
    'addit_info': 'fclass'
}


openStreetData_shp = os.path.abspath(os.path.join(os.path.dirname(__file__), 'OSMdataProcess', OSMdatafilename))

# transform map coordinates to match our map, rename in more logical way, delete unnecessary info
# takes a while to run given the LARGE initial set of datapoints saved to query
def formatNewData(location):
    ct = CoordTransform(SpatialReference('epsg:4326'), SpatialReference('epsg:3857'))
    for n in location:
        if n.name.isdigit():
            temp = n.name
            if n.description == '':
                if n.addit_info == '':
                    n.delete()
                    continue
                else:                        
                    n.name = n.addit_info.capitalize() + ", id: " + temp
                    n.description = n.addit_info
            else:
                if n.addit_info == '' or n.addit_info == 'building':
                    n.name = n.description + ", id: " + temp
                else:
                    n.name = n.addit_info.capitalize() + ': ' + n.description + ", id: " + temp                    
                n.description =  n.addit_info + " id: " + temp
            n.name = re.sub(r'[^\x00-\x7F]+',' ', n.name)
            n.fence.transform(ct)
            try:
                n.update()
            except Exception as e:
                print(str(e))
            print("\n updated " + temp)

def run(verbose=True):
    try:
        # points of interest MAKE SURE THIS LAYER NUMBER IS CORRECT
        osm_pois = LayerMapping(
            Location, openStreetData_shp, data_mapping,
            transform=False,
            layer=8,
        )
        
    except Exception as e:
        print(str(e) + "\n\n file doesn't exist, trying to untar the compressed file in OSMdataProcess/ now")
        tarfile = 'alberta-latest-free.shp.tar.gz'
        os.chdir('OSMdataProcess/')
        subprocess.call(['tar', '-zxvf', tarfile])
        os.chdir('..')
        # retry
        osm_pois = LayerMapping(
            Location, openStreetData_shp, data_mapping,
            transform=False,
            layer = 9,
        )

    # buildings - only keep one's with names MAKE SURE THIS LAYER NUMBER IS CORRECT
    osm_building = LayerMapping(
        Location, openStreetData_shp, data_mapping,
        transform=False,
        layer = 14,
    )
    
    try: 
        # THIS LINE WILL PERMANENTLY REMOVE ALL PREVIOUSLY SAVED OSM LOCATIONS
        Location.objects.filter(name__contains = 'id:').delete()

        osm_pois.save(strict=False, verbose=verbose)
        location = Location.objects.exclude(addit_info__startswith = 'building')  
        formatNewData(location)

        osm_building.save(strict=False, verbose=verbose)
        location = Location.objects.filter(addit_info__startswith = 'building')
        formatNewData(location)
        

    except Exception as e:
        print(e)
 
