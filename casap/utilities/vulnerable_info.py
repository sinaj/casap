import simplejson
from rest_framework.decorators import api_view
from rest_framework.response import Response

from casap.models import Vulnerable


@api_view(['GET'])
def get_vulnerable(request):
    data = request.get_full_path().split('?')[1]
    person = Vulnerable.objects.get(hash=data)
    if person.nickname:
        person_details = [
            [person.nickname],
            [person.sex],
            [person.race],
            [person.hair_colour],
            [person.height],
            [person.weight],
            [person.eye_colour],
            [person.favourite_locations],
            [person.transportation],
            [person.instructions],
            [person.hash],
        ]
    else:
        person_details = [
            [None],
            [person.sex],
            [person.race],
            [person.hair_colour],
            [person.height],
            [person.weight],
            [person.eye_colour],
            [person.favourite_locations],
            [person.transportation],
            [person.instructions],
            [person.hash],
        ]

    return Response(person_details)
