import datetime

from rest_framework.decorators import api_view
from rest_framework.response import Response
from casap.models import FoundActivity
from casap.models import Vulnerable, Location
from django.contrib.gis.geos import GEOSGeometry, Point, WKTWriter

from casap.views.views_dashboard import geofence_record, point_map_record


@api_view(['GET'])
def getPath(request):
    data = request.get_full_path().split('?')[1]
    result = data.replace("%20", " ")

    namePair = result.split(" ")
    firstName = namePair[0]
    lastName = namePair[1]

    person = Vulnerable.objects.filter(first_name=firstName, last_name=lastName).first()
    wkt_w = WKTWriter()
    loc_activities = FoundActivity.objects.prefetch_related('location', 'person').filter(person=person,
                                                                                         category="Location").order_by(
        'time')
    j = 0
    # for the table summary. Group all similar location activities in order
    currlocation = None
    currentplace = None
    startDate = None
    processed = []

    journeys = [
        []]  # list of lists of separate journey dicts to then add to ordered dict of features for template to draw
    feature_fences = []  # list of lists of locations to add
    for l in loc_activities:
        if not startDate:
            startDate = l.time.date()

        # current point
        pnt = Point(float(l.locLon), float(l.locLat), srid=3857)
        # see if activity in geofence but needs to be updated in database (new geofence created recently)
        if not l.location:
            fence_loc = Location.objects.filter(fence__contains=pnt)
            if fence_loc:
                l.location = fence_loc[0]
                l.update()

        prior = {}
        prior['name'] = None
        prior['act_type'] = None
        if len(journeys[j]) > 0:
            prior = journeys[j][-1]

        # if hit a known location add nearest boundary points too
        if l.location:

            # for the processed table groupings (append each place travelled to in order)
            if l.location != currlocation:
                processed.append({"time": str(l.time), "location": l.location, "person": l.person,
                                  "activity_type": str(l.activity_type)})
                currentplace = l
                currlocation = l.location

            # add the ENTRY boundary point then the location
            if str(l.location.name):  # if has name then at known geofence

                # went from location to location
                if (prior['act_type'] == "geo_fence" or prior['act_type'] == "exit place") and prior[
                    'name'] != l.location.name:
                    # use centroids as point to point reference
                    a = prior['feature'].lstrip('b')
                    prior['feature'] = a[1:-1]
                    last_cnt = GEOSGeometry(prior['feature']).centroid

                    wkt_feat = wkt_w.write(last_cnt)
                    a = str(wkt_feat)
                    b = a.lstrip('b')
                    wkt_feat = b[1:-1]
                    to_add = point_map_record(str(l.location.name), wkt_feat, last_cnt, l, "exit place")
                    journeys[j].append(to_add)
                    # start next journey
                    journeys.append([])
                    j += 1

                    # add entry point
                    curr_cnt = l.location.fence.centroid
                    wkt_feat = curr_cnt.wkt
                    to_add = point_map_record(str(l.location.name), wkt_feat, curr_cnt, l, "enter location")
                    journeys[j].append(to_add)

                # entered new location after a travel point
                # get entry point based on last recorded location
                elif prior['name'] and prior['name'] != l.location.name:
                    last_pnt = Point(float(prior['locLon']), float(prior['locLat']), srid=3857)
                    boundary = l.location.fence.boundary
                    opt_dist = boundary.project(last_pnt)
                    # get point on boundary at that distance
                    entry = boundary.interpolate(opt_dist)
                    wkt_feat = wkt_w.write(entry)
                    a = str(wkt_feat)
                    b = a.lstrip('b')
                    wkt_feat = b[1:-1]
                    to_add = point_map_record(str(l.location.name), wkt_feat, entry, l, "enter location")
                    journeys[j].append(to_add)

                # add current location even if stayed in same location
                wkt_fence = wkt_w.write(l.location.fence)
                to_add = geofence_record(l, wkt_fence, True)
                journeys[j].append(to_add)

        # just travel point
        else:
            # for the table count travel as no location
            currlocation = None
            currentplace = None

            # may need exit point from last location to this current point
            if prior['act_type'] == "geo_fence":
                a = prior['feature']
                b = a.lstrip('b')
                prior['feature'] = b[1:-1]
                boundary = GEOSGeometry(prior['feature']).boundary
                opt_dist = boundary.project(pnt)
                exitpnt = boundary.interpolate(opt_dist)
                wkt_feat = wkt_w.write(exitpnt)
                a = str(wkt_feat)
                b = a.lstrip('b')
                wkt_feat = b[1:-1]
                to_add = point_map_record(str(prior['name']), wkt_feat, exitpnt, l, "exit place")
                journeys[j].append(to_add)

                # start next journey after exit
                journeys.append([])
                j += 1

            wkt_feat = wkt_w.write(pnt)
            a = str(wkt_feat)
            b = a.lstrip('b')
            wkt_feat = b[1:-1]
            reg_point = point_map_record("journey: " + str(j), wkt_feat, pnt, l, "moving")
            journeys[j].append(reg_point)

    # get additional known locations details for this person or their friends' homes
    fences = list(Location.objects.filter(person=person))
    for f in fences:
        wkt_fence = wkt_w.write(f.fence)
        to_add = geofence_record(f, wkt_fence, False)
        feature_fences.append([to_add])

    return Response(journeys)
