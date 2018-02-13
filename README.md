# C-ASAP

C-ASAP project aims to develop a software platform for coordinating the activities around reporting missing persons, notifying volunteers in the vicinity, and coordinating the activities of volunteers who may encounter these missing persons, the family members and the police.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Virtualenv/Virtualenvwrapper
- Python 3.5.1
- PostgreSQL and postgis
- settings_server.py from [Carlo Oliva](https://github.com/olivaC) or [Yuxuan Zhao](https://github.com/zhaoyuxuan)

### Installing
1. **_Clone this repository_**  
2. **_cd into the casap directory and add the settings_server.py file here_** 
3. **_Create a Virtual Environment using python3_** 
4. **_Follow the instructions to install the required geospatial libraries, and postgis_** 
---
 - Linux example for step 4. OSX users follow similar steps.
 - Credit to **Falon Scheers** for Linux instructions.
```
$ sudo apt-get install binutils libproj-dev gdal-bin
```
- GEOS download and configure:
```
$ wget http://download.osgeo.org/geos/geos-3.4.2.tar.bz2      
$ tar xjf geos-3.4.2.tar.bz2  
$ cd geos-3.4.2   
$ ./configure     
$ make            
$ sudo make install     
$ cd .. 
```          
- [PROJ.4](https://github.com/OSGeo/proj.4/wiki/) is a library for converting geospatial data to different coordinate reference systems:
```
wget http://download.osgeo.org/proj/proj-4.9.1.tar.gz     
$ wget http://download.osgeo.org/proj/proj-datumgrid-1.5.tar.gz   
Next, untar the source code archive, and extract the datum shifting files in the nad subdirectory. This must be done prior to configuration:    
$ tar xzf proj-4.9.1.tar.gz   
$ cd proj-4.9.1/nad     
$ tar xzf ../../proj-datumgrid-1.5.tar.gz 
$ cd ..     
Finally, configure, make and install PROJ.4:    
$ ./configure     
$ make      
$ sudo make install     
$ cd ..
```

- GDAL open source geospatial library that has support for reading most vector and raster spatial data formats:
```
$ wget http://download.osgeo.org/gdal/1.11.2/gdal-1.11.2.tar.gz   
$ tar xzf gdal-1.11.2.tar.gz  
$ cd gdal-1.11.2  
Configure, make and install:  
$ ./configure --with-python     
$ make # Go get some coffee, this takes a while.      
$ sudo make install     
$ cd ..
```
* Install postgis for your machine: http://postgis.net/install/   
[for Ubuntu](http://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS22UbuntuPGSQL95Apt) first check what release you have: 
```
$ sudo lsb_release -a
```

- Then lookup your release for <i>your_tagname</i> [here](http://www.postgresql.org/download/linux/ubuntu/) and insert:          
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt <i>your_tagname</i>-pgdg main" >> /etc/apt/sources.list'               
```
Add Keys:                  
$ wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -   
$ sudo apt-get update   

Install postgresql 9.5, PostGIS 2.2, PGAdmin3, pgRouting 2.1 :      
$ sudo apt-get install postgresql-9.5-postgis-2.2 pgadmin3 postgresql-contrib-9.5 

To Install pgRouting 2.1 package:         
$ sudo apt-get install postgresql-9.5-pgrouting         

* after PostGIS is installed create database and then put this db name in your settings.py file:             
$ createdb  < db name >          
$ psql < db name >        
$ > CREATE EXTENSION postgis; 
```
---

5. **_Modify **settings_server.py** for your own computer and database_**  
```
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '<db name>',
    }
}
```
6. **_Install requirements.txt_** 
```
$ pip install -r requirements.txt
```

7. **_Make database migrations and migrate to the database_** 
```
$ python manage.py makemigrations casap
$ python manage.py migrate casap
```
- If you get database errors run this:
``` python manage.py migrate --run-syncdb ```

8. **_Load Open Street Maps location data for Alberta_**
* Courtesy from **Falon Scheers**
* Ask for the /OSMdataProcess folder
* First read comments in and run file '/OSMdataProcess/getMapModelInfo.py' 
* Then inspect the output file, '/OSMdataProcess/OSMmapModelInfo.txt' and note the desired layer numbers for buildings and POI
* Then read comments, mend, and run the file 'Load.py' to store OSM locations into your local database    

## Run the Server

```
$ python manage.py runserver
```

## Production server
The project is deployed on the RAC server:  [C-ASAP Server](http://162.246.156.196)

### Production server pre-requisites

In order to make any changes to the production server, ask[@olivaC](https://github.com/olivaC)for a **.pem** file for access to the server.

### Making changes to the production website

1. Ssh in the server:
```
ssh ubuntu@162.246.156.196
```
2. Activate the virtual environment:
```
source django-env/bin/activate
```
3. cd into the casap project
```
cd casap
```
4. pull changes into either the master/development branch (whichever is being used)
```
git pull origin development
```
5. Enter your github credentials
6. If any static files were changed, you will need to serve these. 
```
./manage.py collectstatic
```


## Built With

* [Github](https://www.github.com) - Where the source code lives
* [Django](https://www.djangoproject.com/download/) - The web framework used
* [PostgreSQL](https://www.postgresql.org/) - Database
* [OpenLayers](http://openlayers.org/) - Location based layers
* [OpenStreetMap](https://www.openstreetmap.org) - Location finder
* [Google Maps](https://www.google.ca/maps) - Location
* [Twilio](https://www.twilio.com/) - SMS notifications
* [Rapid Access Cloud](https://cloud.cybera.ca) - Cybera Server
* [Nginx](https://www.nginx.com/) - Serve web pages on RAC server
* [Twitter](https://www.twitter.com) - Tweets
* [Bitly](https://bitly.com) - URL shortener

## Authors

* **Sina Jalali** - *Initial work*
* [**Carlo Oliva**](https://github.com/olivaC)
* [**Yuxuan Zhao**](https://github.com/zhaoyuxuan)

## Acknowledgements 

* **Falon Scheers** - *Location and Activity functionality using OpenLayers and OpenStreetMap*
