from rest_framework.decorators import api_view
from rest_framework.response import Response
from casap.models import Activity
from casap.models import Vulnerable
from casap.models import LostPersonRecord
from casap.models import SightingRecord
from django.http import HttpResponseRedirect, JsonResponse
from django.core.urlresolvers import reverse
from django.contrib.gis.geos import GEOSGeometry, Point, WKTWriter, MultiPolygon




@api_view(['GET','POST'])
def getPath(request):

    if request.method == "POST":
        data = {"test":"name"}
        result = request.POST['name']
        namePair = result.split(" ")
        firstName = namePair[0]
        lastName = namePair[1]

        person = Vulnerable.objects.filter(first_name=firstName,last_name=lastName).first()
        wkt_w = WKTWriter()
        j = 0
        lost_record = LostPersonRecord.objects.filter(vulnerable=person)
        sight_record = SightingRecord.objects.filter(lost_record=lost_record)
        print(sight_record)




    return Response(data) 
    
