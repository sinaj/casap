function show_found(layer, data, datemin, datemax) {
    var wkt_f = new OpenLayers.Format.WKT();
    var last_exit = null;
    var _MS_PER_HOUR = 1000 * 60 * 60;
    var _MS_PER_MIN = 1000 * 60;
    var seen_ids = [];
    // iterate through each journey
    data.forEach(function (journey) {

        var pointList = [];
        var time_spent = {enter: null, exit: null};
        // add each path for each journey separately
        journey.forEach(function (place, i) {

            var color = "green";
            if (layer.name == "Activities path") color = "green";
            if (place.category == "Harmful") color = "green";

            else var time = '';

            if (place.time != null) {
                var time = place.time;
                time_compare = moment(time, 'YYYY-MM-DD, hh:mm:ss ').startOf('day').toDate();
                // skip all activities not within the date range
                if (time_compare < datemin || time_compare > datemax) {
                    return
                }
            }

            if (i == 0 && last_exit != null && pointList.length == 0) {
                pointList.push(last_exit); // keep track of exit point to draw line from THIS IS BUGGY
                last_exit = null;
            }

            //----------------------------------------------------------------------//

            // MoodAlert was written in Python2 and when integration with the C-ASAP project was done,
            // C-ASAP was already written in Python3. String formatting errors were happening everywhere,
            // So some data manipulation had to be done in this Javascript file.

            var shape_type = place.feature.substr(0, place.feature.indexOf(" "));

            if (shape_type.startsWith("b'")) {
                shape_type = shape_type.substring(2);
            }

            if (place.feature.startsWith("b'")) {
                var test = place.feature.substring(2);
                test = test.slice(0, -1);
                place.feature = test;
            }

            geom = wkt_f.read(place.feature);

            //----------------------------------------------------------------------//


            if (shape_type == 'MULTIPOLYGON' && seen_ids.indexOf(place.id) == -1) var title = place.name;
            else var title = place.name + " " + place.act_type;

            if (place.act_type == 'enter location') time_spent.enter = new Date(place.time);

            if (place.act_type == 'exit place') {
                time_spent.exit = new Date(place.time);
                // keep track of total time spent there in millis
                var place_update = layer.getFeaturesByAttribute('title', place.name);
                if (place_update.length != 0) {
                    // add total time spent there all together
                    if (place_update[0].attributes.time != '' && typeof place_update[0].attributes.time === 'number') {
                        place_update[0].attributes.time = place_update[0].attributes.time + (time_spent.exit.getTime() - time_spent.enter.getTime());
                    } else {
                        place_update[0].attributes.time = time_spent.exit.getTime() - time_spent.enter.getTime();
                    }
                    layer.drawFeature(place_update[0]);

                    // update table
                    var curr_entry = $("table#listevent tbody tr > th:first-child").filter(function () {
                        return ($(this).text() == moment(time_spent.enter, "YYYY-MM-DD, hh:mm:ss").format('LLL'));
                    });
                    curr_entry.next().text(moment(time_spent.exit, "YYYY-MM-DD, hh:mm:ss").format('LLL'));
                }

            }

            geom.attributes = {
                'label': '',
                'color': color,
                'fillcolor': color,
                'highlight': "0.4",
                'xOffset': 0,
                'yOffset': -15,
                'strokeWidth': 2,
                'title': title,
                'time': time,
                'owner': place.person,
                'category': place.category,
            };
            if (shape_type == 'MULTIPOLYGON') {

                if (seen_ids.indexOf(place.id) == -1) {
                    if (time_spent.enter == null) {
                        time_spent.enter = new Date(place.time);
                    }
                    layer.addFeatures([geom]);
                    layer.drawFeature(geom);
                    seen_ids.push(place.id);
                }
            }

            if (shape_type == 'POINT') {
                layer.addFeatures([geom]);
                layer.drawFeature(geom);
                var coords = place.feature.replace(/[`~!@#$%^&*()_|+\=?;:'",<>\{\}\[\]\\\/]/gi, '').split(' ');
                var path_pnt = new OpenLayers.Geometry.Point(coords[1], coords[2]);

                // if at last point in journey update last exit
                if (place.act_type == 'exit place') {
                    last_exit = path_pnt;

                } else {
                    pointList.push(path_pnt);
                }
            }

            // after two points

            if (pointList.length > 1) {
                line = new OpenLayers.Geometry.LineString(pointList);
                feature = new OpenLayers.Feature.Vector(line);
                feature.attributes = {
                    'label': '',
                    'dash': "solid",
                    'strokeWidth': 2,
                };
                last = pointList[1];
                pointList = [];
                pointList.push(last);

                layer.addFeatures([feature]);
                layer.drawFeature(feature);
            }
        });
    });
}