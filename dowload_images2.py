import sys
import urllib2, urllib
import json
import os
import shutil
import pyexiv2
from pyexiv2.utils import make_fraction


MAPILLARY_API_IM_SEARCH_URL = 'http://api.mapillary.com/v1/im/search?'
MAX_RESULTS = 400
BASE_DIR = 'downloaded/'


'''
Script to download images using the Mapillary image search API.

Downloads images inside a rect (min_lat, max_lat, min_lon, max_lon).

Write lat, long, bearing into EXIF, so you can open downloaded images in JOSM.

Requires gpxpy, e.g. 'pip install gpxpy'

Requires pyexiv2, see install instructions at http://tilloy.net/dev/pyexiv2/
(or use your favorite installer, e.g. 'brew install pyexiv2').
'''

def create_dirs(base_path):
    try:
        shutil.rmtree(base_path)
    except:
        pass
    os.mkdir(base_path)


def query_search_api(min_lat, max_lat, min_lon, max_lon, max_results):
    '''
    Send query to the search API and get dict with image data.
    '''
    params = urllib.urlencode(zip(['min-lat', 'max-lat', 'min-lon', 'max-lon', 'max-results'],[min_lat, max_lat, min_lon, max_lon, max_results]))
    query = urllib2.urlopen(MAPILLARY_API_IM_SEARCH_URL + params).read()
    query = json.loads(query)
    print("Result: {0} images in area.".format(len(query)))
    return query


def download_images(query, path, size=1024):
    '''
    Download images in query result to path.

    Return list of downloaded images with lat,lon.
    There are four sizes available: 320, 640, 1024 (default), or 2048.
    '''
    im_size = "thumb-{0}.jpg".format(size)
    im_list = []

    for im in query:
        url = im['image_url']+im_size
        filename = im['key']+".jpg"
        try:
            image = urllib.URLopener()
            image.retrieve(url, path+filename)
            im_list.append([filename, str(im['lat']), str(im['lon'])])
            add_coord_into_exif(path+filename, str(im['lat']), str(im['lon']), str(im['ca']))
            print("Successfully downloaded: {0} ca={1}".format(filename, str(im['ca'])))
        except KeyboardInterrupt:
            break
        except:
            print("Failed to download: {0}".format(filename))
    return im_list

def to_deg(value, loc):
    '''
    Convert decimal position to degrees.
    '''
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    abs_value = abs(value)
    deg =  int(abs_value)
    t1 = (abs_value-deg)*60
    mint = int(t1)
    sec = round((t1 - mint)* 60, 6)
    return (deg, mint, sec, loc_value)

def add_coord_into_exif(filename, lat, lon,bearing):
    '''
    Find lat, lon and bearing of filename and write to EXIF.
    '''


    metadata = pyexiv2.ImageMetadata(filename)
    metadata.read()
    #print(metadata)


    try:

        #t = metadata['Exif.Photo.DateTimeOriginal'].value


        bearing=round(float(bearing))

        lat_deg = to_deg(float(lat), ["S", "N"])
        lon_deg = to_deg(float(lon), ["W", "E"])

        # convert decimal coordinates into degrees, minutes and seconds as fractions for EXIF
        exiv_lat = (make_fraction(lat_deg[0],1), make_fraction(int(lat_deg[1]),1), make_fraction(int(lat_deg[2]*1000000),1000000))
        exiv_lon = (make_fraction(lon_deg[0],1), make_fraction(int(lon_deg[1]),1), make_fraction(int(lon_deg[2]*1000000),1000000))

        # convert direction into fraction
        exiv_bearing = make_fraction(int(bearing*100),100)

        # add to exif
        metadata["Exif.GPSInfo.GPSLatitude"] = exiv_lat
        metadata["Exif.GPSInfo.GPSLatitudeRef"] = lat_deg[3]
        metadata["Exif.GPSInfo.GPSLongitude"] = exiv_lon
        metadata["Exif.GPSInfo.GPSLongitudeRef"] = lon_deg[3]
        metadata["Exif.Image.GPSTag"] = 654
        metadata["Exif.GPSInfo.GPSMapDatum"] = "WGS-84"
        metadata["Exif.GPSInfo.GPSVersionID"] = '2 0 0 0'
        metadata["Exif.GPSInfo.GPSImgDirection"] = exiv_bearing
        metadata["Exif.GPSInfo.GPSImgDirectionRef"] = "T"


        metadata.write()
        #print("Added geodata to: {0} ({1}, {2}, {3})".format(filename, lat, lon, bearing))
    except ValueError, e:
        print("Skipping {0}: {1}".format(filename, e))


if __name__ == '__main__':
    '''
    Use from command line as below, or run query_search_api and download_images
    from your own scripts.
    '''

    # handle command line parameters
    if len(sys.argv) < 5:
        print("Usage: python download_images.py min_lat max_lat min_lon max_lon max_results(optional) ")

    try:
        min_lat, max_lat, min_lon, max_lon = sys.argv[1:5]
    except:
        print("Usage: python download_images.py min_lat max_lat min_lon max_lon max_results(optional)")
        raise IOError("Bad input parameters.")

    if len(sys.argv)==6:
        max_results = sys.argv[5]
    else:
        max_results = MAX_RESULTS

    # query api
    query = query_search_api(min_lat, max_lat, min_lon, max_lon, max_results)

    # create directories for saving
    create_dirs(BASE_DIR)

    # download
    downloaded_list = download_images(query, path=BASE_DIR)

    # save filename with lat, lon
    with open(BASE_DIR+"downloaded.txt", "w") as f:
        for data in downloaded_list:
            f.write(",".join(data) + "\n")
